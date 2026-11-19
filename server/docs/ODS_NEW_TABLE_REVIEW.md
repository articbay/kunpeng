# 新增 ODS 表评审清单

本文用于约束新平台接口落表。所有新表在开发前必须完成以下评审，并在接口、
模型或业务口径变化后重新复核：

1. 业务价值及与现有数据的重复关系；
2. 全量或增量同步方式；
3. 只新增、覆盖更新或新增与更新并存；
4. 能稳定唯一定位数据的业务主键；
5. 表名使用全小写 `ods_<平台>_<板块>_<具体内容>`；
6. 对比实际 `row_data`，记录已拆列和未拆列字段；
7. 明确字段含义、单位、时间口径和适用范围。

板块统一使用：

- `voc`：用户评价、问题、聊天等客户声音；
- `return`：退货申请及退货流程；
- `order`：订单、供货单及履约状态。

## 本轮近期新增表评审

| 标准表名 | 业务价值及非重复性 | 同步方式 | 更新策略 | 业务主键 |
|---|---|---|---|---|
| `ods_wb_return_claims` | 买家退货申请工作流；不同于退货统计结果 | 最近14天范围内重叠增量，本地筛更新时间 | 新增与覆盖更新并存，不删除 | `(shop_id, claim_id)` |
| `ods_wb_voc_chat_events` | 私聊消息和投诉；不同于公开评价/问题 | 毫秒`next`游标增量 | 新增与覆盖更新并存 | `(shop_id, event_id)` |
| `ods_wb_voc_feedback_pins` | 评价置顶及自动取消记录；不保存评价正文 | `pinned/unpinned`分别完整游标分页，本地按`changeStateAt`筛窗口 | 新增与覆盖更新并存 | `(shop_id, pin_id)` |
| `ods_wb_order_metadata` | 现有订单的元数据扩展，不作为第二张订单主表 | 按现有订单ID分批增量查询 | 新增与覆盖更新并存 | `(shop_id, order_id)` |
| `ods_wb_order_fbs_supplies` | 多个FBS订单组成的交付批次及生命周期 | 接口无日期过滤，完整游标分页 | 新增与覆盖更新并存 | `(shop_id, supply_id)` |
| `ods_wb_order_reshipment_orders` | 当前需重新发货的异常工作队列 | 全量当前快照 | 新增、重新激活和已解决状态更新，不删除 | `(shop_id, order_id, supply_id)` |
| `ods_wb_sales_reports_daily` | 将财务明细固定到 `period=daily` 的日维度窗口；字段与常规财务明细高度重叠，但可独立验证每日结算和回填 | 重叠窗口增量回补，默认最近7天至昨天 | 新增与覆盖更新并存，不删除 | `(shop_id, date_from, date_to, rrd_id)` |
| `ods_ozon_order_unfulfilled_postings` | 当前待打包/发货工作队列；不同于完整FBS订单历史 | 截止时间重叠窗口，cursor完整分页 | 原子upsert及active/resolved快照对账 | `(shop_id, posting_number)` |
| `ods_ozon_posting_report_tasks` | 保存发货报表异步任务生命周期；不同于订单事实明细 | 按指定窗口创建任务并轮询 | 按任务编码覆盖状态，不删除失败记录 | `(shop_id, report_code)` |
| `ods_ozon_posting_report_rows` | 发货报表商品行，补充订单 API 不稳定或缺失的物流、金额、收件字段 | 报表完成后下载 CSV 全量解析 | 按业务键幂等新增与覆盖更新 | `(shop_id, fulfillment_type, posting_number, sku)` |
| `ods_ozon_analytics_data_daily` | SKU 日经营分析 18 项源指标；是销售漏斗 DWD 的原始来源 | 最近完整平台日重叠回补，14+4 指标分组分页 | 同一店铺、SKU、日期覆盖更新 | `(shop_id, sku, stat_date)` |
| `ods_ozon_analytics_totals_window` | 单次经营分析请求窗口 totals；不与 SKU 日行相加 | 跟随经营分析请求窗口写入 | 同一店铺和窗口覆盖更新 | `(shop_id, date_from, date_to)` |

## 字段解析审计

### `ods_wb_return_claims`

实际顶层字段中的申请ID、类型、状态、商品、评论、价格、币种、图片、视频、
动作及订单/交付/更新时间均已拆列。`origin_id_info` 结构可能随申请来源变化，
继续使用JSON列。所有接口时间按RFC3339解析，未携带时区时使用平台时区。

### `ods_wb_voc_chat_events`

事件、聊天、发送方、正文、商品、订单和毫秒时间戳已拆列。`attachments` 可能是
商品卡片、图片或待下载文件等异构结构，因此保留JSON。任务只保存附件元数据，
不自动下载文件。接口已废弃的买家 `clientID` 不作为业务字段或主键。

当前测试库没有聊天事件样本；首次获得非空响应后，需再次执行
`row_data` 与列结构对比。

### `ods_wb_voc_feedback_pins`

`pinId`、`feedbackId`、`nmId`、`imtId`、`state`、`pinOn`、`pinMethod`、
`changeStateAt`、`unpinnedCause` 均已拆列。`changeStateAt` 是置顶状态变化时间，
不是评价创建时间。接口需要有效订阅或资费；未开通时表和任务可以保留，但403
不能记为同步成功。

