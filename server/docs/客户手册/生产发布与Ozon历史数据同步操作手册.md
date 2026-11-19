# 生产发布与 Ozon 历史数据同步操作手册

> 适用范围：鲲鹏项目当前三仓库组合发布架构，以及生产环境 Ozon ODS、DWD 历史数据回填。
>
> 本文不假设使用人的 Windows 用户名、盘符或本地文件夹。凡出现 `<本地工作区>`，都要替换成自己电脑上存放三个仓库的目录。生产服务器目录是部署架构的一部分，可以直接照抄。
>
> 文中的店铺 ID、分支名和日期范围均应在执行前按实际情况核对。

## 0. 先看结论

### 0.1 一次正常发布怎么走

```text
本地完成修改和自检
→ 提交并推送有改动的前端/后端仓库
→ 在本地 deploy 仓库生成 release-lock.conf
→ 提交并推送 deploy 仓库
→ 登录生产服务器，只更新 repos/deploy
→ 运行 bash scripts/release.sh
→ 检查体检结果并人工验收
```

生产服务器**不需要手动 `git pull` 前端和后端仓库**。`release.sh` 会自动从它们的远端仓库执行 `git fetch`，再按 `release-lock.conf` 中锁定的提交号生成发布版本。

本地代码没有推送、版本锁没有更新，或者 deploy 仓库没有推送时，生产服务器只拉 deploy 也无法发布到本次新代码。

### 0.2 Ozon 历史数据同步怎么走

```text
确认发布成功且容器健康
→ 进入 current 并加载部署函数
→ 备份数据库
→ 查询生产环境实际 Ozon 店铺
→ 设置店铺和日期窗口
→ 按业务依赖顺序串行同步
→ 查询 ODS、DWD 并从页面抽样导出验收
```

发布脚本**不会自动补抓全部 Ozon 历史数据**。只有本次功能确实需要回填旧数据时，才执行历史同步；普通代码发布不需要每次都跑第 7～11 节。

## 1. 必须先理解的目录和数据链路

### 1.1 本地三个 Git 仓库与路径约定

```text
<本地工作区>\
├── kunpeng_client\   # 前端
├── kunpeng_server\   # 后端、调度器、迁移
└── kunpeng_deploy\   # 版本锁定、Compose、发布和回滚脚本
```

`<本地工作区>` 可以位于任意盘符、任意用户名目录，例如 `E:\Projects\Kunpeng`。建议三个仓库保持为同级目录，因为 `prepare-release.sh` 默认按这个结构寻找前端和后端仓库。

在 PowerShell 中可以先设置一个只对当前终端有效的变量，后续命令便不依赖固定盘符：

```powershell
$KUNPENG_WORKSPACE = "<替换成你电脑上的工作区绝对路径>"
Test-Path (Join-Path $KUNPENG_WORKSPACE "kunpeng_client")
Test-Path (Join-Path $KUNPENG_WORKSPACE "kunpeng_server")
Test-Path (Join-Path $KUNPENG_WORKSPACE "kunpeng_deploy")
```

三个检查结果都应为 `True`。不要把示例中的尖括号原样复制执行。

当前使用的分支为：

| 仓库 | 当前发布分支 |
|---|---|
| `kunpeng_client` | `master_copy_dev` |
| `kunpeng_server` | `master_copy` |
| `kunpeng_deploy` | `master` |

分支以后如有调整，以 `git branch --show-current` 的实际输出为准，不要照抄旧分支名。

### 1.2 生产服务器目录

使用生产部署账号登录后，脚本默认把 `$HOME/kunpeng` 作为部署根目录。本文统一用 `KUNPENG_HOME` 表示该目录：

```bash
export KUNPENG_HOME="${KUNPENG_HOME:-$HOME/kunpeng}"
```

当前服务器的部署账号为 `kunpeng` 时，变量值就是 `/home/kunpeng/kunpeng`。如果以后更换账号或安装位置，只需在当前终端把 `KUNPENG_HOME` 设置成实际绝对路径，不要逐条修改后续命令。

