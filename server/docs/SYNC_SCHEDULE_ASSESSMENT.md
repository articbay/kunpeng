# 数据同步调度任务 — 现状盘点与评估

> 目的：在调整"自动调度触发"之前，把 WB / Ozon 所有同步任务的**触发频率**、**数据窗口**、**实时性（T-1 / 实时 / 离线）**、以及**每个任务实际调用了哪些接口、写入哪些数据**完整盘清楚，作为后续决策底稿。
>
> 盘点范围（源码）：
> - `src/kunpeng/core/scheduler.py`（调度器封装）
> - `src/kunpeng/jobs/sync_wildberries.py`、`sync_ozon.py`（任务定义与注册）
> - `src/kunpeng/services/wb_sync_service.py`、`ozon_sync_service.py`（各同步方法的取数窗口与接口调用）
> - `src/kunpeng/clients/wildberries.py`、`ozon.py`（底层 API 端点）
> - `src/kunpeng/main.py`、`src/kunpeng/scheduler_main.py`（启动入口）、`src/kunpeng/config/settings.py`（环境开关）
>
> 变更说明（本轮已执行）：
> - **竞品抓取调度任务已删除**（逻辑未实现，`jobs/competitor_scraper.py` 移除；service/API 保留）。
> - **WB 小时级任务已并入** `sync_wildberries.py`，统一由 `register_wildberries_jobs()` 注册（原 `sync_wildberries_hourly.py` 已删除）。
> - **已落地窗口收敛 + 财务回补**：每小时任务窗口收敛、财务任务改回补窗口，全部由 `settings.sync`（`SyncSettings`）配置化（见第 9 节）。
> - **已接入 6 类 WB 数据**：买家退货申请、Buyer Chat、FBS订单元数据、FBS供货单、重新发货订单、评价置顶记录。

---

## 1. 调度框架现状

- **调度引擎**：APScheduler `AsyncIOScheduler`，全局单例（`kunpeng.core.scheduler.scheduler`）。
- **注册入口**：独立调度进程使用 `python -m kunpeng.scheduler_main`，依次调用 `register_wildberries_jobs()`、`register_ozon_jobs()`；FastAPI 只有在 `RUN_SCHEDULER=true` 时才会启动并注册调度器。
- **注册开关（关键）**：每个 `register_*` 均有一行判断：
  ```python
  if settings.environment != "production" and not settings.jobs_enabled:
      return
  ```
  即 **`environment=production` 或 `jobs_enabled=True` 时才注册**。默认 `environment=development`、`jobs_enabled=False`，开发环境不会自动跑。
- **单任务防护**：`misfire_grace_time=30s`、`coalesce=True`（错过多次只补一次）、`max_instances=1`（同任务不并发）。
- **部署形态**：生产建议 API worker 设置 `RUN_SCHEDULER=false`，调度器用单独进程运行，避免多 worker 重复注册；单进程开发环境也可以显式开启 `RUN_SCHEDULER=true`。

---

## 2. 全量任务盘点表

图例：数据窗口 = 每次执行实际拉取的时间范围；实时性 = 数据新鲜度定位。

### 2.1 Wildberries（`register_wildberries_jobs`，共 34 个）

