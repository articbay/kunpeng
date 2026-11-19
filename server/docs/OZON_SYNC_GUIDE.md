# Ozon 数据同步指南

本指南介绍如何使用 Ozon 数据同步功能。

## 目录

1. [概述](#概述)
2. [API 端点列表](#api-端点列表)
3. [数据库表设计](#数据库表设计)
4. [配置说明](#配置说明)
5. [使用示例](#使用示例)
6. [调试和测试](#调试和测试)

---

## 概述

Ozon 数据同步模块实现了完整的 ODS 层（操作数据存储），支持从 Ozon 平台同步以下数据：

- 订单数据 (FBS Postings)
- FBO 订单数据 (FBO Postings)
- 当前未履约 FBS 工作队列 (Unfulfilled Postings)
- 退货数据 (Returns)
- 评价数据 (Reviews)
- 商品数据 (Products)
- 广告活动与广告统计 (Performance API)
- 财务应计数据 (Finance Accruals)
- 销售实现报告 (Realization Reports)
- 应计类型字典 (Accrual Types)
- 经营分析 SKU 日数据 (Seller Analytics)

此外，当前代码还包含评价评论、商品问题、买家聊天以及订单/退货状态历史的模型和服务能力。这些补充能力没有独立定时任务，不能因为表或 Service 存在就理解为会自动同步。

---

## API 端点列表

### 通用平台同步 API

这些端点适用于所有平台（包括 Wildberries 和 Ozon）。

#### 1. 列出所有平台

```
GET /api/v1/platforms
```

响应示例：
```json
{
  "platforms": ["wildberries", "ozon"]
}
```

#### 2. 列出平台支持的数据类型

```
GET /api/v1/platforms/{platform}/data-types
```

参数：
- `platform`: 平台名称 (例如: "ozon")

响应示例：
```json
{
  "platform": "ozon",
  "data_types": [
    "accrual_types",
    "postings",
    "fbo_postings",
    "order_dwd",
    "product_name_translation",
    "postings_report",
    "returns",
    "return_status_changes",
    "reviews",
    "customer_voice_dwd",
    "advert_efficiency_dwd",
    "sales_funnel_dwd",
    "products",
    "adverts",
    "advert_products",
    "advert_products_hourly",
    "analytics_data",
    "finance_accruals",
    "realization_report"
  ]
}
```

#### 3. 同步所有数据

```
POST /api/v1/platforms/{platform}/sync
```

参数：
- `platform`: 平台名称 (例如: "ozon")
- `shop_id`: 店铺 ID (查询参数)
- `date_from`: 开始日期 (YYYY-MM-DD, 查询参数, 可选)
- `date_to`: 结束日期 (YYYY-MM-DD, 查询参数, 可选)

示例请求：
```bash
curl -X POST "http://localhost:8000/api/v1/platforms/ozon/sync?shop_id=1&date_from=2026-05-01&date_to=2026-05-23"
```

响应示例：
```json
{
  "status": "success",
  "platform": "ozon",
  "shop_id": 1,
  "date_from": "2026-05-01",
  "date_to": "2026-05-23",
  "results": {
    "accrual_types": {
      "status": "success",
      "message": "同步了 10 个应计类型",
      "count": 10
    },
    "postings": {
      "status": "success",
      "message": "同步了 50 个订单 (ODS)",
      "count": 50
    }
  }
}
```

#### 4. 同步特定类型的数据

```
POST /api/v1/platforms/{platform}/sync/{data_type}
```

参数：
- `platform`: 平台名称 (例如: "ozon")
- `data_type`: 数据类型 (例如: "postings")
- `shop_id`: 店铺 ID (查询参数)
- `date_from`: 开始日期 (YYYY-MM-DD, 查询参数, 可选)
- `date_to`: 结束日期 (YYYY-MM-DD, 查询参数, 可选)

示例请求：
```bash
curl -X POST "http://localhost:8000/api/v1/platforms/ozon/sync/postings?shop_id=1&date_from=2026-05-01&date_to=2026-05-23"
```

经营分析可手动指定日期窗口：

```bash
curl -X POST "http://localhost:8000/api/v1/platforms/ozon/sync/analytics_data?shop_id=1&date_from=2026-08-17&date_to=2026-08-23"
```

---

## 数据库表设计

### Ozon 专用表

当前模型共定义 **34 张 Ozon ODS 表**和 **6 张 Ozon DWD 表**。以下名称以当前 `__tablename__` 为准。

#### 字典表
- `ods_ozon_finance_accrual_types`: 应计类型字典

#### 订单相关表
- `ods_ozon_fbs_postings`: FBS 订单主表
- `ods_ozon_fbs_posting_products`: FBS 订单商品表
- `ods_ozon_fbs_posting_delivery`: FBS 配送信息表
- `ods_ozon_fbs_posting_cancellation`: FBS 取消信息表
- `ods_ozon_fbs_posting_optional`: FBS 可选信息表
- `ods_ozon_fbs_posting_external`: FBS 外部订单信息表
- `ods_ozon_fbo_postings`: FBO 订单主表
- `ods_ozon_fbo_posting_products`: FBO 订单商品表
- `ods_ozon_order_unfulfilled_postings`: 当前待卖家处理的未履约 FBS 工作队列
- `ods_ozon_posting_status_history`: FBS/FBO 订单状态变化历史

#### 退货相关表
- `ods_ozon_returns`: 退货主表
- `ods_ozon_return_products`: 退货商品表
- `ods_ozon_return_storage`: 退货仓储费用表
- `ods_ozon_return_status_history`: 退货状态变化历史

#### 评价表
- `ods_ozon_reviews`: 评价表
- `ods_ozon_review_comments`: 评价评论/回复表（当前无独立定时任务）

`ods_ozon_reviews.review_id` 使用 `VARCHAR(64)` 保存 v2 接口返回的 UUID 字符串。评价列表任务每小时执行；店铺未开通相应订阅时，403 会被记录为业务失败，不会伪装成同步成功。

#### 商品问题与聊天
- `ods_ozon_questions`: 商品问题表（当前无独立定时任务）
- `ods_ozon_question_answers`: 商品问题回答表（当前无独立定时任务）
- `ods_ozon_chats`: 买家聊天会话表（当前无独立定时任务）
- `ods_ozon_chat_messages`: 买家聊天消息表（当前无独立定时任务）

#### 财务应计相关表
- `ods_ozon_finance_accruals`: 财务应计主表
- `ods_ozon_finance_accrual_fees`: 从各类费用结构统一拆平的应计费用明细表

#### 销售实现报告相关表
- `ods_ozon_finance_realization_header`: 销售实现报告头表
- `ods_ozon_finance_realization_rows`: 销售实现报告行表

#### 商品与广告
- `ods_ozon_products`: Ozon 商品信息表
- `ods_ozon_adv_campaigns`: 广告活动表
- `ods_ozon_adv_stats_daily`: 广告活动日统计表
- `ods_ozon_adv_stats_product_daily`: 广告 SKU 日统计表
- `ods_ozon_adv_stats_product_hourly`: 广告 SKU 小时统计表

#### 经营分析

- `ods_ozon_analytics_data_daily`: 店铺 × SKU × 平台日的 18 项源指标明细。
- `ods_ozon_analytics_totals_window`: 每个店铺、每个请求日期窗口的 API 原始 totals。

接口每次最多请求 14 个指标，因此同步任务固定拆成 14 项核心指标和 4 项履约指标，使用相同日期窗口和 `sku + day` 维度分页拉取，再按 SKU 与日期合并。明细表同时保存两组原始行、请求指标顺序和 API 时间戳；ODS 不计算转化率或其他派生字段。

#### 发货报表

- `ods_ozon_posting_report_tasks`: 保存 FBS/FBO 发货报表的异步任务、状态、窗口与解析结果。
- `ods_ozon_posting_report_rows`: 保存报表 CSV 商品行及常用拆列字段，为统一订单 DWD 补充物流、金额和收件信息。

发货报表按“创建任务 → 轮询状态 → 下载 CSV → 解析落库”执行；每个 FBS/FBO 报表文件在下载并完整解析后提交对应类型明细，失败任务保留错误状态。

#### DWD
- `dwd_ozon_return_detail`: 关联退货、商品、仓储及原订单信息的退货商品业务明细表
- `dwd_ozon_order_detail`: 合并 FBS/FBO 订单、商品与发货报表的统一订单商品明细表
- `dwd_ozon_product_name_translation_cache`: 按店铺和 SKU 保存商品名称中文翻译，避免重复翻译
- `dwd_ozon_customer_voice_detail`: 以评价为粒度的客户声音业务明细表
- `dwd_ozon_advert_efficiency_detail`: 按广告活动、SKU 和日期生成的广告效率明细表
- `dwd_ozon_sales_funnel_detail`: 从经营分析 ODS 构建的 SKU 日销售漏斗明细表

订单、退货、评价、广告和经营分析同步完成后会在同一业务链路中刷新相应 DWD；DWD 构建不是新的外部 API。商品名称翻译结果通过缓存复用，并由 `ozon_translate_product_names_daily` 每天 04:45 兜底回填。

大多数业务表包含以下字段：
- `shop_id`: 店铺 ID（用于多租户）
- `row_data`: 原始 JSON 数据（完整 API 响应）
- `create_time`: 创建时间
- `update_time`: 更新时间

准确字段、唯一约束和索引见 `docs/数据库表结构文档.md`。ODS 保存平台原始 `row_data`；DWD 不保存 `row_data`，需要追溯时回查对应 ODS。

---

## 配置说明

### 1. 店铺配置

在数据库的 `shop` 表中，需要为 Ozon 店铺配置以下信息：

```sql
INSERT INTO shop (
  name,
  platform,
  api_key,
  config,
  is_active
) VALUES (
  'My Ozon Shop',
  'ozon',
  'YOUR_API_KEY',
  '{"client_id": "YOUR_CLIENT_ID", "api_key": "YOUR_API_KEY"}',
  true
);
```

字段说明：
- `name`: 店铺名称
- `platform`: 平台类型，必须为 "ozon"
- `api_key`: Ozon API Key
- `config`: JSON 配置，包含：
  - `client_id`: Ozon Client ID
  - `api_key`: Ozon API Key（与 api_key 字段重复是为了兼容性）

### 2. 获取 Ozon API 凭证

1. 登录 [Ozon 卖家后台](https://seller.ozon.ru/)
2. 进入 "设置" → "API"
3. 创建新的 API Key 或使用现有的
4. 记录下 `Client ID` 和 `API Key`

评价接口还要求店铺具备相应订阅权限；广告同步使用独立的 Ozon Performance Client-Id/Client-Secret，不应与 Seller API 凭证混淆。

---

## 使用示例

### Python 示例

```python
import httpx

# 基础 URL
BASE_URL = "http://localhost:8000/api/v1"

async def sync_ozon_data():
    """同步 Ozon 数据示例"""
    async with httpx.AsyncClient() as client:
        # 1. 查看支持的平台
        response = await client.get(f"{BASE_URL}/platforms")
        print("Platforms:", response.json())

        # 2. 查看 Ozon 支持的数据类型
        response = await client.get(f"{BASE_URL}/platforms/ozon/data-types")
        print("Data types:", response.json())

        # 3. 同步所有数据
        response = await client.post(
            f"{BASE_URL}/platforms/ozon/sync",
            params={
                "shop_id": 1,
                "date_from": "2026-05-01",
                "date_to": "2026-05-23"
            }
        )
        print("Sync result:", response.json())

        # 4. 只同步订单数据
        response = await client.post(
            f"{BASE_URL}/platforms/ozon/sync/postings",
            params={
                "shop_id": 1,
                "date_from": "2026-05-01",
                "date_to": "2026-05-23"
            }
        )
        print("Postings sync result:", response.json())

# 运行
import asyncio
asyncio.run(sync_ozon_data())
```

### 直接使用服务层

```python
from sqlalchemy.ext.asyncio import AsyncSession
from kunpeng.services.ozon_sync_service import OzonSyncService

async def sync_ozon_data_directly(db: AsyncSession, shop_id: int):
    """直接使用服务层同步数据"""
    # 获取店铺
    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = result.scalar_one_or_none()

    if not shop:
        raise ValueError("Shop not found")

    # 创建服务
    service = OzonSyncService(db, shop)

    # 同步所有数据
    result = await service.sync_all(
        date_from="2026-05-01",
        date_to="2026-05-23"
    )

    print(result)
```

---

## 调试和测试

### 1. 使用测试脚本

在 `docs/` 目录下有测试脚本 `test_ozon_sync_service.py`：

```bash
cd docs
python test_ozon_sync_service.py
```

注意：使用前需要在脚本中配置真实的 Ozon 凭证。

### 2. 查看日志

日志配置在 `src/kunpeng/core/logging.py` 中，日志级别跟随项目现有的 `DEBUG` 配置：

```env
DEBUG=true
```

### 3. 常见问题

#### Q: 如何只同步特定日期的数据？

A: 使用 `date_from` 和 `date_to` 参数：

```bash
curl -X POST "http://localhost:8000/api/v1/platforms/ozon/sync?shop_id=1&date_from=2026-05-01&date_to=2026-05-10"
```

#### Q: 财务应计数据如何同步？

A: 财务应计数据是按天同步的，建议每天凌晨同步前一天的数据。

#### Q: 如何查看数据库中的原始数据？

A: ODS 表使用 `row_data` 保存原始 API 响应；DWD 表不保留 `row_data`，需要追溯时按业务键回查对应 ODS。

---

## 相关文件

- `src/kunpeng/clients/ozon.py`: Ozon API 客户端
- `src/kunpeng/services/ozon_sync_service.py`: Ozon 同步服务
- `src/kunpeng/services/platform_sync.py`: 平台同步注册表
- `src/kunpeng/crud/ods/ozon/`: ODS 层 CRUD 操作
- `src/kunpeng/models/ods/ozon/`: ODS 层模型定义
- 详细的 API 字段映射文档已归档至知识库（坤鹏_API字段映射归档）

**最后更新**：2026-08-26（补充发货报表 ODS、五张新增 DWD、商品名称翻译缓存及 13 个 Ozon 调度任务现状）