```text
$KUNPENG_HOME/
├── repos/
│   ├── deploy/       # 唯一执行正常发布脚本的仓库
│   ├── client/
│   └── server/
├── shared/           # .env、备份和日志等共享资源
├── releases/         # 每次发布生成的组合版本
├── current           # 当前线上版本软链
└── previous          # 上一个组合版本软链
```

注意：生产服务器不存在 `$KUNPENG_HOME/repo` 这个单数目录。正常发布入口是：

```bash
$KUNPENG_HOME/repos/deploy/scripts/release.sh
```

### 1.3 Ozon 历史数据同步链路

正常的源数据同步命令走完整链路：

```text
Ozon API → ODS → DWD → 中文翻译字段
```

带 `_dwd` 的独立构建命令只会：

```text
已有 ODS → DWD
```

它们不会调用 Ozon API。ODS 没有数据时，单独重建 DWD 也不会产生新业务数据。

## 2. 本地发布前检查

发布前先确认前后端代码已经完成测试、提交并推送。不要把 `.env`、Token、数据库密码或店铺 API Key 提交到 Git。

### 2.1 后端自检

在 Windows PowerShell 中执行。以下命令沿用第 1.1 节设置的 `$KUNPENG_WORKSPACE`：

```powershell
Set-Location (Join-Path $KUNPENG_WORKSPACE "kunpeng_server")
git status --short
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m black .
.\.venv\Scripts\python.exe -m isort .
```

如果改了数据库模型，还必须确认已经新增 Alembic 迁移，并在测试库执行成功：

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

禁止删除或改写已经提交的迁移文件。

### 2.2 前端自检

```powershell
Set-Location (Join-Path $KUNPENG_WORKSPACE "kunpeng_client")
npm run lint
npm run build
```

### 2.3 提交并推送前后端

先用 `git status --short` 确认修改范围，只添加本次相关文件。不要为了省事把不相关改动一起提交。

后端示例：

```powershell
Set-Location (Join-Path $KUNPENG_WORKSPACE "kunpeng_server")
git status --short
git add <本次后端文件>
git commit -m "feat(ozon): 本次改动说明"
git push origin HEAD
```

前端示例：

```powershell
Set-Location (Join-Path $KUNPENG_WORKSPACE "kunpeng_client")
git status --short
git add <本次前端文件>
git commit -m "feat(ozon): 本次改动说明"
git push origin HEAD
```

如果前后端已经提交，只需要确认对应提交已推送，不要制造空提交：

```powershell
git status --short
git log -1 --oneline
git status -sb
```

`git status -sb` 不应显示本地分支领先远端（`ahead`）。如果显示领先，说明还有提交没有推送。

## 3. 本地生成并提交组合版本锁

这一步必须在前后端提交完成后执行。它会把前后端当前 `HEAD` 的完整提交号写入部署仓库的 `release-lock.conf`。

### 3.1 使用 Git Bash

在 VS Code 中打开 `kunpeng_deploy` 仓库，并在该仓库根目录新建 Git Bash 终端。先用 `pwd` 和 `git rev-parse --show-toplevel` 确认位置，不要在手册里硬编码某台电脑的 `bash.exe` 或工作区路径。

```bash
git rev-parse --show-toplevel
bash scripts/prepare-release.sh
```

正常输出会显示已锁定的前端、后端完整提交号。如果三个仓库没有放在同一父目录下，需要在 Git Bash 中显式传入实际路径：

```bash
CLIENT_REPO="/<盘符小写>/<前端仓库路径>" SERVER_REPO="/<盘符小写>/<后端仓库路径>" bash scripts/prepare-release.sh
```

Git Bash 中的 Windows 路径要写成 `/e/Projects/...` 形式，而不是 `E:\Projects\...`；路径中有空格时必须保留双引号。

### 3.2 审核并提交部署仓库

```bash
git diff -- release-lock.conf
git status --short
git add release-lock.conf
git commit -m "chore(deploy): 锁定本次前后端版本"
git push origin master
```

至此，Gitee 上应同时存在：