| 任务函数 | 触发频率 | 触发表达式 | 每次拉取数据窗口 | 实时性定位 |
|---|---|---|---|---|
| `sync_all_shops_sales` | 每小时 | `interval 60min` | 近 24 小时（`now-24h` 起） | 准实时（小时级） |
| `sync_all_shops_orders` | 每小时 | `interval 60min` | 近 24 小时 | 准实时（小时级） |
| `sync_all_shops_marketplace_orders` | 每小时 | `interval 60min` | 近 `sync.wb_marketplace_lookback_days` 天（默认 2） | 准实时（小时级） |
| `sync_all_shops_new_orders` | 每小时 | `interval 60min` | 当前待处理新订单快照（接口无日期参数） | 准实时（小时级） |
| `sync_all_shops_return_claims` | 每小时，启动立即执行 | `interval 60min` | 接口近14天全量分页后，本地筛选最近1小时新增/更新 | 准实时（小时级） |
| `sync_all_shops_chat_events` | 每小时，启动立即执行 | `interval 60min` | 昨天00:00~运行时刻 | 准实时（小时级） |
| `sync_all_shops_feedbacks` | 每小时 | `interval 60min` | 昨天~今天 | 准实时（小时级） |
| `sync_all_shops_questions` | 每小时 | `interval 60min` | Service 默认回看窗口 | 准实时（小时级） |
| `sync_all_shops_returns` | 每小时 | `interval 60min` | Service 默认回看窗口 | 准实时（小时级） |
| `sync_all_shops_advert_stats_hourly` | 每小时 | `5 * * * *`（每小时第 5 分） | 当天整天累计，增量算当前小时 | 小时级（近实时） |
| `sync_all_shops_search_cluster_stat_hourly` | 每小时 | `5 * * * *`（每小时第 5 分） | 当天整天累计，增量算当前小时 | 小时级（近实时） |
| `sync_all_shops_adverts` | 每天 | `0 2 * * *`（02:00） | T-1（昨天单日） | T-1（离线日更） |
| `sync_all_shops_feedback_pins` | 每天，启动时立即执行 | `0 3 * * *`（03:00） | 昨天00:00~运行时刻 | T-1（离线日更） |
| `sync_all_shops_order_metadata` | 每天，启动时立即执行 | `0 3 * * *`（03:00） | 昨天00:00~运行时刻内的现有Marketplace订单 | T-1（离线日更） |
| `sync_all_shops_fbs_supplies` | 每天，启动时立即执行 | `0 3 * * *`（03:00） | 全量分页；业务统计窗口为昨天00:00~运行时刻 | 全量状态刷新 |
| `sync_all_shops_reshipment_orders` | 每天，启动时立即执行 | `0 3 * * *`（03:00） | 当前完整快照；状态变化统计窗口为昨天00:00~运行时刻 | 状态快照 |
| `sync_all_shops_funnel` | 每天 | `0 4 * * *`（04:00） | T-1（昨天单日） | T-1（离线日更） |
| `sync_all_shops_balance` | 每天 | `0 8 * * *`（08:00） | 实时快照（无日期区间） | 实时快照 |
| `sync_all_shops_finance` | 每天 | `0 9 * * *`（09:00） | 回补 `[今天-N, 昨天]`（N=`sync.finance_backfill_days`，默认 7） | T-1 + 回补 |
| `sync_all_shops_finance_daily` | 每天 | `0 10 * * *`（10:00） | 最近7个完整平台日 | 按日财务回补 |
| `reconcile_wb_voc_feedback_dwd` | 每天+启动补跑 | `30 3 * * *` | 从现有 ODS 全量幂等校准 | DWD 兜底 |
| `reconcile_wb_voc_question_dwd` | 每天+启动补跑 | `35 3 * * *` | 从现有 ODS 全量幂等校准 | DWD 兜底 |
| `reconcile_wb_return_dwd` | 每天+启动补跑 | `40 3 * * *` | 从现有 ODS 全量幂等校准 | DWD 兜底 |
| `reconcile_wb_order_dwd` | 每天+启动补跑 | `45 3 * * *` | 从现有 ODS 全量幂等校准 | DWD 兜底 |
| `reconcile_wb_order_statistics_dwd` | 每天+启动补跑 | `50 3 * * *` | 从现有 ODS 全量幂等校准 | DWD 兜底 |
| `translate_wb_dwd_to_chinese` | 每15分钟 | `interval 15min` | 补齐 DWD 待翻译原文 | 中文字段回填 |
| `sync_all_shops_seller_balance` | 每天 | `0 3 * * *` | 当前余额快照 | 每日快照 |
| `sync_all_shops_sales_report_list` | 每周一 | `5 3 * * mon` | 上一自然周 | 周汇总 |
| `sync_all_shops_region_sales` | 每天 | `5 3 * * *` | 最近2个完整平台日 | T-1 + 回补 |
| `sync_all_shops_search_traffic` | 每天 | `15 3 * * *` | 最近7日并对比前7日 | 滚动窗口 |
| `sync_all_shops_product_search_texts` | 每天 | `35 3 * * *` | 最近2个完整平台日 | T-1 + 回补 |
| `sync_all_shops_adv_enhanced` | 每天 | `0 3 * * *` | 当前广告增强数据 | 日更 |
| `sync_all_shops_advert_fullstats` | 每小时 | `10 * * * *` | 当前广告完整统计窗口 | 小时级 |
| `refresh_all_shops_adverts_report` | 每天 | `30 2 * * *` | 从广告 ODS 刷新周度 DWD | DWD 日校准 |

