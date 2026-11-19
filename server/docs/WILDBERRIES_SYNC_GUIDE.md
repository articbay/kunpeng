# Wildberries 数据同步指南

本指南介绍如何使用 Wildberries（WB）数据同步功能，结构与 `docs/OZON_SYNC_GUIDE.md` 对齐，便于对照查阅。

> 相关文档：定时任务见 `docs/SCHEDULED_JOBS.md`，同步窗口/实时性评估见 `docs/SYNC_SCHEDULE_ASSESSMENT.md`，表字段明细见 `docs/数据库表结构文档.md`。

## 目录

1. [概述](#概述)
2. [两套同步入口](#两套同步入口)
3. [API 端点列表](#api-端点列表)
4. [数据库表设计](#数据库表设计)
5. [配置说明](#配置说明)
6. [使用示例](#使用示例)
7. [调试和测试](#调试和测试)
8. [相关文件](#相关文件)

---

## 概述

Wildberries 数据同步模块实现了完整的 ODS 层（操作数据存储），从 WB 平台同步以下数据：

- 销售数据（Sales）
- 订单数据（Orders）
- Marketplace 订单及状态历史（FBS Orders）
- 新订单/待处理组装订单（New Orders）
- FBS 订单元数据、供货单和重新发货订单状态
- 销售漏斗（Sales Funnel）
- 退货数据（Returns）
- 买家退货申请（Buyers Returns）
- 广告数据（活动 / 商品 / 预算 / 统计 / 搜索关键字统计）
- 广告小时统计、搜索关键字小时统计（Hourly）
- 评价数据（Feedbacks）
- 评价置顶及自动取消置顶记录（Feedback Pins）
- 问答数据（Questions）
- Buyer Chat 买家聊天事件（Chat Events）
- 财务销售报告（Finance Sales Report）
- 店铺余额与 Cashback（Balance）

数据流向：`WB API → WildberriesClient → WBSyncService → CRUD → MySQL`。WB API 返回 camelCase 字段，写入模型时统一转 snake_case。

---

## 两套同步入口

WB 同步对外有两套 HTTP 入口，底层都走 `WBSyncService`，按需选用：

| 入口 | 路由前缀 | 特点 | 适用场景 |
|------|----------|------|----------|
| WB 专用路由 | `/api/v1/wildberries` | 覆盖最全，含 balance、adverts-hourly、search-cluster-hourly 等专有子接口 | 手动排查、需要触发小时级/余额等专有同步 |
| 通用平台路由 | `/api/v1/platforms/wildberries` | 与 Ozon 对称的统一接口，靠 `data_type` 参数化 | 多平台统一调度、脚本批量触发 |

> 两套入口都对当前登录会话临时放开了鉴权（见路由内注释），生产环境请勿直接暴露到公网。

---

## API 端点列表

### 一、WB 专用路由（`/api/v1/wildberries`）

#### 1. 全量同步

```
POST /api/v1/wildberries/sync
```

请求体（JSON，`WBSyncRequest`）：

```json
{
  "shop_id": 1,
  "date_from": "2026-05-01",
  "date_to": "2026-05-23",
  "sync_types": ["sales", "orders", "finance"]
}
```

- `shop_id`：店铺 ID（必填）
- `date_from` / `date_to`：日期区间（`YYYY-MM-DD`，可选）
- `sync_types`：要同步的类型数组（可选）。**不传时默认同步**：`sales`、`orders`、`funnel`、`returns`、`adverts`、`feedbacks`、`questions`、`finance`、`marketplace_orders`、`balance`。

响应示例：

```json
{
  "status": "success",
  "message": "数据同步完成",
  "synced_count": { "sales": 120, "orders": 130, "finance": 45 }
}
```

#### 2. 按类型单独同步

下列端点都接收查询参数 `shop_id`（必填）、`date_from`、`date_to`（可选），返回统一的 `MessageResponse`：

| 端点 | 说明 |
|------|------|
| `POST /api/v1/wildberries/sync/sales` | 仅同步销售数据 |
| `POST /api/v1/wildberries/sync/orders` | 仅同步订单数据 |
| `POST /api/v1/wildberries/sync/funnel` | 仅同步销售漏斗数据 |
| `POST /api/v1/wildberries/sync/returns` | 仅同步退货数据 |
| `POST /api/v1/wildberries/sync/marketplace-orders` | 仅同步 Marketplace 订单 |
| `POST /api/v1/wildberries/sync/finance` | 仅同步财务销售报告 |
| `POST /api/v1/wildberries/sync/finance-daily` | 仅同步 `period=daily` 的按日财务销售报告 |
| `POST /api/v1/wildberries/sync/adverts` | 仅同步广告（活动 + 商品 + 预算 + 搜索关键字统计） |

不接收日期参数（内部按当前口径计算）的专有端点：

| 端点 | 说明 |
|------|------|
| `POST /api/v1/wildberries/sync/balance` | 仅同步余额与 cashback（`shop_id` 必填） |
| `POST /api/v1/wildberries/sync/adverts-hourly` | 手动触发广告统计小时同步 |
| `POST /api/v1/wildberries/sync/search-cluster-hourly` | 手动触发搜索词统计小时同步 |

示例：

```bash
curl -X POST "http://localhost:8000/api/v1/wildberries/sync/sales?shop_id=1&date_from=2026-05-01&date_to=2026-05-23"
```

> 注：数据查询接口（`GET /sales`、`GET /orders` 等）已从路由中移除，分析师直接连接数据库查询 ODS 层表。

### 二、通用平台路由（`/api/v1/platforms`）

与 Ozon 共用的统一接口。

#### 1. 列出所有平台

```
GET /api/v1/platforms
```

响应：`{"platforms": ["wildberries", "ozon"]}`

#### 2. 列出 WB 支持的数据类型

```
GET /api/v1/platforms/wildberries/data-types
```

响应：

```json
{
  "platform": "wildberries",
  "data_types": [
    "sales", "orders", "funnel", "returns", "adverts",
    "feedbacks", "questions", "finance", "marketplace_orders"
  ]
}
```

> 注意：通用路由的 `data_types` 覆盖 9 种，**不含** `balance` 及小时级同步（`adverts-hourly` / `search-cluster-hourly`）。这些只能走 WB 专用路由或定时任务。
>
> 买家退货申请、Buyer Chat、订单元数据、FBS 供货单、重新发货订单和评价置顶记录目前是**仅定时任务同步**，尚未开放对应的手动 HTTP 路由。

#### 3. 同步全部 / 指定类型

```
POST /api/v1/platforms/wildberries/sync
POST /api/v1/platforms/wildberries/sync/{data_type}
```

查询参数：`shop_id`（必填）、`date_from`、`date_to`（可选，缺省时默认近 7 天）。

```bash
curl -X POST "http://localhost:8000/api/v1/platforms/wildberries/sync/sales?shop_id=1&date_from=2026-05-01&date_to=2026-05-23"
```

---

## 数据库表设计

WB 当前共有 **39 张 ODS 表**和 **9 张 DWD 表**。ODS 主要使用前缀 `ods_wb_`，DWD 使用前缀 `dwd_wb_`；少量已落地表名含中文业务板块，本文按当前真实 `__tablename__` 记录，不在文档修改中重命名。

### 订单 / 销售

| 表名 | 说明 |
|------|------|
| `ods_wb_supplier_sales` | 供应商销售明细 |
| `ods_wb_supplier_orders` | 供应商订单明细 |
| `ods_wb_marketplace_orders` | Marketplace（FBS）订单主表 |
| `ods_wb_marketplace_order_status_histories` | Marketplace 订单状态变更历史 |
| `ods_wb_new_orders` | 新订单/待处理组装订单（供下游提醒） |
| `ods_wb_order_metadata` | 使用 Marketplace 订单 ID 补全的 FBS 订单元数据 |
| `ods_wb_order_fbs_supplies` | FBS供货单及其当前生命周期状态 |
| `ods_wb_order_reshipment_orders` | 当前及历史需重新发货的FBS订单状态 |

### 运营分析

| 表名 | 说明 |
|------|------|
| `ods_wb_sales_funnels` | 销售漏斗统计 |
| `ods_wb_goods_returns` | 退货明细 |

### 客户声音 / 售后

| 表名 | 说明 |
|------|------|
| `ods_wb_return_claims` | 买家退货申请及处理状态 |
| `ods_wb_feedbacks` | 商品评价 |
| `ods_wb_voc_feedback_pins` | 评价置顶及自动取消置顶操作记录 |
| `ods_wb_questions` | 商品问答 |
| `ods_wb_voc_chat_events` | Buyer Chat 买家聊天事件及关联商品/订单信息 |

### 广告

| 表名 | 说明 |
|------|------|
| `ods_wb_adverts` | 广告活动基础信息 |
| `ods_wb_advert_product` | 广告商品明细 |
| `ods_wb_advert_budget` | 广告预算 |
| `ods_wb_advert_stats` | 广告统计（商品维度，日级） |
| `ods_wb_advert_stats_hourly` | 广告统计（小时维度增量） |
| `ods_wb_search_cluster_stat` | 搜索关键字统计（日级） |
| `ods_wb_search_cluster_stat_hourly` | 搜索关键字统计（小时维度增量） |
| `ods_wb_norm_query_bids` | 标准查询竞价 |
| `ods_wb_norm_query_minus` | 排除关键词 |
| `ods_wb_norm_query_list` | 标准查询列表 |
| `ods_wb_norm_query_stats` | 标准查询统计 |
| `ods_wb_promotion_counts` | 促销计数 |
| `ods_wb_bid_recommendations` | 竞价推荐 |
| `ods_wb_advert_full_stats` | 广告完整统计 |
| `ods_wb_adverts_v2` | 广告活动 V2 |

### 财务

| 表名 | 说明 |
|------|------|
| `ods_wb_sales_reports` | 财务销售报告明细 |
| `ods_wb_sales_reports_daily` | `period=daily` 按日财务销售报告明细；与常规明细可能重叠，不可直接相加 |
| `ods_wb_sales_report_list` | 财务报表列表和周度报告范围 |
| `ods_wb_balance` | 店铺余额快照 |
| `ods_wb_cashback` | Cashback 数据 |
| `ods_wb_finance_seller_balance` | 财务域卖家余额每日快照 |
| `ods_wb_finance_region_sales` | 国家、地区、城市和商品维度区域销售报告 |

### 搜索流量

| 表名 | 说明 |
|------|------|
| `ods_wb_traffic_search_traffic` | 商品搜索流量滚动窗口 |
| `ods_wb_traffic_product_search_texts` | 商品自然搜索词报告 |

### DWD 业务明细

| 表名 | 说明 |
|------|------|
| `dwd_wb_adverts_report_detail` | 广告活动周度聚合明细 |
| `dwd_wb_order_detail` | Marketplace 订单业务明细 |
| `dwd_wb_order_statistics_detail` | Statistics API 订单统计明细 |
| `dwd_wb_return_detail` | 退货业务明细 |
| `dwd_wb_sales_funnel_detail` | 销售漏斗商品明细 |
| `dwd_wb_sales_report_detail` | 财务结算明细 |
| `dwd_wb_sales_report_summary` | 财务报告周汇总 |
| `dwd_wb_voc_feedback_detail` | 评价客户声音明细 |
| `dwd_wb_voc_question_detail` | 问答客户声音明细 |

> ODS 保留平台 API 原字段名及原始 `row_data`，例如 `barcode`、`sku`、`skus`。`barcode_ori`、`barcode_hand` 是 DWD 业务识别字段，不应写回或替代 ODS 原字段。

> 各 ODS 表继承 `create_time` / `update_time`，多数表带 `shop_id`（多租户）和 `row_data`（原始 JSON）。业务时间字段按数据含义单独命名，例如 `event_at`、`claim_updated_at`。字段级明细见 `docs/数据库表结构文档.md`。

### 同步类型 → 接口 / 写入表 对照

| data_type | Service 方法 | 主要写入表 |
|-----------|--------------|-----------|
| `sales` | `sync_sales` | `ods_wb_supplier_sales` |
| `orders` | `sync_orders` | `ods_wb_supplier_orders` |
| `marketplace_orders` | `sync_marketplace_orders` | `ods_wb_marketplace_orders`、`ods_wb_marketplace_order_status_histories` |
| `funnel` | `sync_funnel` | `ods_wb_sales_funnels` |
| `returns` | `sync_returns` | `ods_wb_goods_returns` |
| `adverts` | `sync_adverts` | `ods_wb_adverts`、`ods_wb_advert_product`、`ods_wb_advert_budget`、`ods_wb_advert_stats`、`ods_wb_search_cluster_stat` |
| `feedbacks` | `sync_feedbacks` | `ods_wb_feedbacks` |
| `questions` | `sync_questions` | `ods_wb_questions` |
| `finance` | `sync_finance` | `ods_wb_sales_reports` |
| （专用）finance-daily | `sync_finance_daily` | `ods_wb_sales_reports_daily` |
| （专用）balance | `sync_balance` | `ods_wb_balance`、`ods_wb_cashback` |
| （专用）adverts-hourly | `sync_advert_stats_hourly` | `ods_wb_advert_stats_hourly` |
| （专用）search-cluster-hourly | `sync_search_cluster_stat_hourly` | `ods_wb_search_cluster_stat_hourly` |
| （仅定时任务）new_orders | `sync_new_orders` | `ods_wb_new_orders` |
| （仅定时任务）return_claims | `sync_return_claims` | `ods_wb_return_claims` |
| （仅定时任务）chat_events | `sync_chat_events` | `ods_wb_voc_chat_events` |
| （仅定时任务）order_metadata | `sync_order_metadata` | `ods_wb_order_metadata` |
| （仅定时任务）fbs_supplies | `sync_fbs_supplies` | `ods_wb_order_fbs_supplies` |
| （仅定时任务）reshipment_orders | `sync_reshipment_orders` | `ods_wb_order_reshipment_orders` |
| （仅定时任务）feedback_pins | `sync_feedback_pins` | `ods_wb_voc_feedback_pins` |
| （定时/专用接口）adv-enhanced | `sync_all_adv_enhanced` | 8 张广告增强 ODS 表 |

> `sync_adverts` 是最“重”的任务：一次触发串联多个广告接口、写 5 张表，且按广告 ID 逐个查预算/统计，耗时随广告数放大。
>
> 新增任务的实际频率：`return_claims`、`chat_events` 在调度进程启动时立即执行，之后每小时执行；`order_metadata`、`fbs_supplies`、`reshipment_orders`、`feedback_pins` 在启动时立即执行，之后每天莫斯科时间 03:00 执行。完整任务清单见 `docs/SCHEDULED_JOBS.md`。

---

## 配置说明

### 1. 店铺配置

通过系统的店铺配置流程在 `shops` 表中创建 WB 店铺。不要用数据库客户端直接写入明文令牌；应让应用层通过 `EncryptedText` 完成加密后再保存。

- `platform` 必须为 `wildberries`
- `name`、`user_id` 为必填字段；`platform_shop_id` 用于区分同一用户下的多个店铺
- `api_key`：WB API Token。需按启用的数据域配置相应权限；本轮新增接口分别需要 `Buyers Returns`、`Buyers Chat`、`Marketplace`、`Feedbacks and Questions` 权限。令牌仍由现有加密字段保存，文档和代码中不得写入明文。

### 2. 同步窗口配置（`settings.sync`）

定时任务的取数窗口由 `SyncSettings` 管理，可用 `.env` 以 `sync_` 前缀覆盖，改后重启生效（详见 `docs/SCHEDULED_JOBS.md`）：

| 配置项 | 默认值 | 作用 |
|--------|--------|------|
| `sync_wb_orders_lookback_hours` | `24` | sales / orders 回看小时数 |
| `sync_wb_marketplace_lookback_days` | `2` | marketplace_orders 回看天数 |
| `sync_wb_return_claims_lookback_hours` | `1` | 买家退货申请按更新时间回看小时数 |
| `sync_wb_chat_events_lookback_days` | `1` | Buyer Chat 从 N 天前零点回看到运行时刻 |
| `sync_wb_order_metadata_lookback_days` | `1` | 订单元数据使用的 Marketplace 订单回看天数 |
| `sync_wb_reshipment_lookback_days` | `1` | 重新发货订单状态变化统计窗口 |
| `sync_wb_feedback_pins_lookback_days` | `1` | 评价置顶记录从 N 天前零点回看到运行时刻 |
| `sync_finance_backfill_days` | `7` | 财务任务回补天数（防 T+1 延迟结算） |
| `sync_wb_finance_daily_backfill_days` | `7` | `period=daily` 按日财务明细回补天数 |

---

## 使用示例

### Python（HTTP 调用）

```python
import httpx, asyncio

BASE_URL = "http://localhost:8000/api/v1"

async def sync_wb_data():
    async with httpx.AsyncClient() as client:
        # 查看 WB 支持的数据类型
        r = await client.get(f"{BASE_URL}/platforms/wildberries/data-types")
        print("Data types:", r.json())

        # 全量同步（WB 专用路由，JSON body）
        r = await client.post(
            f"{BASE_URL}/wildberries/sync",
            json={"shop_id": 1, "date_from": "2026-05-01", "date_to": "2026-05-23"},
        )
        print("Sync all:", r.json())

        # 仅同步销售（查询参数）
        r = await client.post(
            f"{BASE_URL}/wildberries/sync/sales",
            params={"shop_id": 1, "date_from": "2026-05-01", "date_to": "2026-05-23"},
        )
        print("Sales:", r.json())

asyncio.run(sync_wb_data())
```

### 直接使用服务层

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService

async def sync_wb_directly(db: AsyncSession, shop_id: int):
    shop = (await db.execute(select(Shop).where(Shop.id == shop_id))).scalar_one_or_none()
    if not shop:
        raise ValueError("Shop not found")
    service = WBSyncService(db, shop)
    result = await service.sync_all(date_from="2026-05-01", date_to="2026-05-23")
    print(result)
```

---

## 调试和测试

### 集成测试

WB 定时任务的集成测试位于 `tests/integration/test_jobs.py`，带 `wb` mark：


```bash
poetry run pytest tests/integration/test_jobs.py -v -m wb -s
```

### 查看 DEBUG 日志

`clients/wildberries.py`、`clients/base.py` 中有大量 `logger.debug()`，记录请求头、响应解析、限流等待等细节：

```bash
poetry run pytest tests/integration/test_jobs.py -v -k sales --log-cli-level=DEBUG -s
```

### 手动触发单个 Job

```python
import asyncio
from kunpeng.jobs.sync_wildberries import sync_all_shops_sales

asyncio.run(sync_all_shops_sales())
```

> 会真实调用 API 并写库，请确认环境配置正确。

---

## 相关文件

- `src/kunpeng/clients/wildberries.py`：WB API 客户端（多端点：statistics / analytics / advert / feedbacks）
- `src/kunpeng/services/wb_sync_service.py`：WB 同步服务
- `src/kunpeng/services/platform_sync.py`：平台同步注册表（`WildberriesPlatformService`）
- `src/kunpeng/api/v1/wildberries.py`：WB 专用路由
- `src/kunpeng/api/v1/platforms/sync.py`：通用平台路由
- `src/kunpeng/jobs/sync_wildberries.py`：WB 定时同步任务
- `src/kunpeng/crud/ods/wildberries/`：ODS 层 CRUD
- `src/kunpeng/models/ods/wildberries/`：ODS 层模型定义

**最后更新**：2026-08-26（按当前模型校准 4 张 WB 财务/流量 ODS 的英文规范表名）