- 前端目标提交；
- 后端目标提交；
- 部署仓库中引用这两个提交的 `release-lock.conf`。

## 4. 在生产服务器发布

### 4.1 使用部署账号进入部署仓库

使用生产部署账号（当前为 `kunpeng`）登录。**不要先执行 `sudo -i` 切到 root**，否则 `$HOME` 会改变，发布脚本可能寻找错误的部署根目录。脚本需要 Docker 权限时会自行请求 `sudo`。

```bash
export KUNPENG_HOME="${KUNPENG_HOME:-$HOME/kunpeng}"
cd "$KUNPENG_HOME/repos/deploy"
```

确认当前目录确实是 Git 仓库：

```bash
pwd
git status --short
git branch --show-current
```

`git status --short` 必须为空。如果服务器部署仓库存在未提交修改，先停止发布并确认来源，不要覆盖。

### 4.2 更新部署仓库

```bash
git pull --ff-only origin master
```

检查本次锁定版本：

```bash
cat release-lock.conf
```

该文件只能包含前后端提交号，不应包含密码或 Token。

### 4.3 执行唯一正确的发布脚本

```bash
bash scripts/release.sh
```

发布脚本会自动：

1. 获取前端、后端锁定提交；
2. 创建新的 `releases/<时间戳>` 组合版本；
3. 注入服务器共享配置；
4. 备份当前生产数据库；
5. 构建前端、后端镜像；
6. 启动数据库并执行 `alembic upgrade head`；
7. 切换 `current` 软链；
8. 启动后端、调度器和前端；
9. 执行发布后体检。

只有最终出现“发布完成”和体检通过，才能认为发布成功。不要再使用旧的 `deploy-update-prod.sh`。

## 5. 发布完成后的生产检查

### 5.1 加载当前版本的部署函数

```bash
export KUNPENG_HOME="${KUNPENG_HOME:-$HOME/kunpeng}"
cd "$KUNPENG_HOME/current"
source scripts/lib/deploy-common.sh
```

每次新开 SSH、重新登录或进入新的 root shell，都需要重新执行上面两条命令。否则会出现：

```text
compose_run: command not found
```

### 5.2 检查版本软链和发布清单

```bash
readlink -f "$KUNPENG_HOME/current"
readlink -f "$KUNPENG_HOME/previous"
cat "$KUNPENG_HOME/current/manifest.env"
```

确认 `current` 指向本次新生成的时间戳目录，`manifest.env` 中的前后端提交号与本地锁定一致。

### 5.3 检查四个容器

```bash
compose_run "$PWD" ps
```

以下服务都应处于运行或健康状态：

- `db`
- `backend`
- `scheduler`
- `frontend`

### 5.4 再次执行体检

```bash
bash scripts/smoke-test.sh "$PWD"
```

应检查通过：前端首页、后端健康接口、API 文档、登录路由及四个容器。

### 5.5 检查数据库迁移版本

```bash
compose_run "$PWD" exec -T backend alembic current
```

输出应位于本次代码的 Alembic Head。

### 5.6 检查日志

```bash
compose_run "$PWD" logs --since=10m --tail=200 backend
```

```bash
compose_run "$PWD" logs --since=10m --tail=200 scheduler
```

大量下面这种日志是健康检查，不是报错：

```text
GET /health 200 OK
```

过滤健康检查并查看真实错误：

```bash
compose_run "$PWD" logs --since=2h backend 2>&1 | grep -v "health" | grep -E -i "ERROR|Traceback|Internal Server Error|同步失败"
```

### 5.7 页面人工验收

至少检查：

- 页面能正常打开和登录；
- Ozon 对应模块可以查询；
- 店铺和日期筛选生效；
- 数据预览字段顺序正确；
- Excel 可以下载，表头、店铺 ID 和中文翻译列正确。

## 6. 发布失败或线上异常时回滚

查看可回滚版本：

```bash
bash "$KUNPENG_HOME/current/scripts/rollback.sh" --list
```

默认切回 `previous`：