> 小时级任务逻辑：调 API 拿"今天整天累计" − "今天已入库的历史小时累计" = 当前小时增量；幂等写入。跨天边界（00:00–00:10）结算的是**昨天 23:00**那一格。

### 2.2 Ozon（`register_ozon_jobs`，共 13 个）

| 任务函数 | 触发频率 | 触发表达式 | 每次拉取数据窗口 | 实时性定位 |
|---|---|---|---|---|
| `sync_all_shops_postings` | 每小时 | `interval 60min` | 近 `sync.ozon_postings_lookback_days` 天（默认 3） | 准实时（小时级） |
| `sync_all_shops_fbo_postings` | 每小时 | `interval 60min` | 近 `sync.ozon_fbo_lookback_days` 天（默认 3） | 准实时（小时级） |
| `sync_all_shops_unfulfilled_postings` | 启动立即执行，之后每小时 | `interval 60min` | 平台时区昨天 00:00 到本次实际运行时刻（`cutoff` 履约截止时间，默认回看 1 天） | 准实时状态快照（小时级） |
| `sync_all_shops_returns` | 每小时 | `interval 60min` | 近 `sync.ozon_returns_lookback_days` 天（默认 2） | 准实时（小时级） |
| `sync_all_shops_reviews` | 每小时 | `interval 60min` | Service 评价分页窗口 | 准实时（小时级） |
| `sync_all_shops_advert_products_hourly` | 每小时 | `10 * * * *`（每小时第10分） | 当天广告SKU累计数据，折算小时增量 | 小时级（近实时） |
| `sync_all_shops_finance` | 每天 | `20 3 * * *`（03:20） | 回补 `[今天-N, 昨天]`（N=`sync.finance_backfill_days`，默认 7，按天循环） | T-1 + 回补 |
| `sync_all_shops_accrual_types` | 每天 | `10 4 * * *`（04:10） | 全量维度字典（无区间） | 离线维度表 |
| `sync_all_shops_products` | 每天 | `30 4 * * *`（04:30） | 全量商品（分页遍历） | 离线维度表 |
| `translate_ozon_product_names` | 每天 | `45 4 * * *`（04:45） | 扫描待翻译商品并复用 `(shop_id, sku)` 缓存 | 中文字段回填 |
| `sync_all_shops_adverts` | 每天 | `0 5 * * *`（05:00） | 近 7 天 | T-1/近 7 日 |
| `sync_all_shops_advert_products` | 每天 | `30 5 * * *`（05:30） | 近 7 天（异步报表，耗时） | T-1/近 7 日 |
| `sync_all_shops_analytics_data` | 每天 | `0 7 * * *`（07:00） | 最近7个完整平台日，14+4指标分组分页 | T-1 + 回补 |

---

## 3. 每个任务同步了哪些接口 / 哪些数据

> 重点：部分任务是**一个调度触发、内部串联多个接口 / 多张表**。下表按"任务 → 调用接口 → 写入数据表"展开。

### 3.1 Wildberries