当前测试库没有置顶记录样本；字段完整性暂以官方返回结构为准，首次取得非空
响应后再次复核。

### `ods_wb_order_metadata`

顶层 `id`、`meta`、`metaDetails` 均已保存。后两者是随订单类型变化的嵌套结构，
在没有稳定口径和明确查询消费者前保留JSON，避免把临时字段固化成列。

### `ods_wb_order_fbs_supplies`

根据实际 `row_data`，除原有状态、名称、创建/关闭/扫描时间、货物类型及目的仓外，
新增拆列：

- `rejected_at` ← `rejectDt`，供货单拒绝时间；
- `recommended_warehouse_id` ← `recommendedWhId`，推荐仓库ID；
- `is_pickup_point_shipment_allowed` ← `isPickupPointShipmentAllowed`，
  是否允许发往取货点。

### `ods_wb_order_reshipment_orders`

官方业务负载主要为 `orderID` 和 `supplyID`，均已拆列。`is_active`、
`first_seen_at`、`last_seen_at`、`status_changed_at`、`resolved_at` 为本地
快照对账字段，不来自API。只有完整成功的快照才能把消失记录标记为已解决。

当前测试库无重新发货样本，首次取得非空响应后再次复核。

### `ods_wb_sales_reports_daily`

该表调用与 `ods_wb_sales_reports` 相同的 Finance API 明细端点，但请求明确传入
`period=daily`，并写入独立表。它的不可替代价值是固定日维度窗口，便于检查
平台 T+1 回填和按日对账；它不是一套可以与常规明细相加的新收入数据。

- **同步方式**：增量回补。任务每天 10:00 按平台时区执行，默认回补最近 7 天至昨天。
- **更新策略**：同一 `(shop_id, date_from, date_to, rrd_id)` 覆盖更新拆列字段和
  `row_data`；新业务键新增；不物理删除历史。
- **字段解析**：模型拆出 91 个业务及公共字段，覆盖报告范围、商品、订单、价格、
  佣金、支付、物流、仓储、促销和罚款等口径；完整 API 行仍保留在 `row_data`。
- **空响应**：HTTP 204 或空正文按空列表处理，表示本次窗口暂时没有返回记录，
  不能据此删除旧数据或将另一张财务表清空。
- **重复关系**：同一个 `rrd_id` 可能同时存在于常规财务表和按日财务表。
  下游选择其一作为统计来源，禁止 `UNION ALL` 后直接求和。

### `ods_ozon_order_unfulfilled_postings`

根据实际 `row_data`，新增拆列直接影响履约处理的时间、物流、允许操作、履约要求、
分拣中心、目的地点和多箱信息。`cutoff_at` 保持可空：v4请求使用
`cutoff_from/cutoff_to` 筛选履约截止时间，但当前订单对象没有返回可直接写入的
cutoff字段，禁止用 `shipment_date` 代替。

以下结构继续保留在完整 `row_data` 中：`optional`、`addressee`、`legal_info`、
`tariffication`、`tariffication_steps`、`container`、`prr_option` 等。原因是结构
复杂、尚无明确查询消费者，或平台口径仍可能变化；后续只有在确认稳定含义和业务
用途后才增加独立列。

### `ods_ozon_posting_report_tasks` 与 `ods_ozon_posting_report_rows`

- 报表任务表拆出 `report_code`、履约方式、请求窗口、状态、报表类型、完成时间、行数和错误信息；请求参数与状态响应保留 JSON。
- 报表行表保留完整 CSV 原始行 `row_data`，同时拆出订单/发货号、时间、状态、SKU、货号、商品属性、价格、运费、折扣和履约费用等稳定字段。
- 下载地址只作为短期任务信息使用，文档、日志和导出中不得记录签名参数或凭证。
- 每个 FBS/FBO 报表文件只有在完成、下载成功且完整解析后才提交对应类型明细；失败任务保留状态。
- 行表与订单 API 可能包含重复业务信息，下游应以统一订单 DWD 作为查询口径，不得简单相加。

### `ods_ozon_analytics_data_daily` 与 `ods_ozon_analytics_totals_window`

- API 每次最多请求 14 项指标，当前固定拆为 14 项核心指标和 4 项履约指标，使用相同 `sku + day` 维度与窗口分页后合并。
- 日明细保存两组原始行、指标请求顺序、API 时间戳和 `has_*_metrics` 标记，用于区分真实零值与该组未返回。
- totals 单独保存在窗口汇总表，禁止写入 SKU 日明细或与 SKU 行直接求和。
- ODS 保留 API 原值，不在 ODS 计算加购至下单转化率；该派生指标只在 `dwd_ozon_sales_funnel_detail` 中明确标记为项目计算值。
- 任一指标组或任一页失败时整轮回滚，避免保存半套指标。

## 改名兼容规则

迁移 `91d7e6c4a2f8` 兼容旧表、Navicat手工新表以及两者并存三种状态：

- 目标表不存在时，从已有旧表安全改名；
- 目标表和旧表并存时，先按业务主键合并；
- 合并后旧表改为 `legacy_20260728_*`，不直接删除；
- 所有模型和定时任务只写标准表；
- legacy表确认无新增写入后，才允许通过后续独立迁移清理。

**最后更新**：2026-08-26（新增 Ozon 发货报表与经营分析四张 ODS 表评审）