```bash
bash "$KUNPENG_HOME/current/scripts/rollback.sh"
```

普通回滚只切换代码和容器，不恢复数据库，也不执行 Alembic downgrade。

不要随意添加 `--restore-db`。恢复数据库可能覆盖发布后新增的生产数据，只有明确评估并再次确认后才允许执行。

## 7. 历史数据回填前准备

### 7.1 进入正确目录

```bash
export KUNPENG_HOME="${KUNPENG_HOME:-$HOME/kunpeng}"
cd "$KUNPENG_HOME/current"
source scripts/lib/deploy-common.sh
```

长时间任务建议在 `tmux` 中执行，防止 SSH 断开：

```bash
tmux new -s ozon-backfill
```

如果进入了新的 tmux shell，需要再次执行 `cd` 和 `source`。

### 7.2 回填前备份

```bash
BACKUP_TAG="before_ozon_backfill_$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE=$(backup_database "$PWD" "$KUNPENG_HOME/shared" "$BACKUP_TAG") || { echo "数据库备份失败，停止操作"; exit 1; }
echo "$BACKUP_FILE"
ls -lh "$BACKUP_FILE"
```

必须确认文件存在且大小不为 0。

### 7.3 查询生产环境实际 Ozon 店铺

```bash
compose_run "$PWD" exec -T db sh -lc 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT id,name,platform_shop_id FROM shops WHERE platform=\"ozon\" ORDER BY id;"'
```

根据实际结果设置店铺。下面仅为示例：

```bash
OZON_SHOPS="2 5 6 7 8 9 10 11 12"
```

不要长期把旧店铺清单当成事实，每次大批量回填前都重新查询。

## 8. 定义统一的同步函数

复制下面整个函数：

```bash
ozon_sync() {
    DATA_TYPE="$1"
    SHOP_ID="$2"
    DATE_FROM="$3"
    DATE_TO="$4"
    echo "正在同步：${DATA_TYPE} 店铺=${SHOP_ID} 日期=${DATE_FROM}~${DATE_TO}"
    compose_run "$PWD" exec -T backend python -c "import urllib.request; u='http://127.0.0.1:8000/api/v1/platforms/ozon/sync/${DATA_TYPE}?shop_id=${SHOP_ID}&date_from=${DATE_FROM}&date_to=${DATE_TO}'; r=urllib.request.Request(u,method='POST'); print(urllib.request.urlopen(r,timeout=7200).read().decode('utf-8'))"
}
```

再复制按窗口批量执行函数：

```bash
run_windows() {
    TYPE="$1"
    SHOPS="$2"
    WINDOWS="$3"
    for SHOP_ID in $SHOPS; do
        for RANGE in $WINDOWS; do
            DATE_FROM="${RANGE%,*}"
            DATE_TO="${RANGE#*,}"
            ozon_sync "$TYPE" "$SHOP_ID" "$DATE_FROM" "$DATE_TO" || return 1
        done
    done
}
```

2026 年 2 月到 8 月的历史窗口示例：

```bash
HISTORY_WINDOWS="2026-02-01,2026-02-28 2026-03-01,2026-03-31 2026-04-01,2026-04-30 2026-05-01,2026-05-31 2026-06-01,2026-06-30 2026-07-01,2026-07-31 2026-08-01,2026-08-26"
```

日期需要按实际回填期修改，不要无限期照抄 2026 年示例。

## 9. 各业务模块正确的历史同步命令

一次只运行一个命令。等待当前命令完全返回后再运行下一个，不要多窗口并行调用同一店铺的 Ozon 接口。

### 9.1 商品基础资料

商品名称、货号、品类及翻译关联依赖商品 ODS，其他 DWD 回填前先执行一次：

```bash
for SHOP_ID in $OZON_SHOPS; do ozon_sync products "$SHOP_ID" 2026-02-01 2026-08-26 || break; done
```

`products` 不依赖历史日期，日期参数只是为了复用统一命令。

### 9.2 订单 DWD

订单分 FBS 和 FBO，两项都要同步：