| 任务 | 调用接口（client 方法 / API 端点） | 写入数据（ODS 表） |
|---|---|---|
| `sync_sales` | `statistics.get_supplier_sales` → `GET /api/v1/supplier/sales` | `ods_wb_supplier_sales` |
| `sync_orders` | `statistics.get_supplier_orders` → `GET /api/v1/supplier/orders` | `ods_wb_supplier_orders` |
| `sync_adverts` **(多接口)** | `advert.get_adverts_list` → `/api/advert/v2/adverts`；`advert.get_advert_budget` → `/adv/v1/budget`；`advert.get_advert_stats` → `/adv/v3/fullstats`；`advert.get_normquery_stats` → `/adv/v1/normquery/stats` | `ods_wb_adverts`、`ods_wb_advert_product`、`ods_wb_advert_budget`、`ods_wb_advert_stats`、`ods_wb_search_cluster_stat` |
| `sync_feedbacks` | `feedbacks.get_feedbacks` → `/api/v1/feedbacks` | `ods_wb_feedbacks` |
| `sync_feedback_pins` | `feedbacks.get_feedback_pins` → `/api/feedbacks/v1/pins` | `ods_wb_voc_feedback_pins` |
| `sync_questions` | `feedbacks.get_questions` → `/api/v1/questions`（已答/未答各拉一遍） | `ods_wb_questions` |
| `sync_chat_events` | `buyer_chat.get_events` → `GET /api/v1/seller/events` | `ods_wb_voc_chat_events` |
| `sync_funnel` | `analytics.get_sales_funnel` → `/api/analytics/v3/sales-funnel/products` | `ods_wb_sales_funnels` |
| `sync_returns` | `analytics.get_goods_return` → `/api/v1/analytics/goods-return` | `ods_wb_goods_returns` |
| `sync_return_claims` | `returns.get_claims` → `GET /api/v1/claims`（归档/未归档分别分页） | `ods_wb_return_claims` |
| `sync_finance` | `finance.get_sales_reports_detailed` → `/api/finance/v1/sales-reports/detailed` | `ods_wb_sales_reports` |
| `sync_marketplace_orders` **(多接口)** | `marketplace.get_orders` → `/api/v3/orders`；`marketplace.get_orders_status` → `/api/v3/orders/status`；`marketplace.get_orders_status_history` → `/api/v3/orders/status/history` | `ods_wb_marketplace_orders`、`ods_wb_marketplace_order_status_histories` |
| `sync_new_orders` | `marketplace.get_new_orders` → `GET /api/v3/orders/new` | `ods_wb_new_orders` |
| `sync_order_metadata` | `marketplace.get_orders_metadata` → `POST /api/marketplace/v3/orders/meta` | `ods_wb_order_metadata` |
| `sync_fbs_supplies` | `marketplace.get_supplies` → `GET /api/v3/supplies` | `ods_wb_order_fbs_supplies` |
| `sync_reshipment_orders` | `marketplace.get_reshipment_orders` → `GET /api/v3/supplies/orders/reshipment` | `ods_wb_order_reshipment_orders` |
| `sync_balance` **(多接口)** | `advert.get_balance` → `/adv/v1/balance`（余额 + cashback） | `ods_wb_balance`、`ods_wb_cashback` |
| `sync_advert_stats_hourly` | `advert.get_adverts_list` + `advert.get_advert_stats`（当天累计，算小时增量） | `ods_wb_advert_stats_hourly` |
| `sync_search_cluster_stat_hourly` | `advert.get_adverts_list` + `advert.get_normquery_stats`（当天累计，算小时增量） | `ods_wb_search_cluster_stat_hourly` |

> 注：`sync_adverts` 是 WB 里最"重"的任务——一次触发内串联 4 个广告相关接口、写 5 张表，且要按广告 ID 逐个查预算/统计，耗时随广告数放大。

### 3.2 Ozon

