# 定时任务（调度任务）文档

本文档记录项目中所有定时同步任务的执行时间、频率、任务说明以及测试方法。

> 数据窗口/实时性盘点与优化评估见：`docs/SYNC_SCHEDULE_ASSESSMENT.md`。

---

## 目录

- [架构概览](#架构概览)
- [任务清单](#任务清单)
  - [Wildberries 基础同步](#wildberries-基础同步)
  - [Ozon 同步](#ozon-同步)
- [技术实现](#技术实现)
- [测试方法](#测试方法)
  - [集成测试](#集成测试)
  - [命令行速查](#命令行速查)
- [常见问题](#常见问题)

---

## 架构概览

项目使用 **APScheduler 3.10**（`AsyncIOScheduler`）作为任务调度框架。调度器以全局单例形式存在于 `kunpeng.core.scheduler`，随 FastAPI 应用启动而启动。

```
┌─────────────────────────────────────────────┐
│           APScheduler (AsyncIOScheduler)    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Interval │  │  Cron    │  │  Date    │  │
│  │ Trigger  │  │ Trigger  │  │ Trigger  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       └─────────────┴─────────────┘         │
│                    │                        │
│           ┌────────┴────────┐               │
│           ▼                 ▼               │
│          sync_all_shops_*  (Job 函数)       │
│         (Job 函数)      (Job 函数)          │
└─────────────────────────────────────────────┘
```

**关键文件：**

| 文件 | 说明 |
|------|------|
| `src/kunpeng/core/scheduler.py` | 调度器核心封装（`TaskScheduler`） |
| `src/kunpeng/jobs/sync_wildberries.py` | WB 基础同步任务 |
| `src/kunpeng/jobs/sync_ozon.py` | Ozon 同步任务 |
| `src/kunpeng/main.py` | FastAPI 入口（注册并启动调度器） |
| `scripts/run_scheduler.py` | 独立启动调度器的脚本 |

---

## 任务清单

### Wildberries 基础同步

> 源文件：`src/kunpeng/jobs/sync_wildberries.py`

| 任务函数 | 频率 | Cron / Interval | 说明 |
|---------|------|----------------|------|
| `sync_all_shops_sales` | 每小时，启动后第 6 分钟首次执行 | `interval(minutes=60)` | 同步销售数据，回看 `sync.wb_orders_lookback_hours`（默认 24h） |
| `sync_all_shops_orders` | 每小时，启动后第 8 分钟首次执行 | `interval(minutes=60)` | 同步订单数据，回看 `sync.wb_orders_lookback_hours`（默认 24h） |
| `sync_all_shops_marketplace_orders` | 每小时，启动后第 16 分钟首次执行 | `interval(minutes=60)` | 同步 Marketplace 订单，回看 `sync.wb_marketplace_lookback_days`（默认 2 天） |
| `sync_all_shops_adverts` | 每天 | `0 2 * * *`（凌晨 2 点） | 同步广告活动列表及基础数据 |
| `sync_all_shops_finance` | 每天 | `0 9 * * *`（早上 9 点） | 同步财务数据，回补 `[今天-sync.finance_backfill_days, 昨天]`（默认 7 天，防延迟结算） |
| `sync_all_shops_feedbacks` | 每小时，启动后第 10 分钟首次执行 | `interval(minutes=60)` | 同步商品评价数据，供下游识别增量客户声音 |
| `sync_all_shops_feedback_pins` | 每天，启动后第 20 分钟补跑 | `0 3 * * *`（凌晨 3 点） | 分页同步昨天 00:00 至本次运行时刻的评价置顶及自动取消置顶记录 |
| `sync_all_shops_questions` | 每小时，启动后第 12 分钟首次执行 | `interval(minutes=60)` | 同步商品问答数据，供下游识别增量客户声音 |
| `sync_all_shops_funnel` | 每天 | `0 4 * * *`（凌晨 4 点） | 同步销售漏斗数据 |
| `sync_all_shops_returns` | 每小时，启动后第 14 分钟首次执行 | `interval(minutes=60)` | 同步退货商品明细，供下游识别增量退货 |
| `sync_all_shops_return_claims` | 每小时，启动时立即执行 | `interval(minutes=60)` | 同步买家退货申请；按 `dt_update`（缺失时用 `dt`）筛选最近 1 小时 |
| `sync_all_shops_chat_events` | 每小时，启动后第 2 分钟首次执行 | `interval(minutes=60)` | 同步买家聊天事件；窗口为莫斯科时间昨天 00:00 至本次运行时刻 |
| `sync_all_shops_order_metadata` | 每天，启动后第 22 分钟补跑 | `5 3 * * *`（凌晨 3:05） | 用现有 Marketplace 订单 ID 补全 FBS 订单元数据 |
| `sync_all_shops_fbs_supplies` | 每天，启动后第 24 分钟补跑 | `10 3 * * *`（凌晨 3:10） | 分页同步全部 FBS 供货单；统计昨天 00:00 至本次运行时刻 |
| `sync_all_shops_reshipment_orders` | 每天，启动后第 26 分钟补跑 | `15 3 * * *`（凌晨 3:15） | 对账当前需重新发货的 FBS 订单快照；统计昨天 00:00 至本次运行时刻的状态变化 |
| `sync_all_shops_balance` | 每天 | `0 8 * * *`（早上 8 点） | 同步店铺余额 |
| `sync_all_shops_chat_events` | 每小时，启动时立即执行 | `interval(minutes=60)` | 同步买家聊天事件；窗口为莫斯科时间昨天 00:00 至本次运行时刻 |
| `sync_all_shops_order_metadata` | 每天，启动时立即执行 | `0 3 * * *`（凌晨 3 点） | 用现有 Marketplace 订单 ID 补全 FBS 订单元数据 |
| `sync_all_shops_fbs_supplies` | 每天，启动时立即执行 | `0 3 * * *`（凌晨 3 点） | 分页同步全部 FBS 供货单；统计昨天 00:00 至本次运行时刻 |
| `sync_all_shops_reshipment_orders` | 每天，启动时立即执行 | `0 3 * * *`（凌晨 3 点） | 对账当前需重新发货的 FBS 订单快照；统计昨天 00:00 至本次运行时刻的状态变化 |
| `sync_all_shops_balance` | 每天 | `0 8 * * *`（早上 8 点） | 同步推广账户余额 |
| `sync_all_shops_seller_balance` | 每天 | `0 3 * * *`（凌晨 3 点） | 同步财务域卖家当前余额，每店铺每天保存一份快照 |
| `sync_all_shops_sales_report_list` | 每周一 | `5 3 * * mon`（凌晨 3:05） | 同步上一自然周（周一至周日）的财务报表列表 |
| `sync_all_shops_region_sales` | 每天 | `5 3 * * *`（凌晨 3:05） | 同步最近 2 个已结束完整平台日的区域销售聚合报告 |
| `sync_all_shops_search_traffic` | 每天 | `15 3 * * *`（凌晨 3:15） | 同步最近 7 个已结束完整平台日的商品搜索流量 |
| `sync_all_shops_product_search_texts` | 每天 | `35 3 * * *`（凌晨 3:35） | 同步最近 2 个已结束完整平台日的商品自然搜索词报告 |
| `sync_all_shops_advert_stats_hourly` | 每小时 | `5 * * * *`（每小时第 5 分） | 广告统计按小时维度增量同步，支持跨天边界 |
| `sync_all_shops_search_cluster_stat_hourly` | 每小时 | `7 * * * *`（每小时第 7 分） | 搜索关键字统计按小时维度增量同步，支持跨天边界 |

**注册函数：** `register_wildberries_jobs()`（`production` 环境或 `jobs_enabled=True` 时生效）。
WB 全部任务（含上面两个小时级任务）已统一在此函数中注册。

**卖家余额快照说明：**
- 数据来自 Finance API 的 `GET /api/v1/account/balance`。
- 该接口只返回调用时的当前余额，不支持传入日期范围，因此任务不能回补历史日期。
- 数据保存到 `ods_wb_finance_seller_balance`，以 `shop_id + snapshot_date` 唯一约束幂等更新。
- `snapshot_date` 和凌晨 3 点的触发时间均使用项目统一的平台时区（默认 `Europe/Moscow`）。

**财务报表列表说明：**
- 数据来自 Finance API 的 `POST /api/finance/v1/sales-reports/list`，请求 `period=weekly`。
- 每周一 03:05 按平台时区计算上一自然周，即上周一至上周日的闭区间。
- 数据保存到 `ods_wb_sales_report_list`，以 `shop_id + report_id` 唯一约束幂等更新，不覆盖 `ods_wb_sales_reports` 财务明细。
- 单页最多 1000 份报表，通过 `limit + offset` 分页；需要翻页时遵守每个卖家账户每分钟 1 次的接口限制。
- 03:05 同时存在 Analytics 等其他域名任务；本任务使用 Finance API，与 03:00 的卖家余额任务间隔 5 分钟。

**区域销售报告说明：**
- 数据来自 Analytics API 的 `GET /api/v1/analytics/region-sale`。
- 默认窗口为 `[平台今天-2天, 平台昨天]`，即最近两个已结束的完整平台日。
- 数据保存到 `ods_wb_finance_region_sales`，按店铺、查询窗口和地区商品维度幂等更新。
- 窗口天数由 `sync.wb_region_sales_lookback_days` 控制，允许范围为 1 至 31 天。

**商品搜索词报告说明：**
- 数据来自 Analytics API 的 `POST /api/v2/search-report/product/search-texts`；先通过 `POST /api/v2/search-report/table/details` 分页发现店铺商品。
- 默认窗口为 `[平台今天-2天, 平台昨天]`，即最近两个已结束的完整平台日。
- 商品按最多 50 个一批查询，请求间隔至少 20 秒，避免触发平台的 3 次/分钟限制。
- 数据保存到 `ods_wb_traffic_product_search_texts`，按店铺、窗口、商品、标准化搜索词哈希和排序指标幂等更新。
- 默认按打开商品卡次数取每个商品前 30 个搜索词，供 SEO、商品运营和广告选词分析使用。
- 该接口要求店铺令牌包含 Analytics 权限并开通 Jam；权限或订阅不足时任务会记录失败，不会写入半批数据。

**商品搜索流量说明：**
- 数据来自 Analytics API 的 `POST /api/v2/search-report/table/details`。
- 默认窗口为 `[平台今天-7天, 平台昨天]`，保存的是滚动 7 天汇总快照。
- 同时传入紧邻的前 7 天作为 `pastPeriod`，例如当前周期为 7 月 17 日至 23 日时，对比周期为 7 月 10 日至 16 日，用于计算排名、流量和转化指标变化。
- 数据保存到 `ods_wb_traffic_search_traffic`，按店铺、窗口、商品和搜索位置分组幂等更新。
- 相邻窗口存在日期重叠，下游用于趋势比较，不能把多个滚动窗口直接相加。
- 任务使用 `positionCluster=all` 并按每页最多 1000 个商品分页，供商品运营、SEO、广告运营和 BI 分析搜索排名、打开商品卡、加购、下单及转化表现。
- 为避免与相同接口的商品搜索词任务竞争额度，区域销售、搜索流量、商品搜索词依次在 3:05、3:15、3:35 错峰执行。

**小时级任务核心逻辑：**
- 广告小时统计在每小时第 5 分钟执行，搜索关键字小时统计在第 7 分钟执行，均统计上一个整点的数据
- 跨天边界处理：00:05 执行时，结算的是 **昨天 23:00** 的数据
- 增量计算：当前小时 API 累计值 − 之前小时已同步累计值，幂等写入

**买家退货申请任务：**

- 数据源：`GET https://returns-api.wildberries.ru/api/v1/claims`
- 接口只返回最近 14 天且不支持时间范围参数，因此分别分页拉取
  `is_archive=false` 和 `is_archive=true`，再在本地筛选最近一小时内新增或更新的申请
- 使用 `(shop_id, claim_id)` 唯一键写入 `ods_wb_return_claims`；重复同步时更新状态和原始 JSON，不新增重复行、不删除历史数据
- 调度进程启动后立即执行一次，之后每 60 分钟执行
- 店铺令牌必须包含 `Buyers Returns` 权限；Personal/Service 令牌可满足两类数据分页请求

**买家聊天事件任务：**

- 数据源：`GET https://buyer-chat-api.wildberries.ru/api/v1/seller/events`
- 使用毫秒级 `next` 游标，从莫斯科时间昨天 00:00 开始分页，直到响应中的
  `totalEvents=0`；本地再次按 `[昨天 00:00, 本次运行时刻)` 过滤
- 使用 `(shop_id, event_id)` 唯一键写入 `ods_wb_voc_chat_events`；重叠窗口重复
  同步时更新消息、附件元数据及原始 JSON，不新增重复行、不删除历史数据
- 只保存附件元数据、URL 和下载 ID，不自动下载附件文件，也不自动回复买家
- 调度进程启动后第 2 分钟执行一次，之后每 60 分钟执行
- 店铺令牌必须包含 `Buyers Chat` 权限，并使用 Personal/Service 类型以支持分页

**评价置顶记录任务：**

- 数据源：`GET https://feedbacks-api.wildberries.ru/api/feedbacks/v1/pins`
- 接口没有日期参数；分别使用 `state=pinned` 和 `state=unpinned` 获取置顶及平台自动取消置顶的记录，每页最多 500 条，使用响应中的 `next` 操作游标完整分页
- 莫斯科时间窗口为 `[昨天 00:00, 本次运行时刻)`；完整拉取后按 `changeStateAt` 在本地筛选该窗口
- 使用 `(shop_id, pin_id)` 唯一键写入 `ods_wb_voc_feedback_pins`；重复同步只更新状态、取消原因、原始 JSON 和最近同步时间，不新增重复行、不删除历史记录
- 可通过 `(shop_id, feedback_id)` 与 `ods_wb_feedbacks` 联查评价正文；任务只读，不自动置顶或取消置顶
- 调度进程启动后第 20 分钟补跑一次，之后每天莫斯科时间凌晨 3 点执行
- 店铺令牌必须包含 `Feedbacks and Questions` 类目权限

**FBS 订单元数据任务：**

- 订单 ID 来源：`ods_wb_marketplace_orders`，不额外创建重复的订单主表
- 本地订单窗口：莫斯科时间 `[昨天 00:00, 本次运行时刻)`，回看天数可配置
- 数据源：`POST https://marketplace-api.wildberries.ru/api/marketplace/v3/orders/meta`
- 每批最多提交 100 个订单 ID，保存 `metaDetails`、兼容期内的 `meta` 和完整原始 JSON
- 使用 `(shop_id, order_id)` 唯一键写入 `ods_wb_order_metadata`；重复同步只更新元数据和最近同步时间，不删除历史数据
- 调度进程启动后第 22 分钟补跑一次，之后每天莫斯科时间凌晨 3:05 执行
- 店铺令牌必须包含 `Marketplace` 类目权限

**FBS 供货单任务：**

- 数据源：`GET https://marketplace-api.wildberries.ru/api/v3/supplies`
- 接口不支持日期参数，使用 `limit=1000` 和响应中的 `next` 游标完整分页
- 全部供货单均写入或刷新，避免漏掉以前创建、今天才关闭或扫描的供货单；
  同时按创建、关闭或扫描时间统计莫斯科时间 `[昨天 00:00, 本次运行时刻)`
- 使用 `(shop_id, supply_id)` 唯一键写入 `ods_wb_order_fbs_supplies`；重复同步更新
  状态和原始 JSON，保留首次发现时间，不删除历史数据
- 调度进程启动后第 24 分钟补跑一次，之后每天莫斯科时间凌晨 3:10 执行
- 店铺令牌必须包含 `Marketplace` 类目权限

**FBS 重新发货订单任务：**

- 数据源：`GET https://marketplace-api.wildberries.ru/api/v3/supplies/orders/reshipment`
- 接口不支持日期和分页参数，返回当前仍需重新发货的全部 FBS 组装订单快照
- 使用 `(shop_id, order_id, supply_id)` 唯一键写入 `ods_wb_order_reshipment_orders`；重复同步更新原始 JSON 和最近发现时间，不新增重复行
- 只在接口成功且响应结构有效后执行快照对账：本次仍存在的订单标记为 `is_active=true`，之前存在但本次消失的订单标记为已解决并记录 `resolved_at`；接口失败不会误关闭现有记录
- 不物理删除历史记录；莫斯科时间 `[昨天 00:00, 本次运行时刻)` 仅用于统计首次发现、重新激活或解决等状态变化
- 调度进程启动后第 26 分钟补跑一次，之后每天莫斯科时间凌晨 3:15 执行
- 店铺令牌必须包含 `Marketplace` 类目权限

---

### Ozon 同步

> 源文件：`src/kunpeng/jobs/sync_ozon.py`

| 任务函数 | 频率 | Cron / Interval | 说明 | 状态 |
|---------|------|----------------|------|------|
| `sync_all_shops_postings` | 每小时，启动后第 3 分钟首次执行 | `interval(minutes=60)` | 同步 Ozon 订单数据，回看 `sync.ozon_postings_lookback_days`（默认 3 天） | ✅ 已启用 |
| `sync_all_shops_fbo_postings` | 每小时，启动后第 5 分钟首次执行 | `interval(minutes=60)` | 同步 Ozon FBO 订单数据，回看 `sync.ozon_fbo_lookback_days`（默认 3 天） | ✅ 已启用 |
| `sync_all_shops_unfulfilled_postings` | 每小时，启动后第 1 分钟首次执行 | `interval(minutes=60)` | 使用 v4 游标完整分页；截止时间窗口为莫斯科时间昨天 00:00 至本次运行时刻 | ✅ 已启用 |
| `sync_all_shops_returns` | 每小时，启动后第 7 分钟首次执行 | `interval(minutes=60)` | 同步 Ozon 退货数据，回看 `sync.ozon_returns_lookback_days`（默认 2 天） | ✅ 已启用 |
| `sync_all_shops_reviews` | 每小时，启动后第 9 分钟首次执行 | `interval(minutes=60)` | 同步 Ozon 评价数据；未开通订阅时会明确记录 403 业务失败，不会重试永久权限错误 | ✅ 已启用 |
| `sync_all_shops_finance` | 每天 | `20 3 * * *`（凌晨 3:20） | 同步 Ozon 财务应计数据，回补 `[今天-sync.finance_backfill_days, 昨天]`（默认 7 天） | ✅ 已启用 |
| `sync_all_shops_accrual_types` | 每天 | `10 4 * * *`（凌晨 4:10） | 同步 Ozon 应计类型维度字典 | ✅ 已启用 |
| `sync_all_shops_products` | 每天 | `30 4 * * *`（凌晨 4:30） | 同步 Ozon 商品信息维度（全量分页） | ✅ 已启用 |
| `translate_ozon_product_names` | 每天 | `45 4 * * *`（凌晨 4:45） | 使用持久化缓存按店铺和 SKU 回填中文商品名称 | ✅ 已启用 |
| `sync_all_shops_adverts` | 每天 | `0 5 * * *`（凌晨 5 点） | 同步 Ozon 广告数据（Performance API，近 7 天） | ✅ 已启用 |
| `sync_all_shops_advert_products` | 每天 | `30 5 * * *`（凌晨 5:30） | 同步 Ozon 广告 SKU 明细（异步报表，耗时，近 7 天） | ✅ 已启用 |
| `sync_all_shops_analytics_data` | 每天 | `0 7 * * *`（上午 7 点） | 同步 Ozon 经营分析 SKU 日数据，回补最近 7 个完整平台日 | ✅ 已启用 |
| `sync_all_shops_advert_products_hourly` | 每小时 | `10 * * * *`（每小时第 10 分） | 同步广告 SKU 当天累计并折算当前小时增量 | ✅ 已启用 |

> ✅ 当前 Ozon 定时任务在 `register_ozon_jobs()` 中已**全部启用**并注册到调度器。

当前共注册 **13 个 Ozon 任务**。订单、退货、评价、广告和经营分析 ODS 同步成功后，还会在对应服务链路中即时构建相关 DWD；这些 DWD 构建步骤不单独占用调度任务数量。

**商品名称翻译缓存：**

- `ozon_translate_product_names_daily` 每天 04:45 运行，在 04:30 商品维度同步之后执行。
- 结果按 `(shop_id, sku)` 写入 `dwd_ozon_product_name_translation_cache`，相同店铺 SKU 不重复自动翻译。
- 缓存供订单、退货、客户声音、广告效率和销售漏斗 DWD 复用。

**注册函数：** `register_ozon_jobs()`（`production` 环境或 `jobs_enabled=True` 时生效）

**经营分析 SKU 日任务：**

- 数据源：`POST https://api-seller.ozon.ru/v1/analytics/data`，固定维度 `sku + day`。
- 18 个源指标分为 14 项核心指标和 4 项履约指标两次请求，再按 `(shop_id, sku, stat_date)` 合并；不在 ODS 计算派生比例。
- 每页 `limit=1000`，按 `offset` 完整分页；同一店铺两次请求之间至少间隔 65 秒，HTTP 429 最多重试 3 次。
- 最近 7 个已结束的莫斯科平台日幂等写入 `ods_ozon_analytics_data_daily`，请求窗口 totals 写入 `ods_ozon_analytics_totals_window`。
- 两组指标全部拉取并校验成功后才提交；任一组或任一页失败则该店铺整轮回滚，避免半批数据。

**FBS 未履约订单任务：**

- 数据源：`POST https://api-seller.ozon.ru/v4/posting/fbs/unfulfilled/list`
- `cutoff_from/cutoff_to` 表示履约截止时间，不是订单创建时间；每次窗口为平台时区
  （默认 `Europe/Moscow`）昨天 00:00 到本次任务实际运行时刻，不扩展到当天 23:59:59
- 使用响应根节点的 `cursor` 和 `has_next` 完整分页；最多 500 页，并拦截空游标和
  重复游标，避免死循环
- 使用 `(shop_id, posting_number)` 唯一键原子 upsert 到
  `ods_ozon_order_unfulfilled_postings`；更新订单现状和原始 JSON，但不覆盖
  `first_seen_at`
- 只有某店铺本轮所有 API 页都成功后才执行状态对账；仍返回的订单更新
  `last_seen_at`、设为 `is_active=true` 并清空 `resolved_at`；v4 返回记录本身
  不带 cutoff 字段，因此该店铺以前有效但从本轮完整结果中消失的订单设为
  `is_active=false` 并记录 `resolved_at`
- API 请求、响应解析或分页失败时整轮回滚，不会误把已有订单标记为已解决；历史记录
  始终保留，不物理删除
- 调度进程启动后立即执行一次，之后每 60 分钟执行

---

## 技术实现

### 环境限制

所有 `register_*_jobs()` 函数都有环境判断：

```python
if settings.environment != "production" and not settings.jobs_enabled:
    logger.info("当前环境非 production 且 jobs_enabled=False，跳过注册定时任务")
    return
```

即 **`environment=production` 或 `jobs_enabled=True` 时才注册**。默认 `environment=development`、`jobs_enabled=False`，因此开发环境启动 FastAPI 不会自动注册定时任务，避免开发时意外触发；如需在非生产环境调试调度，可显式设置 `jobs_enabled=True`。

### 调度器配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `misfire_grace_time`（interval） | 2 小时 | 小时/间隔任务在电脑短时休眠后合并补跑一次 |
| `misfire_grace_time`（cron） | 12 小时 | 每日任务在当天恢复运行后合并补跑一次 |
| `coalesce` | `True` | 错过多个执行点时合并为一次 |
| `max_instances` | 1 | 同一任务同时只能有一个实例运行 |

调度函数返回 `status=error`、`partial*` 或非空 `failed_campaigns` 时，调度包装层会抛出业务失败，让 APScheduler 将该次执行标记为失败；不再只显示“函数正常返回”。电脑关机期间无法实际执行任务，宽限期只负责在电脑恢复后补跑最新一次。

### 同步窗口配置

各任务的取数窗口已在 job 层显式传参，并由 `settings.sync`（`SyncSettings`）统一管理，可通过 `.env` 以 `sync_` 前缀覆盖：

| 配置项 | 默认值 | 作用任务 |
|------|-----|------|
| `sync_wb_orders_lookback_hours` | `24` | WB sales / orders 回看小时数 |
| `sync_wb_marketplace_lookback_days` | `2` | WB marketplace_orders 回看天数 |
| `sync_wb_region_sales_lookback_days` | `2` | WB 区域销售报告已结束完整平台日数量 |
| `sync_wb_product_search_texts_lookback_days` | `2` | WB 商品搜索词报告已结束完整平台日数量 |
| `sync_wb_search_traffic_lookback_days` | `7` | WB 商品搜索流量滚动窗口的完整平台日数量 |
| `sync_wb_return_claims_lookback_hours` | `1` | WB 买家退货申请按更新时间回看小时数 |
| `sync_wb_chat_events_lookback_days` | `1` | WB 买家聊天事件从 N 天前零点回看到本次运行时刻 |
| `sync_wb_order_metadata_lookback_days` | `1` | WB 订单元数据从 N 天前零点回看到本次运行时刻 |
| `sync_wb_reshipment_lookback_days` | `1` | WB 重新发货订单状态变化从 N 天前零点统计到本次运行时刻 |
| `sync_wb_feedback_pins_lookback_days` | `1` | WB 评价置顶记录从 N 天前零点回看到本次运行时刻 |
| `sync_ozon_postings_lookback_days` | `3` | Ozon postings 回看天数 |
| `sync_ozon_fbo_lookback_days` | `3` | Ozon fbo_postings 回看天数 |
| `sync_ozon_returns_lookback_days` | `2` | Ozon returns 回看天数 |
| `sync_ozon_analytics_lookback_days` | `7` | Ozon 经营分析回补的完整平台日数量（允许 1 至 31 天） |
| `sync_finance_backfill_days` | `7` | WB / Ozon 财务任务回补天数（防延迟结算） |

说明：
- **每小时任务窗口已收敛**（Ozon 订单原先兜底 30 天 → 现默认 3 天），靠幂等 upsert 去重，显著降低 API/DB 压力。
- **财务任务改为回补窗口** `[今天-N, 昨天]`（默认 7 天），覆盖平台 T+1 延迟结算，幂等写入不会重复计数。
- 调窗口无需改代码，改 `.env` 后重启应用即可生效。

### 独立运行调度器

```bash
poetry run python -m kunpeng.scheduler_main
```

该入口以独立进程启动调度器，适用于将调度器与 Web 服务分开部署的场景；API worker 应设置 `RUN_SCHEDULER=false`。

---

## 测试方法

### 集成测试

所有调度任务都编写了 pytest 集成测试，位于：

```
tests/integration/test_jobs.py
```

共 **32 个**集成测试，真实调用 API 并写入数据库。

| Mark | 数量 | 筛选命令 |
|------|------|---------|
| `integration` | 32 | 全部集成测试 |
| `wb` | 23 | Wildberries 任务（含财务报表、搜索流量、买家退货申请、买家聊天、评价置顶、订单元数据、FBS 供货单和重新发货订单） |
| `ozon` | 9 | Ozon 任务 |
| `hourly` | 4 | 小时级同步任务（同时带 `wb` mark） |

### 命令行速查

```bash
cd /path/to/backend

# ── 查看所有可测试的任务 ──
poetry run pytest tests/integration/test_jobs.py --collect-only

# ── 运行全部集成测试 ──
poetry run pytest tests/integration/test_jobs.py -v -s

# ── 只测试 Wildberries 任务 ──
poetry run pytest tests/integration/test_jobs.py -v -m wb -s

# ── 只测试 Ozon 任务 ──
poetry run pytest tests/integration/test_jobs.py -v -m ozon -s

# ── 只测试小时级任务 ──
poetry run pytest tests/integration/test_jobs.py -v -m hourly -s

# ── 测试单个指定任务 ──
poetry run pytest tests/integration/test_jobs.py -v -k sales -s

# ── 测试多个指定任务 ──
poetry run pytest tests/integration/test_jobs.py -v -k "sales or orders" -s

# ── 跳过集成测试（只跑单元测试）──
poetry run pytest -v -m "not integration"
```

> `-s` 参数用于显示 `print` / `logging` 输出，便于观察真实 API 调用结果。

### 查看 DEBUG 日志

API 客户端（`clients/wildberries.py`、`clients/base.py`）中有大量 `logger.debug()` 日志，记录了请求头、响应解析、限流等待等细节。默认不显示，可通过以下方式开启：

```bash
# 显示 DEBUG 及以上级别的所有日志
poetry run pytest tests/integration/test_jobs.py -v -k sales \
  --log-cli-level=DEBUG -s

# 自定义日志格式
poetry run pytest tests/integration/test_jobs.py -v -k sales \
  --log-cli-level=DEBUG \
  -o "log_cli_format=%(asctime)s [%(levelname)s] %(name)s: %(message)s" \
  -s
```

查看 SQLAlchemy 执行的 SQL：

```bash
# 在测试 / 脚本中加入
import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)   # 显示 SQL
logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)  # 显示 SQL + 参数
```

> 后端服务运行时，DEBUG 日志由 `.env` 中的 `DEBUG=true` 控制（见 `core/logging.py`）。

### 直接调用 Job 函数

如果需要临时手动触发某个任务（如排查问题），也可以直接调用 Job 函数：

```python
import asyncio
from kunpeng.jobs.sync_wildberries import sync_all_shops_sales

async def manual_trigger():
    result = await sync_all_shops_sales()
    print(result)

asyncio.run(manual_trigger())
```

> ⚠️ 这会真实调用 API 并写入数据库，请确保环境配置正确。

---

## 常见问题

### Q: 为什么开发环境不注册定时任务？

A: 防止开发过程中频繁触发 API 调用，避免浪费 API 配额和干扰生产数据。测试时通过 pytest 或手动调用即可。若确实需要在非生产环境验证调度，可设置 `jobs_enabled=True` 强制注册。

### Q: 如何临时在生产环境禁用某个任务？

A: 可以注释掉 `register_*_jobs()` 中对应的 `scheduler.add_*_job()` 调用，或者通过独立脚本 `run_scheduler.py` 的代码移除指定 job。

### Q: 任务执行失败了怎么办？

A: 查看日志中的 `[定时任务]` 前缀日志，每个任务函数内部都包裹了 `try/except`，失败时会记录具体错误信息但不会影响其他任务。

### Q: 如何修改任务执行时间？

A: 修改对应 `register_*_jobs()` 函数中的 Cron 表达式或 interval 参数，然后重启应用即可。

### Q: 数据库连接失败会怎样？

A: 任务执行时会创建独立的数据库会话（`AsyncSessionLocal`），连接失败会记录异常并返回错误结果，不会导致调度器崩溃。

### Q: 集成测试报错 `attached to a different loop` 怎么办？

A: 这是 SQLAlchemy async engine 连接池跨 event loop 的问题。

**原因：** 全局 `engine` 的连接池会缓存连接并绑定到首个使用它的 event loop，而 pytest-asyncio 默认为每个测试函数创建独立的 event loop，导致第二个测试复用旧连接时报错。表现为：第一个任务测试通过，第二个开始报 `RuntimeError: ... got Future ... attached to a different loop`。

**解决方案：** 已在 `tests/integration/conftest.py` 中通过 `autouse` fixture 解决——每个测试前后调用 `engine.dispose()` 释放连接池，强制每个测试使用全新连接：

```python
import pytest_asyncio
from kunpeng.core.database import engine

@pytest_asyncio.fixture(autouse=True)
async def reset_engine_pool():
    await engine.dispose()
    yield
    await engine.dispose()
```

该 fixture 仅作用于集成测试目录，不影响生产代码，且自动应用到所有测试，无需逐个标注。

---

*最后更新：2026-08-07*