```bash
ORDER_SHOPS="$OZON_SHOPS"
run_windows postings "$ORDER_SHOPS" "$HISTORY_WINDOWS"
run_windows fbo_postings "$ORDER_SHOPS" "$HISTORY_WINDOWS"
```

如果部分店铺已经回填完成，只把缺失店铺写入 `ORDER_SHOPS`。例如只补店铺 8 和 9：

```bash
ORDER_SHOPS="8 9"
```

这两项都会先写订单 ODS，再自动更新订单 DWD、关联退货 DWD和中文翻译字段。

### 9.3 退货 DWD

先按物流退货日期同步：

```bash
run_windows returns "$OZON_SHOPS" "$HISTORY_WINDOWS"
```

再按可视状态变更时间补抓，补齐近期变化的退货和赔偿状态：

```bash
run_windows return_status_changes "$OZON_SHOPS" "$HISTORY_WINDOWS"
```

两项都会先写退货 ODS，再刷新退货 DWD及翻译字段。

### 9.4 客户声音 DWD

评价接口在实际运行中可能每个请求都返回店铺全部评价，因此不需要按月重复拉取。每个店铺对完整区间执行一次即可：

```bash
for SHOP_ID in $OZON_SHOPS; do ozon_sync reviews "$SHOP_ID" 2026-02-01 2026-08-26 || echo "店铺 ${SHOP_ID} 评价同步失败，请记录后继续"; done
```

`reviews` 会先写评价 ODS，再构建客户声音 DWD并处理翻译字段。

如果 Ozon 返回：

```text
403 PermissionDenied
ReviewList is not available with existing subscription
```

说明该店铺订阅无评价接口权限，不是数据库或 DWD 错误。此时只能利用已有 ODS 重建 DWD：

```bash
ozon_sync customer_voice_dwd <店铺ID> 2026-02-01 2026-08-26
```

该命令不会从 Ozon 获取新评价。

### 9.5 广告效率 DWD

先同步广告活动及活动级日统计：

```bash
run_windows adverts "$OZON_SHOPS" "$HISTORY_WINDOWS"
```

再同步 SKU 级广告日统计并构建广告效率 DWD：

```bash
run_windows advert_products "$OZON_SHOPS" "$HISTORY_WINDOWS"
```

注意：

- `adverts` 不直接生成广告效率 DWD；
- `advert_products` 才会写 `ods_ozon_adv_stats_product_daily` 并构建 DWD；
- Ozon Performance 报表是异步生成的，单个批次可能等待数分钟；
- 同一凭证同时只允许有限数量的活跃报表任务，禁止并行；
- 当前逻辑默认只同步当前运行中的 SKU 广告活动；已经结束的历史 SKU 活动可能无法补齐；
- CPO、SEARCH_PROMO 等非 SKU 活动不进入当前 SKU 日粒度广告效率 DWD。

终端显示 `status=success`、`count=0` 不一定代表没有落库。统一同步路由只读取 `count/ods_count`，而广告服务实际返回 `campaigns/stats/rows`，所以要以数据库查询为准。

### 9.6 销售漏斗 DWD

`analytics_data` 会先写经营分析 ODS，再构建销售漏斗 DWD。

非 Premium 店铺只能查询最近三个月。以 2026-08-27 执行为例：

```bash
ANALYTICS_WINDOWS="2026-05-27,2026-05-31 2026-06-01,2026-06-30 2026-07-01,2026-07-31 2026-08-01,2026-08-26"
run_windows analytics_data "$OZON_SHOPS" "$ANALYTICS_WINDOWS"
```

未来执行时必须重新计算“当前日期往前三个月”，不能继续使用上面的固定日期。

如果使用超过权限范围的历史日期，Ozon 可能返回具有误导性的错误：

```text
400 Bad Request
date_to must be greater than date_from
```

即使传入的开始、结束日期实际不同，也应先检查店铺是否为非 Premium，以及日期是否超过最近三个月。

该接口限制约为每个卖家账号每分钟一次请求，整体任务耗时较长属于正常现象。

## 10. 同步命令与 ODS、DWD 对照