| 任务 | 调用接口（client 方法 / API 端点） | 写入数据（ODS 表） |
|---|---|---|
| `sync_postings` **(多接口/多表)** | `posting.get_fbs_postings` → `POST /v4/posting/fbs/list` | `ods_ozon_fbs_postings` 及其商品、配送、取消、可选和外部信息子表 |
| `sync_fbo_postings` | `posting.get_fbo_postings` → `POST /v2/posting/fbo/list` | `ods_ozon_fbo_postings`、`ods_ozon_fbo_posting_products` |
| `sync_unfulfilled_postings` | `posting.get_unfulfilled_postings` → `POST /v4/posting/fbs/unfulfilled/list`（根节点 `postings/count/cursor/has_next`，游标分页） | `ods_ozon_order_unfulfilled_postings`（含当前有效/已离开列表状态） |
| `sync_returns` | `return_.get_returns_list` → `POST /v1/returns/list` | `ods_ozon_returns`、`ods_ozon_return_products`、`ods_ozon_return_storage` |
| `sync_reviews` | `review.get_review_list` → `POST /v2/review/list` | `ods_ozon_reviews` |
| `sync_finance_accruals` **(多表)** | `finance.get_accrual_by_day` → `POST /v1/finance/accrual/by-day`（按天循环） | `ods_ozon_finance_accruals`、`ods_ozon_finance_accrual_fees` |
| `sync_accrual_types` | `finance.get_accrual_types` → `POST /v1/finance/accrual/types` | `ods_ozon_finance_accrual_types` |
| `sync_products` **(多接口)** | `product.get_product_list` → `/v3/product/list`；`product.get_product_info_list` → `/v3/product/info/list` | `ods_ozon_products` |
| `sync_adverts` **(Performance API，多接口)** | `performance.get_campaigns` → `/api/client/campaign`；`performance.get_statistics_daily` → `/api/client/statistics/daily/json` | `ods_ozon_adv_campaigns`、`ods_ozon_adv_stats_daily` |
| `sync_advert_products` **(异步报表)** | `performance.get_campaigns`；`performance.fetch_statistics_report`（提交→轮询→下载） | `ods_ozon_adv_stats_product_daily` |
| `sync_advert_products_hourly` **(异步报表)** | `performance.get_campaigns`；`performance.fetch_statistics_report`（当天累计，算小时增量） | `ods_ozon_adv_stats_product_hourly` |
| `sync_analytics_data` | `POST /v1/analytics/data`（14+4 指标分组、`sku + day` 分页） | `ods_ozon_analytics_data_daily`、`ods_ozon_analytics_totals_window`；成功后构建 `dwd_ozon_sales_funnel_detail` |
| `translate_ozon_product_names` | 不调用 Ozon；读取商品原名并调用翻译服务 | `dwd_ozon_product_name_translation_cache`，并回填相关 DWD 中文字段 |

> 注 1：`sync_postings` / `sync_finance_accruals` 是 Ozon 里最"重"的任务，一次触发写 3~6 张关联表。
> 注 2：`OzonSyncService` 还有一个 `sync_realization_report`（`POST /v2/finance/realization` → `ods_ozon_finance_realization_header/row`），**未接入定时任务**，目前只能手动/接口触发。若需要"结算单"数据日更，需要新增一个调度任务。

---

## 4. 每日执行时间轴（生产环境）

```
调度进程启动时立即执行
  WB: return_claims / chat_events / feedback_pins / order_metadata /
      fbs_supplies / reshipment_orders
  Ozon: unfulfilled_postings

每60分钟       WB: sales / orders / feedbacks / questions / returns /
                   return_claims / chat_events / marketplace_orders / new_orders
每60分钟       Ozon: postings / fbo_postings / unfulfilled_postings /
                     returns / reviews
每小时(:05)   WB: advert_stats_hourly / search_cluster_stat_hourly
每小时(:10)   Ozon: advert_products_hourly
─────────────────────────────────────────────
02:00  WB adverts
03:00  WB feedback_pins / seller_balance / adv_enhanced
03:05~03:50  WB 周报/区域/搜索/订单扩展及 DWD 错峰校准
03:20  Ozon finance(accruals)
04:00  WB funnel
04:10  Ozon accrual_types
04:30  Ozon products
04:45  Ozon product_name_translation
05:00  Ozon adverts
05:30  Ozon advert_products
07:00  Ozon analytics_data
08:00  WB balance
09:00  WB finance(T-1)
10:00  WB finance_daily_by_day
```

---

## 5. 数据实时性归类

- **实时/状态快照**：WB `balance`（余额）和 `reshipment_orders`（当前重新发货清单）；接口本身不接受日期区间。
- **近实时（小时级）**：WB sales/orders/marketplace/new_orders、feedbacks/questions、returns/return_claims、chat_events、广告和搜索词小时表，以及 Ozon postings/fbo/unfulfilled/returns/reviews、广告SKU小时表。重叠窗口靠唯一键幂等 upsert。
- **T-1 / 离线日更**：WB adverts/funnel/feedback_pins/order_metadata/fbs_supplies/reshipment_orders/finance，以及 Ozon finance/adverts/analytics_data。凌晨处理昨天数据、回补完整平台日或刷新完整状态。
- **离线维度表**：Ozon accrual_types / products（全量刷新，不分区间）；商品翻译缓存每天在商品同步后回填。