| 命令 | API 后写入的 ODS | 自动更新的 DWD |
|---|---|---|
| `products` | 商品 ODS | 为其他 DWD 提供商品、品类关联 |
| `postings` | FBS 订单 ODS | 订单 DWD、关联退货 DWD |
| `fbo_postings` | FBO 订单 ODS | 订单 DWD、关联退货 DWD |
| `returns` | 退货 ODS | 退货 DWD |
| `return_status_changes` | 退货 ODS | 退货 DWD |
| `reviews` | 评价 ODS | 客户声音 DWD |
| `adverts` | 广告活动、活动日统计 ODS | 不直接构建广告效率 DWD |
| `advert_products` | SKU 广告日统计 ODS | 广告效率 DWD |
| `analytics_data` | 经营分析日统计 ODS | 销售漏斗 DWD |

以下命令只使用已有 ODS，不请求平台 API：

- `order_dwd`
- `customer_voice_dwd`
- `advert_efficiency_dwd`
- `sales_funnel_dwd`

## 11. 历史数据完成后的数据库验收

### 11.1 订单 DWD

```bash
compose_run "$PWD" exec -T db sh -lc 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT shop_id,COUNT(*) AS row_count,MIN(in_process_date) AS min_date,MAX(in_process_date) AS max_date FROM dwd_ozon_order_detail WHERE in_process_date BETWEEN \"2026-02-01\" AND \"2026-08-26\" GROUP BY shop_id ORDER BY shop_id;"'
```

### 11.2 退货 DWD

```bash
compose_run "$PWD" exec -T db sh -lc 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT shop_id,COUNT(*) AS row_count,MIN(DATE(return_date)) AS min_date,MAX(DATE(return_date)) AS max_date FROM dwd_ozon_return_detail WHERE return_date >= \"2026-02-01\" AND return_date < \"2026-08-27\" GROUP BY shop_id ORDER BY shop_id;"'
```

### 11.3 客户声音 DWD

```bash
compose_run "$PWD" exec -T db sh -lc 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT shop_id,COUNT(*) AS row_count,MIN(DATE(published_at)) AS min_date,MAX(DATE(published_at)) AS max_date FROM dwd_ozon_customer_voice_detail WHERE published_at >= \"2026-02-01\" AND published_at < \"2026-08-27\" GROUP BY shop_id ORDER BY shop_id;"'
```

### 11.4 广告 SKU ODS 与广告效率 DWD

```bash
compose_run "$PWD" exec -T db sh -lc 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT shop_id,COUNT(*) AS row_count,MIN(stat_date) AS min_date,MAX(stat_date) AS max_date FROM ods_ozon_adv_stats_product_daily WHERE stat_date BETWEEN \"2026-02-01\" AND \"2026-08-26\" GROUP BY shop_id ORDER BY shop_id;"'
```

```bash
compose_run "$PWD" exec -T db sh -lc 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT shop_id,COUNT(*) AS row_count,MIN(stat_date) AS min_date,MAX(stat_date) AS max_date FROM dwd_ozon_advert_efficiency_detail WHERE stat_date BETWEEN \"2026-02-01\" AND \"2026-08-26\" GROUP BY shop_id ORDER BY shop_id;"'
```

### 11.5 销售漏斗 DWD

非 Premium 示例按最近三个月验收：

```bash
compose_run "$PWD" exec -T db sh -lc 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT shop_id,COUNT(*) AS row_count,MIN(stat_date) AS min_date,MAX(stat_date) AS max_date FROM dwd_ozon_sales_funnel_detail WHERE stat_date BETWEEN \"2026-05-27\" AND \"2026-08-26\" GROUP BY shop_id ORDER BY shop_id;"'
```

MySQL 出现下面的提示是普通安全警告，不代表查询失败：

```text
mysql: [Warning] Using a password on the command line interface can be insecure.
```

不同 DWD 的业务粒度不同，不能直接比较不同表之间的总行数。没有订单、评价、退货或广告活动的店铺，对应表为 0 可能是正常结果。