---

## 6. 基于接口特性的同步时间 / 周期评估

> 结合各接口的数据产出节奏（实时事件流 vs. 平台 T+1 结算）给出建议。

| 数据域 | 接口数据产出节奏 | 现状触发 | 评估与建议 |
|---|---|---|---|
| 订单/发货（WB orders/new_orders、Ozon postings/fbo/unfulfilled） | 近实时事件流 / 未履约当前状态 | 每小时 | Ozon unfulfilled 使用昨天零点至运行时刻的截止时间窗口，并在完整分页成功后幂等写入和对账 |
| WB订单元数据 | 依赖现有Marketplace订单ID | 启动立即执行 + 每天03:00 | 日更合理；每批最多100个订单ID，不重复维护订单主表 |
| WB供货单/重新发货 | 供货单全量分页、重新发货当前快照 | 启动立即执行 + 每天03:00 | 适合状态刷新；重新发货记录采用激活/解决标记，不物理删除历史 |
| 销售（WB sales） | 近实时 | 每小时，窗口 24h | 合理，保持 |
| 退货（WB/Ozon returns） | 用户和物流状态可能随时变化 | 每小时 | 适合增量识别；重复数据由唯一键覆盖 |
| WB买家退货申请 | 平台仅提供近14天分页数据 | 启动立即执行 + 每小时，本地筛选近1小时 | 频率合理；需关注全量分页带来的API耗时 |
| 广告日统计（WB adverts、Ozon adverts） | 平台按天结算，当天数据会回填修正 | 每天凌晨 T-1 | 合理。若要盘中监控投放，才需要小时级（WB 已有小时表覆盖） |
| 广告小时（WB advert_stats_hourly/search_cluster、Ozon advert_products_hourly） | 平台当天累计值持续更新 | 每小时 | 合理，增量算法已处理累计口径 |
| 财务/结算（WB finance、Ozon finance accruals） | 平台 T+1 甚至更晚结算 | 每天，回补近7天 | 当前回补窗口合理，可覆盖平台延迟结算 |
| 客户声音（WB feedbacks/questions/chat_events、Ozon reviews） | 用户随时产生 | 每小时 | 适合客服SLA和客户声音分析；Buyer Chat只保存消息和附件元数据，不自动回复 |
| WB评价置顶记录 | 状态按操作发生时间变化 | 启动立即执行 + 每天03:00 | 日更满足运营分析；与评价正文通过feedback_id联查 |
| 余额（WB balance） | 实时快照 | 每天 1 次 | 若要监控广告余额告警，建议提到每小时；纯记录每天即可 |
| 商品/维度字典（Ozon products / accrual_types） | 变更极低频 | 每天 | 合理，甚至可降到每天 1 次或按需触发 |

---

## 7. 需要重点评估/优化的点（供决策）

1. ✅ **已落地：每小时任务窗口收敛（成本/性能）**
   - Ozon `postings/fbo` 由兜底 30 天收敛到默认 3 天、`returns` 2 天；WB `marketplace` 兜底 7 天收敛到 2 天。
   - 靠幂等 upsert 去重，显著降低 API 调用量、翻页与 DB 压力。窗口由 `settings.sync` 配置。

2. ✅ **已落地（部分）：关键 job 窗口显式传参 + 配置化**
   - WB sales/orders/marketplace/return_claims/chat_events/order_metadata/reshipment/feedback_pins/finance，以及 Ozon postings/fbo/returns/finance，均在 job 层确定窗口并由 `settings.sync` 管理。
   - WB supplies 接口无日期参数，任务全量分页后按业务时间统计昨天窗口；WB questions/returns 和 Ozon reviews 仍使用 service 默认窗口。

3. **重任务耗时随规模放大**
   - WB `sync_adverts`（4 接口/5 表/按广告 ID 循环）、WB `sync_return_claims`（近14天归档/未归档分页）、Ozon `sync_postings`（多表）、`sync_finance_accruals`（按天循环）耗时会随数据量放大。
   - `max_instances=1` 下，若单轮超过触发间隔会 misfire。建议监控单轮耗时。

4. ✅ **已支持调度与 Web 解耦**
   - API worker 可设置 `RUN_SCHEDULER=false`，独立进程通过 `python -m kunpeng.scheduler_main` 注册全部任务。
   - 生产仍需保证独立调度进程只有一个实例，避免任务重复触发。

5. **整点任务扎堆**
   - 大量 `interval 60min` 都在整点触发，且多店铺串行循环。峰值集中。
   - 待评估：错峰（不同任务给不同分钟偏移），或店铺级并发控制。

6. **未接入调度的数据（仍待办）**
   - Ozon `sync_realization_report`（结算单）已有 service 实现但**没有定时任务**。若业务需要，需补一个调度任务（建议 T+1 每天，甚至每月账单周期触发）。

> ✅ 另：**财务回补窗口已落地** —— WB/Ozon 财务任务改为回补 `[今天-N, 昨天]`（默认 7 天，`settings.sync.finance_backfill_days`），覆盖平台 T+1 延迟结算，幂等写入不会重复计数。

---

## 8. 调度决策状态

| 决策项 | 选项 A | 选项 B | 选项 C |
|---|---|---|---|
| 小时级数据窗口 ✅已落地 | 收敛到近 24~72h（**已采用**，省成本） | 保持大窗口靠幂等 | 双档：小时增量 + 每日回补 |
| 调度部署形态 ✅已支持 | 独立调度进程 + Web 关闭注册（**生产推荐**） | 保持单进程，Web 单副本（开发可用） | 引入分布式锁允许多副本 |
| 触发错峰 | 按任务加分钟偏移（推荐） | 维持整点（现状） | 引入优先级队列 |
| 窗口参数化 ✅已落地 | job 层显式传参 + 配置化（**已采用**） | 维持 service 默认兜底 | — |
| 财务回补 ✅已落地 | 每天补拉近 7 天防延迟结算（**已采用**） | 只拉 T-1 | — |
| Ozon 结算单 | 新增 realization 每日调度（推荐若需要） | 维持手动触发 | — |

> 备注：已落地竞品任务清理、WB 小时任务合并、窗口收敛、财务回补、独立调度进程入口，以及 6 类新增 WB 数据同步。剩余待评估项主要是任务错峰、单轮耗时监控和 Ozon 结算单调度。

---

## 9. 已落地的同步窗口配置（`settings.sync`）

通过 `.env` 以 `sync_` 前缀覆盖，改后重启应用生效：

| 配置项 | 默认值 | 作用 |
|---|---|---|
| `sync_wb_orders_lookback_hours` | `24` | WB sales / orders 回看小时数 |
| `sync_wb_marketplace_lookback_days` | `2` | WB marketplace_orders 回看天数 |
| `sync_wb_return_claims_lookback_hours` | `1` | WB 买家退货申请按更新时间回看小时数 |
| `sync_wb_chat_events_lookback_days` | `1` | WB Buyer Chat 从 N 天前零点回看到运行时刻 |
| `sync_wb_order_metadata_lookback_days` | `1` | WB 订单元数据使用的订单回看天数 |
| `sync_wb_reshipment_lookback_days` | `1` | WB 重新发货状态变化统计窗口 |
| `sync_wb_feedback_pins_lookback_days` | `1` | WB 评价置顶记录回看天数 |
| `sync_ozon_postings_lookback_days` | `3` | Ozon postings 回看天数 |
| `sync_ozon_fbo_lookback_days` | `3` | Ozon fbo_postings 回看天数 |
| `sync_ozon_unfulfilled_lookback_days` | `1` | Ozon 待处理 FBS 订单的 cutoff 窗口起点：运行日往前 N 天的 00:00 |
| `sync_ozon_returns_lookback_days` | `2` | Ozon returns 回看天数 |
| `sync_finance_backfill_days` | `7` | WB / Ozon 财务任务回补天数 |

定义见 `src/kunpeng/config/settings.py` 的 `SyncSettings`。

**最后更新**：2026-08-26（按当前 WB 34 个、Ozon 13 个注册任务校准，并补充 Ozon 经营分析与商品翻译链路）