## 12. 常见故障处理

### 12.1 `compose_run: command not found`

```bash
export KUNPENG_HOME="${KUNPENG_HOME:-$HOME/kunpeng}"
cd "$KUNPENG_HOME/current"
source scripts/lib/deploy-common.sh
```

随后用 `type compose_run` 检查。

### 12.2 外层显示 HTTP 500

终端中的 `urllib.error.HTTPError: HTTP Error 500` 只是统一同步路由的外层错误，真实原因在后端日志：

```bash
compose_run "$PWD" logs --since=2h backend 2>&1 | grep -E -i "Data type sync failed|HTTPStatusError|OperationalError|Traceback|500 Internal Server Error|同步失败:"
```

查看 Ozon 返回的具体响应：

```bash
compose_run "$PWD" logs --since=2h backend 2>&1 | grep -E "analytics/data|review/list|API客户端.*响应内容" | tail -n 80
```

### 12.3 日志全是 `/health 200`

健康检查会快速淹没尾部日志。过滤后再看：

```bash
compose_run "$PWD" logs --since=2h backend 2>&1 | grep -v "health" | tail -n 300
```

### 12.4 评价接口 403

如果响应说明当前订阅不能使用 `ReviewList`，需要在 Ozon Seller 后台确认评价接口订阅和 API Key 权限。反复重试不会解决。

### 12.5 广告同步很慢

广告 SKU 数据需要提交、轮询、下载 Ozon 异步报表，然后落 ODS、构建 DWD和翻译。六个店铺乘七个月就是 42 个窗口，耗时数小时并不异常。

不要并行运行多个 `advert_products`，否则容易触发 429 或“已有活跃报表任务”。

### 12.6 任务失败后的续跑

函数会在每个任务前显示：

```text
正在同步：analytics_data 店铺=7 日期=2026-07-01~2026-07-31
```

只重跑该店铺和日期：

```bash
ozon_sync analytics_data 7 2026-07-01 2026-07-31
```

ODS 和 DWD 使用业务唯一键更新，正常情况下重复执行同一窗口不会制造重复业务数据。

## 13. 生产操作安全原则

- 不执行 `DROP`、`TRUNCATE` 或无条件 `DELETE`；
- 不在服务器版本目录直接改代码；
- 不打印、复制或截图真实 `.env`、Token、数据库密码；
- 不并行运行 Ozon 广告或经营分析历史回填；
- 不因 `count=0` 就直接判断没有落库，必须查询 ODS 和 DWD；
- 不因 HTTP 200 就直接判断完成，必须同时检查业务返回、数据库和前端；
- 不直接恢复发布前数据库备份，避免覆盖发布后产生的新数据；
- 发布只使用 `repos/deploy/scripts/release.sh`，回滚只使用当前版本中的 `rollback.sh`。

## 14. 最简操作清单

### 正常发布

1. 本地前后端测试通过；
2. 有改动的前端、后端仓库分别提交并推送；
3. Git Bash 运行 `prepare-release.sh`；
4. 提交并推送 `kunpeng_deploy/release-lock.conf`；
5. 使用部署账号登录服务器，不执行 `sudo -i`；
6. 设置 `KUNPENG_HOME` 并进入 `repos/deploy`；
7. 只对 deploy 执行 `git pull --ff-only origin master`；
8. `bash scripts/release.sh`；
9. 检查 `current`、四个容器、迁移、体检和页面。

### Ozon 历史回填

1. 进入 `current` 并加载 `deploy-common.sh`；
2. 备份数据库；
3. 查询最新 Ozon 店铺 ID；
4. 定义 `ozon_sync`、`run_windows` 和日期窗口；
5. 商品 → 订单 → 退货 → 客户声音 → 广告 → 销售漏斗，逐项串行；
6. 非 Premium 销售漏斗只同步最近三个月；
7. 每项完成后查询 ODS、DWD，并在前端抽样导出验收。

---

维护原则：发布看脚本最终结果，同步看 API、ODS、DWD 三层结果，最后以生产页面和导出文件完成验收。
