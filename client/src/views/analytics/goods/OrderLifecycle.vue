<template>
  <div class="lifecycle-page">
    <el-card shadow="never" class="heading-card">
      <div class="heading">
        <div><h2>订单生命周期</h2><p>按平台追踪订单商品从下单、履约到取消、售出及退货的当前状态。</p></div>
        <div class="heading-side">
          <el-radio-group v-model="platform" @change="changePlatform">
            <el-radio-button value="ozon">Ozon</el-radio-button>
            <el-radio-button value="wildberries">Wildberries</el-radio-button>
          </el-radio-group>
          <div class="updated">数据更新时间：{{ formatDateTime(updatedAt) }}</div>
        </div>
      </div>
    </el-card>

    <el-alert v-if="platform === 'ozon'" title="Ozon 阶段图按已发生的履约节点累计计数，同一发货单可进入多个阶段；“配送节点”不代表买家签收。" type="warning" :closable="false" show-icon class="notice" />
    <el-alert v-else title="WB 阶段图展示互斥的当前状态；“已售出”以销售或财务数据为依据，不代表精确的买家签收时间。" type="warning" :closable="false" show-icon class="notice" />

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" label-width="88px">
        <el-row :gutter="14">
          <el-col :xs="24" :sm="12" :lg="4"><el-form-item label="店铺"><PlatformShopSelect :key="platform" v-model="filters.shop_id" :platform="platform" @update:model-value="search" @shops-loaded="shops = $event" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="7"><el-form-item label="下单日期"><el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" /></el-form-item></el-col>
          <el-col v-if="platform === 'ozon'" :xs="24" :sm="12" :lg="4"><el-form-item label="履约方式"><el-select v-model="filters.fulfillment_type" clearable placeholder="全部"><el-option label="FBS（我的仓库）" value="FBS" /><el-option label="FBO（Ozon仓库）" value="FBO" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="4"><el-form-item label="生命周期"><el-select v-model="filters.stage" clearable placeholder="全部"><el-option v-for="item in stageOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :lg="platform === 'ozon' ? 5 : 9"><el-form-item label-width="0" class="actions"><el-button type="primary" :icon="Search" @click="search">查询</el-button><el-button :icon="RefreshLeft" @click="reset">重置</el-button><el-button text :icon="advanced ? ArrowUp : ArrowDown" @click="advanced = !advanced">{{ advanced ? '收起' : '更多' }}</el-button></el-form-item></el-col>
          <template v-if="advanced">
            <el-col v-for="field in textFields" :key="field.key" :xs="24" :sm="12" :lg="4"><el-form-item :label="field.label"><el-input v-model.trim="filters[field.key]" clearable @keyup.enter="search" /></el-form-item></el-col>
            <el-col :xs="24" :sm="12" :lg="4"><el-form-item :label="platform === 'ozon' ? 'Ozon SKU' : 'WB 商品ID'"><el-input-number v-model="filters.product_id" :controls="false" :min="1" clearable /></el-form-item></el-col>
            <el-col :xs="24" :sm="12" :lg="5"><el-form-item label="异常筛选"><el-select v-model="filters.anomaly" clearable placeholder="全部"><el-option v-for="item in anomalyOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
            <el-col :xs="24" :sm="24" :lg="7"><el-form-item label="关键词"><el-input v-model.trim="filters.keyword" :placeholder="keywordPlaceholder" clearable @keyup.enter="search" /></el-form-item></el-col>
          </template>
        </el-row>
      </el-form>
    </el-card>

    <div class="kpi-grid" v-loading="summaryLoading"><el-card v-for="card in kpiCards" :key="card.label" shadow="never"><div class="kpi-label">{{ card.label }}</div><div class="kpi-value">{{ card.value }}</div><div class="kpi-note">{{ card.note }}</div></el-card></div>

    <div class="chart-grid">
      <el-card shadow="never"><template #header><strong>{{ platform === 'ozon' ? '履约阶段概览（累计节点）' : '当前生命周期阶段分布' }}</strong></template><VChart class="chart" :option="stageOption" autoresize /></el-card>
      <el-card shadow="never"><template #header><strong>下单批次趋势</strong></template><VChart class="chart" :option="trendOption" autoresize /><div class="chart-note">退货指标按原订单下单日期归属，不代表退货实际发生日期。</div></el-card>
    </div>

    <el-card shadow="never" class="status-card"><template #header><strong>{{ platform === 'ozon' ? '当前订单状态分布（发货单去重）' : '当前 WB 状态分布（订单商品）' }}</strong></template><div class="status-list"><div v-for="item in statusItems" :key="item.key" class="status-item"><span>{{ item.label }}</span><strong>{{ formatInt(item.count) }}</strong></div><el-empty v-if="!statusItems.length" description="暂无状态数据" :image-size="60" /></div></el-card>

    <el-card shadow="never" class="table-card">
      <template #header><div class="table-header"><div><strong>订单商品生命周期明细</strong><span>共 {{ total }} 条，已选 {{ selected.length }} 条</span></div><div class="table-actions"><el-radio-group v-model="filters.sort_order" size="small" @change="search"><el-radio-button value="desc">时间倒序</el-radio-button><el-radio-button value="asc">时间正序</el-radio-button></el-radio-group><el-dropdown split-button type="success" :loading="exporting" @click="exportRows('filtered')" @command="exportRows"><span>导出</span><template #dropdown><el-dropdown-menu><el-dropdown-item command="filtered">导出筛选结果（最多5万行）</el-dropdown-item><el-dropdown-item command="selected" :disabled="!selected.length">导出已选（{{ selected.length }}）</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div></div></template>
      <el-table ref="tableRef" v-loading="loading" :data="rows" :row-key="rowKey" border stripe height="570" @selection-change="selected = $event">
        <el-table-column type="selection" width="48" fixed="left" reserve-selection />
        <el-table-column label="操作" width="70" fixed="left"><template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">详情</el-button></template></el-table-column>
        <el-table-column label="订单与商品">
          <el-table-column label="下单时间" width="168"><template #default="{ row }">{{ formatDateTime(row.orderTime) }}</template></el-table-column>
          <el-table-column prop="shop_id" label="店铺ID" width="92" />
          <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip><template #default="{ row }">{{ shopName(row.shop_id) }}</template></el-table-column>
          <el-table-column v-if="platform === 'ozon'" label="履约" width="75"><template #default="{ row }"><el-tag :type="rawValue(row, 'fulfillment_type') === 'FBS' ? 'success' : 'primary'" size="small">{{ rawValue(row, 'fulfillment_type') }}</el-tag></template></el-table-column>
          <el-table-column prop="primaryId" :label="platform === 'ozon' ? '发货号码' : 'SRID'" min-width="175" show-overflow-tooltip />
          <el-table-column prop="orderNo" label="订单号" min-width="150" show-overflow-tooltip />
          <el-table-column prop="productId" :label="platform === 'ozon' ? 'Ozon SKU' : 'WB 商品ID'" width="125" />
          <el-table-column prop="sellerCode" label="卖家货号" min-width="130" show-overflow-tooltip />
          <el-table-column prop="productName" label="商品名称" min-width="210" show-overflow-tooltip />
          <el-table-column v-if="platform === 'ozon'" prop="quantity" label="数量" width="70" />
          <el-table-column v-else prop="price" label="折后价" width="100" />
        </el-table-column>
        <el-table-column label="当前状态">
          <el-table-column prop="stageLabel" label="生命周期" min-width="120" show-overflow-tooltip />
          <el-table-column prop="statusLabel" :label="platform === 'ozon' ? '订单状态' : 'WB 状态'" min-width="140" show-overflow-tooltip />
          <el-table-column v-if="platform === 'wildberries'" prop="supplierStatus" label="卖家状态" min-width="125" show-overflow-tooltip />
        </el-table-column>
        <el-table-column v-if="platform === 'ozon'" label="履约时间线">
          <el-table-column label="实际发货" width="168"><template #default="{ row }">{{ formatDateTime(stringValue(row, 'shipment_date')) }}</template></el-table-column>
          <el-table-column label="移交配送" width="168"><template #default="{ row }">{{ formatDateTime(stringValue(row, 'transferred_to_delivery_at')) }}</template></el-table-column>
          <el-table-column label="配送节点（非签收）" width="180"><template #default="{ row }">{{ formatDateTime(stringValue(row, 'delivery_date')) }}</template></el-table-column>
          <el-table-column label="取消时间" width="168"><template #default="{ row }">{{ formatDateTime(stringValue(row, 'cancellation_at')) }}</template></el-table-column>
        </el-table-column>
        <el-table-column v-else label="供货与销售">
          <el-table-column label="供货单" min-width="135"><template #default="{ row }">{{ display(rawValue(row, 'supply_id')) }}</template></el-table-column>
          <el-table-column label="仓库" min-width="130"><template #default="{ row }">{{ display(rawValue(row, 'warehouse_name_cn') || rawValue(row, 'warehouse_name')) }}</template></el-table-column>
          <el-table-column label="供货扫描" width="168"><template #default="{ row }">{{ formatDateTime(stringValue(row, 'supply_scan_at')) }}</template></el-table-column>
          <el-table-column label="销售时间" width="168"><template #default="{ row }">{{ formatDateTime(stringValue(row, 'sale_at') || stringValue(row, 'finance_first_sale_at')) }}</template></el-table-column>
        </el-table-column>
        <el-table-column label="退货情况"><el-table-column prop="returnCount" label="记录数" width="80" /><el-table-column prop="returnStatus" label="最新状态" min-width="150" show-overflow-tooltip /><el-table-column prop="returnReason" label="最新原因" min-width="160" show-overflow-tooltip /></el-table-column>
        <el-table-column label="数据状态" width="140"><template #default="{ row }"><div class="tags"><el-tag v-if="row.isCancelled" type="info" size="small">已取消</el-tag><el-tag v-if="row.returnCount" type="warning" size="small">有退货</el-tag><el-tag v-if="row.isSold" type="success" size="small">已售出</el-tag><el-tag v-if="row.hasConflict" type="danger" size="small">关联冲突</el-tag></div></template></el-table-column>
      </el-table>
      <div class="pagination"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20, 50, 100]" :total="total" layout="total, sizes, prev, pager, next, jumper" @size-change="search" @current-change="fetchRows" /></div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="`${platformName} 订单生命周期详情`" size="820px">
      <template v-if="current">
        <el-descriptions :column="2" border class="summary-descriptions"><el-descriptions-item :label="platform === 'ozon' ? '发货号码' : 'SRID'">{{ current.primaryId }}</el-descriptions-item><el-descriptions-item label="订单号">{{ display(current.orderNo) }}</el-descriptions-item><el-descriptions-item :label="platform === 'ozon' ? 'SKU / 货号' : 'WB商品ID / 货号'">{{ display(current.productId) }} / {{ display(current.sellerCode) }}</el-descriptions-item><el-descriptions-item label="商品名称">{{ display(current.productName) }}</el-descriptions-item></el-descriptions>
        <h3>履约时间线</h3><el-timeline><el-timeline-item v-for="node in timeline" :key="`${node.label}:${node.time}`" :timestamp="formatDateTime(node.time)" :type="node.type">{{ node.label }}<div v-if="node.note" class="timeline-note">{{ node.note }}</div></el-timeline-item></el-timeline>
        <section v-for="group in detailGroups" :key="group.title" class="detail-group"><h3>{{ group.title }}</h3><el-descriptions :column="2" border><el-descriptions-item v-for="field in group.fields" :key="field.key" :label="field.label">{{ detailValue(field.key) }}</el-descriptions-item></el-descriptions></section>
        <div class="drill-actions"><el-button type="primary" plain @click="goOrder">查看来源订单</el-button><el-button type="warning" plain :disabled="!current.returnCount" @click="goReturn">查看退货明细</el-button></div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type TableInstance, type TimelineItemProps } from 'element-plus'
import { ArrowDown, ArrowUp, RefreshLeft, Search } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import PlatformShopSelect from '@/components/PlatformShopSelect.vue'
import type { Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'
import { ozonOrderLifecycleApi, type LifecycleFilters, type LifecycleSummary, type OzonOrderLifecycleItem } from '@/api/modules/ozonOrderLifecycle'
import { wbOrderLifecycleApi, type WBOrderLifecycleFilters, type WBOrderLifecycleItem, type WBOrderLifecycleSummary } from '@/api/modules/wbOrderLifecycle'

use([CanvasRenderer, BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent])
type Platform = 'ozon' | 'wildberries'
type RawRow = OzonOrderLifecycleItem | WBOrderLifecycleItem
type FilterTextKey = 'primary_id' | 'order_no' | 'supply_id' | 'seller_code' | 'status' | 'substatus' | 'return_status' | 'return_reason'
interface Filters { shop_id?: number; fulfillment_type?: 'FBS' | 'FBO'; stage?: string; anomaly?: string; product_id?: number; keyword?: string; sort_order: 'asc' | 'desc'; primary_id?: string; order_no?: string; supply_id?: string; seller_code?: string; status?: string; substatus?: string; return_status?: string; return_reason?: string }
interface UnifiedRow { shop_id: number; rowId: string; orderTime: string | null; primaryId: string; orderNo: string | number | null; productId: string | number | null; sellerCode: string | null; productName: string | null; quantity: number | null; price: string | number | null; stageLabel: string; statusLabel: string | null; supplierStatus: string | null; returnCount: number; returnStatus: string | null; returnReason: string | null; isCancelled: boolean; isSold: boolean; hasConflict: boolean; raw: RawRow }

const route = useRoute(), router = useRouter()
const platform = ref<Platform>(route.query.platform === 'wildberries' ? 'wildberries' : 'ozon')
const loading = ref(false), summaryLoading = ref(false), exporting = ref(false), advanced = ref(false)
const rows = ref<UnifiedRow[]>([]), selected = ref<UnifiedRow[]>([]), shops = ref<Shop[]>([])
const ozonSummary = ref<LifecycleSummary>(), wbSummary = ref<WBOrderLifecycleSummary>()
const current = ref<UnifiedRow>(), drawerVisible = ref(false), tableRef = ref<TableInstance>()
const page = ref(1), pageSize = ref(20), total = ref(0)
const filters = reactive<Filters>({ sort_order: 'desc' })
const dateRange = ref<[string, string]>(defaultRange())
let rowsRequestId = 0
let summaryRequestId = 0
const platformName = computed(() => platform.value === 'ozon' ? 'Ozon' : 'WB')
const updatedAt = computed(() => platform.value === 'ozon' ? ozonSummary.value?.updated_at : wbSummary.value?.updated_at)
const keywordPlaceholder = computed(() => platform.value === 'ozon' ? '发货号、订单号、商品、货号、状态或退货原因' : 'SRID、订单号、供货单、商品、状态或退货原因')
const textFields = computed<Array<{ key: FilterTextKey; label: string }>>(() => platform.value === 'ozon' ? [
  { key: 'primary_id', label: '发货号码' }, { key: 'order_no', label: '订单号' }, { key: 'seller_code', label: '卖家货号' }, { key: 'status', label: '订单状态' }, { key: 'substatus', label: '子状态' }, { key: 'return_status', label: '退货状态' }, { key: 'return_reason', label: '退货原因' }
] : [
  { key: 'primary_id', label: 'SRID' }, { key: 'order_no', label: '订单ID' }, { key: 'supply_id', label: '供货单号' }, { key: 'seller_code', label: '卖家货号' }, { key: 'status', label: 'WB状态' }, { key: 'substatus', label: '卖家状态' }, { key: 'return_status', label: '退货状态' }, { key: 'return_reason', label: '退货原因' }
])
const stageOptions = computed(() => (platform.value === 'ozon' ? [
  ['待发货', 'pending_shipment'], ['已发货', 'shipped'], ['已移交配送', 'transferred'], ['已记录配送节点', 'delivery_node'], ['已取消', 'cancelled'], ['发生退货', 'returned']
] : [
  ['新订单', 'new'], ['组装中', 'assembling'], ['配送中', 'in_delivery'], ['WB已接收', 'wb_received'], ['待取件', 'ready_for_pickup'], ['已售出', 'sold'], ['已取消', 'cancelled'], ['已退货', 'returned'], ['状态未知', 'unknown']
]).map(([label, value]) => ({ label, value })))
const anomalyOptions = computed(() => platform.value === 'ozon' ? [
  { label: '承诺时间已过且无配送节点（待核查）', value: 'promise_passed_without_delivery_node' }, { label: '退货数量大于下单数量', value: 'return_qty_exceeds_ordered' }, { label: '有退货但最新状态缺失', value: 'return_status_missing' }
] : [
  { label: '当前状态缺失', value: 'missing_current_status' }, { label: '退货身份关联冲突', value: 'return_identity_conflict' }, { label: '终态缺少对应时间', value: 'terminal_without_time' }
])

function ymd(value: Date) { return value.toISOString().slice(0, 10) }
function defaultRange(): [string, string] { const end = new Date(); const start = new Date(); start.setDate(end.getDate() - 29); return [ymd(start), ymd(end)] }
function ozonFilters(): LifecycleFilters { return { shop_id: filters.shop_id, date_from: dateRange.value?.[0], date_to: dateRange.value?.[1], fulfillment_type: filters.fulfillment_type, posting_number: filters.primary_id, order_number: filters.order_no, sku: filters.product_id, offer_id: filters.seller_code, status_code: filters.status, substatus_code: filters.substatus, return_status: filters.return_status, return_reason: filters.return_reason, keyword: filters.keyword, stage: filters.stage as LifecycleFilters['stage'], anomaly: filters.anomaly as LifecycleFilters['anomaly'], sort_order: filters.sort_order } }
function wbFilters(): WBOrderLifecycleFilters { return { shop_id: filters.shop_id, date_from: dateRange.value?.[0], date_to: dateRange.value?.[1], srid: filters.primary_id, order_id: filters.order_no ? Number(filters.order_no) : undefined, supply_id: filters.supply_id, nm_id: filters.product_id, supplier_article: filters.seller_code, supplier_status: filters.substatus, wb_status: filters.status, return_status: filters.return_status, return_reason: filters.return_reason, keyword: filters.keyword, stage: filters.stage as WBOrderLifecycleFilters['stage'], anomaly: filters.anomaly as WBOrderLifecycleFilters['anomaly'], sort_order: filters.sort_order } }
function normalizeOzon(row: OzonOrderLifecycleItem): UnifiedRow { return { shop_id: row.shop_id, rowId: `${row.shop_id}:${row.fulfillment_type}:${row.posting_number}:${row.sku}`, orderTime: row.in_process_at, primaryId: row.posting_number, orderNo: row.order_number, productId: row.sku, sellerCode: row.offer_id, productName: row.product_name_cn || row.product_name, quantity: row.quantity, price: null, stageLabel: ozonStage(row), statusLabel: row.status_name_cn || row.status_code, supplierStatus: null, returnCount: row.return_cnt, returnStatus: row.latest_return_status_display_name_cn || row.latest_return_status_sys_name, returnReason: row.latest_return_reason_name_cn, isCancelled: Boolean(row.cancellation_at), isSold: false, hasConflict: false, raw: row } }
function normalizeWB(row: WBOrderLifecycleItem): UnifiedRow { return { shop_id: row.shop_id, rowId: `${row.shop_id}:${row.srid}`, orderTime: row.order_at, primaryId: row.srid, orderNo: row.order_id, productId: row.nm_id, sellerCode: row.supplier_article, productName: row.product_title_cn || row.product_title, quantity: null, price: row.price_with_disc, stageLabel: row.lifecycle_stage_cn, statusLabel: row.wb_status_cn || row.wb_status, supplierStatus: row.supplier_status_cn || row.supplier_status, returnCount: row.return_cnt, returnStatus: row.latest_return_status_cn || row.latest_return_status, returnReason: row.latest_return_reason_cn || row.latest_return_reason, isCancelled: row.is_cancelled, isSold: row.is_sold, hasConflict: row.has_return_identity_conflict, raw: row } }
function ozonStage(row: OzonOrderLifecycleItem) { if (row.return_cnt) return '发生退货'; if (row.cancellation_at) return '已取消'; if (row.delivery_date) return '配送节点'; if (row.transferred_to_delivery_at) return '已移交配送'; if (row.shipment_date) return '已发货'; return '待发货' }
async function fetchRows() { const requestId = ++rowsRequestId; loading.value = true; try { if (platform.value === 'ozon') { const result = await ozonOrderLifecycleApi.list({ ...ozonFilters(), page: page.value, page_size: pageSize.value }); if (requestId !== rowsRequestId) return; rows.value = result.items.map(normalizeOzon); total.value = result.total } else { const result = await wbOrderLifecycleApi.list({ ...wbFilters(), page: page.value, page_size: pageSize.value }); if (requestId !== rowsRequestId) return; rows.value = result.items.map(normalizeWB); total.value = result.total } } catch { if (requestId === rowsRequestId) ElMessage.error(`${platformName.value} 订单生命周期加载失败`) } finally { if (requestId === rowsRequestId) loading.value = false } }
async function fetchSummary() { const requestId = ++summaryRequestId; summaryLoading.value = true; try { if (platform.value === 'ozon') { const result = await ozonOrderLifecycleApi.summary(ozonFilters()); if (requestId === summaryRequestId) ozonSummary.value = result } else { const result = await wbOrderLifecycleApi.summary(wbFilters()); if (requestId === summaryRequestId) wbSummary.value = result } } catch { if (requestId === summaryRequestId) ElMessage.error(`${platformName.value} 订单生命周期汇总加载失败`) } finally { if (requestId === summaryRequestId) summaryLoading.value = false } }
function search() { page.value = 1; tableRef.value?.clearSelection(); selected.value = []; void Promise.all([fetchRows(), fetchSummary()]) }
function clearPlatformFilters() { const sort = filters.sort_order; Object.keys(filters).forEach((key) => delete filters[key as keyof Filters]); filters.sort_order = sort }
function reset() { clearPlatformFilters(); filters.sort_order = 'desc'; dateRange.value = defaultRange(); advanced.value = false; search() }
function changePlatform() { clearPlatformFilters(); rows.value = []; selected.value = []; current.value = undefined; drawerVisible.value = false; shops.value = []; void router.replace({ path: '/analytics/goods/lifecycle', query: { ...route.query, platform: platform.value } }); search() }
async function exportRows(scope: 'filtered' | 'selected') { if (scope === 'selected' && !selected.value.length) return; exporting.value = true; try { if (platform.value === 'ozon') { const selected_keys = selected.value.map((row) => { const raw = row.raw as OzonOrderLifecycleItem; return { shop_id: raw.shop_id, fulfillment_type: raw.fulfillment_type, posting_number: raw.posting_number, sku: raw.sku } }); const blob = await ozonOrderLifecycleApi.export({ scope, filters: ozonFilters(), selected_keys }); downloadExcel(blob, 'Ozon订单生命周期') } else { const selected_keys = selected.value.map((row) => { const raw = row.raw as WBOrderLifecycleItem; return { shop_id: raw.shop_id, srid: raw.srid } }); const blob = await wbOrderLifecycleApi.export({ scope, filters: wbFilters(), selected_keys }); downloadExcel(blob, 'WB订单生命周期') } ElMessage.success('导出成功') } catch { ElMessage.error('导出失败') } finally { exporting.value = false } }
function rowKey(row: UnifiedRow) { return row.rowId }
function shopName(id: number) { return shops.value.find((shop) => shop.id === id)?.name || `店铺 ${id}` }
function rawValue(row: UnifiedRow, key: string): unknown { return (row.raw as unknown as Record<string, unknown>)[key] }
function stringValue(row: UnifiedRow, key: string) { const value = rawValue(row, key); return typeof value === 'string' ? value : null }
function display(value: unknown) { return value === null || value === undefined || value === '' ? '—' : String(value) }
function formatInt(value: number) { return Number(value || 0).toLocaleString('zh-CN') }
function percent(value: number) { return `${(Number(value || 0) * 100).toFixed(1)}%` }
function formatDateTime(value?: string | null) { return value ? value.replace('T', ' ').replace(/(Z|[+-]\d{2}:\d{2})$/, '') : '—' }

const kpiCards = computed(() => { if (platform.value === 'ozon') { const m = ozonSummary.value?.metrics; if (!m) return []; return [
  { label: '发货单数', value: formatInt(m.posting_count), note: `${formatInt(m.item_row_count)} 个商品行` }, { label: '下单件数', value: formatInt(m.order_qty), note: '商品数量合计' }, { label: '已发货发货单', value: `${formatInt(m.shipped_posting_count)} / ${percent(m.shipped_rate)}`, note: '按发货单去重' }, { label: '已取消发货单', value: `${formatInt(m.cancelled_posting_count)} / ${percent(m.cancelled_rate)}`, note: '按发货单去重' }, { label: '发生退货商品行', value: `${formatInt(m.returned_item_count)} / ${percent(m.returned_item_rate)}`, note: '按订单商品行计算' }, { label: '累计退货件数', value: formatInt(m.return_qty), note: '当前已关联退货' }
] } const m = wbSummary.value?.metrics; if (!m) return []; const coverage = m.order_count ? m.marketplace_covered_count / m.order_count : 0; return [
  { label: '订单商品数', value: formatInt(m.order_count), note: '按店铺与 SRID 去重' }, { label: '已售出', value: `${formatInt(m.sold_count)} / ${percent(m.sold_rate)}`, note: '销售或财务证据口径' }, { label: '已取消', value: `${formatInt(m.cancelled_count)} / ${percent(m.cancelled_rate)}`, note: '当前已取消订单商品' }, { label: '发生退货', value: `${formatInt(m.returned_count)} / ${percent(m.returned_rate)}`, note: '已关联退货记录' }, { label: '已进入终态', value: formatInt(m.terminal_count), note: '售出、取消或退货' }, { label: 'Marketplace覆盖', value: `${formatInt(m.marketplace_covered_count)} / ${percent(coverage)}`, note: '存在 Marketplace 订单数据' }
] })
const stageOption = computed(() => { const stages = platform.value === 'ozon' ? (ozonSummary.value?.stages || []).map((x) => ({ label: x.label, count: x.posting_count })) : (wbSummary.value?.stages || []).map((x) => ({ label: x.label, count: x.order_count })); return { tooltip: { trigger: 'axis' }, grid: { left: 115, right: 35, top: 15, bottom: 25 }, xAxis: { type: 'value' }, yAxis: { type: 'category', inverse: true, data: stages.map((x) => x.label) }, series: [{ type: 'bar', data: stages.map((x) => x.count), itemStyle: { color: platform.value === 'ozon' ? '#67c23a' : '#7b4fc9' }, label: { show: true, position: 'right' } }] } })
const trendOption = computed(() => { if (platform.value === 'ozon') { const trend = ozonSummary.value?.trend || []; return { tooltip: { trigger: 'axis' }, legend: { top: 0 }, grid: { left: 45, right: 25, top: 42, bottom: 30 }, xAxis: { type: 'category', data: trend.map((x) => x.stat_date) }, yAxis: { type: 'value' }, series: [{ name: '发货单数', type: 'bar', data: trend.map((x) => x.posting_count) }, { name: '下单件数', type: 'line', data: trend.map((x) => x.order_qty) }, { name: '取消发货单', type: 'line', data: trend.map((x) => x.cancelled_posting_count) }, { name: '当前退货件数', type: 'line', data: trend.map((x) => x.return_qty) }] } } const trend = wbSummary.value?.trend || []; return { tooltip: { trigger: 'axis' }, legend: { top: 0 }, grid: { left: 45, right: 25, top: 42, bottom: 30 }, xAxis: { type: 'category', data: trend.map((x) => x.stat_date) }, yAxis: { type: 'value' }, series: [{ name: '订单商品数', type: 'bar', data: trend.map((x) => x.order_count) }, { name: '已售出', type: 'line', data: trend.map((x) => x.sold_count) }, { name: '已取消', type: 'line', data: trend.map((x) => x.cancelled_count) }, { name: '发生退货', type: 'line', data: trend.map((x) => x.returned_count) }] } })
const statusItems = computed(() => platform.value === 'ozon' ? (ozonSummary.value?.statuses || []).map((x) => ({ key: `${x.status_code}:${x.status_name_cn}`, label: x.status_name_cn || x.status_code || '状态未返回', count: x.posting_count })) : (wbSummary.value?.statuses || []).map((x) => ({ key: `${x.wb_status}:${x.wb_status_cn}`, label: x.wb_status_cn || x.wb_status || '状态未返回', count: x.order_count })))

const ozonGroups = groups([
  ['订单标识', [['shop_id', '店铺ID'], ['fulfillment_type', '履约方式'], ['posting_number', '发货号码'], ['order_id', '订单ID'], ['order_number', '订单号'], ['status_code', '状态编码'], ['substatus_code', '子状态编码'], ['status_name_cn', '当前状态']]],
  ['商品信息', [['sku', 'Ozon SKU'], ['offer_id', '卖家货号'], ['product_name_cn', '商品名称（中文）'], ['product_name', '商品名称'], ['quantity', '下单数量']]],
  ['退货情况', [['return_cnt', '退货记录数'], ['return_qty', '累计退货数量'], ['first_return_date', '首次退货日期'], ['latest_return_status_display_name_cn', '最新退货状态'], ['latest_return_status_change_at', '最新状态变更时间'], ['latest_return_reason_name_cn', '最新退货原因'], ['last_ready_to_pickup_at', '最近到达取货点'], ['last_picked_up_at', '最近向卖家退回']]],
  ['数据质量', [['create_time', '创建时间'], ['update_time', '更新时间']]]
])
const wbGroups = groups([
  ['订单与商品', [['shop_id', '店铺ID'], ['srid', 'SRID'], ['order_id', '订单ID'], ['order_uid', '订单UID'], ['g_number', 'G Number'], ['nm_id', 'WB商品ID'], ['supplier_article', '卖家货号'], ['barcode', '条码'], ['product_title_cn', '商品名称'], ['subject_name_cn', '品类'], ['tech_size_cn', '尺码'], ['price_with_disc', '折后价格']]],
  ['当前状态', [['lifecycle_stage_cn', '生命周期'], ['supplier_status_cn', '卖家状态'], ['wb_status_cn', 'WB状态'], ['is_cancelled', '已取消'], ['is_sold', '已售出'], ['is_terminal', '已进入终态'], ['last_change_at', '最近变更时间'], ['cancelled_at', '取消时间']]],
  ['供货与物流', [['supply_id', '供货单ID'], ['supply_name', '供货单名称'], ['supply_is_done', '供货单已完成'], ['delivery_type', '配送类型'], ['warehouse_name_cn', '仓库'], ['region_name_cn', '地区'], ['supply_created_at', '供货单创建'], ['supply_scan_at', '供货扫描'], ['supply_closed_at', '供货关闭'], ['supply_rejected_at', '供货拒绝']]],
  ['销售与财务', [['sale_at', '销售时间'], ['sale_id', '销售ID'], ['sale_event_type', '销售事件'], ['finance_row_cnt', '财务记录数'], ['finance_sale_row_cnt', '财务销售记录数'], ['finance_first_sale_at', '首次财务销售时间']]],
  ['退货情况', [['return_cnt', '退货记录数'], ['latest_return_srid', '最新退货SRID'], ['latest_return_status_cn', '最新退货状态'], ['latest_return_type_cn', '最新退货类型'], ['latest_return_reason_cn', '最新退货原因'], ['return_ready_at', '退货可取'], ['return_completed_at', '退货完成'], ['return_expired_at', '退货过期'], ['return_link_method', '退货关联方式'], ['has_return_identity_conflict', '退货身份冲突']]],
  ['数据来源与质量', [['has_statistics_order_data', '统计订单数据'], ['has_marketplace_order_data', 'Marketplace订单数据'], ['has_supply_data', '供货数据'], ['has_sale_data', '销售数据'], ['has_finance_data', '财务数据'], ['has_return_data', '退货数据'], ['create_time', '创建时间'], ['update_time', '更新时间']]]
])
function groups(values: Array<[string, string[][]]>) { return values.map(([title, values]) => ({ title, fields: values.map(([key, label]) => ({ key, label })) })) }
const detailGroups = computed(() => platform.value === 'ozon' ? ozonGroups : wbGroups)
function openDetail(row: UnifiedRow) { current.value = row; drawerVisible.value = true }
const timeline = computed<Array<{ label: string; time: string | null; type: TimelineItemProps['type']; note?: string }>>(() => { if (!current.value) return []; const row = current.value; if (platform.value === 'ozon') return [
  { label: '进入处理', time: stringValue(row, 'in_process_at'), type: 'primary' }, { label: '实际发货', time: stringValue(row, 'shipment_date'), type: stringValue(row, 'shipment_date') ? 'success' : 'info' }, { label: '移交配送', time: stringValue(row, 'transferred_to_delivery_at'), type: stringValue(row, 'transferred_to_delivery_at') ? 'success' : 'info' }, { label: '记录配送节点', time: stringValue(row, 'delivery_date'), type: stringValue(row, 'delivery_date') ? 'success' : 'info', note: '此节点不代表买家签收' }, ...(stringValue(row, 'cancellation_at') ? [{ label: '订单取消', time: stringValue(row, 'cancellation_at'), type: 'danger' as const }] : []), ...(stringValue(row, 'first_return_date') ? [{ label: '首次退货', time: stringValue(row, 'first_return_date'), type: 'warning' as const }] : [])
]; return [
  { label: '订单创建', time: stringValue(row, 'order_at'), type: 'primary' }, ...(stringValue(row, 'supply_created_at') ? [{ label: '供货单创建', time: stringValue(row, 'supply_created_at'), type: 'success' as const }] : []), ...(stringValue(row, 'supply_scan_at') ? [{ label: '供货扫描', time: stringValue(row, 'supply_scan_at'), type: 'success' as const }] : []), ...(stringValue(row, 'supply_closed_at') ? [{ label: '供货关闭', time: stringValue(row, 'supply_closed_at'), type: 'success' as const }] : []), ...(stringValue(row, 'supply_rejected_at') ? [{ label: '供货拒绝', time: stringValue(row, 'supply_rejected_at'), type: 'danger' as const }] : []), ...(stringValue(row, 'sale_at') || stringValue(row, 'finance_first_sale_at') ? [{ label: '取得销售证据', time: stringValue(row, 'sale_at') || stringValue(row, 'finance_first_sale_at'), type: 'success' as const, note: '销售或财务数据口径，不代表精确签收时间' }] : []), ...(stringValue(row, 'cancelled_at') ? [{ label: '订单取消', time: stringValue(row, 'cancelled_at'), type: 'danger' as const }] : []), ...(stringValue(row, 'return_ready_at') ? [{ label: '退货可取', time: stringValue(row, 'return_ready_at'), type: 'warning' as const }] : []), ...(stringValue(row, 'return_completed_at') ? [{ label: '退货完成', time: stringValue(row, 'return_completed_at'), type: 'warning' as const }] : []), ...(stringValue(row, 'return_expired_at') ? [{ label: '退货过期', time: stringValue(row, 'return_expired_at'), type: 'info' as const }] : [])
] })
function detailValue(key: string) { if (!current.value) return '—'; const value = rawValue(current.value, key); if (typeof value === 'boolean') return value ? '是' : '否'; if (key.endsWith('_at') || key.includes('date') || key.endsWith('_time')) return formatDateTime(typeof value === 'string' ? value : null); return display(value) }
function drillQuery() { if (!current.value) return {}; return platform.value === 'ozon' ? { platform: 'ozon', shop_id: String(current.value.shop_id), fulfillment_type: display(rawValue(current.value, 'fulfillment_type')), posting_number: current.value.primaryId, order_number: current.value.orderNo || undefined, sku: String(current.value.productId || ''), offer_id: current.value.sellerCode || undefined } : { platform: 'wildberries', shop_id: String(current.value.shop_id), srid: current.value.primaryId, order_id: current.value.orderNo || undefined, nm_id: current.value.productId || undefined, supplier_article: current.value.sellerCode || undefined } }
function goOrder() { router.push({ path: platform.value === 'ozon' ? '/analytics/orders' : '/analytics/orders/statistics', query: drillQuery() }) }
function goReturn() { router.push({ path: '/analytics/returns', query: drillQuery() }) }
onMounted(search)
</script>

<style scoped lang="scss">
.lifecycle-page { .heading-card, .notice, .filter-card, .status-card, .table-card { margin-bottom: 16px; } .heading, .heading-side, .table-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; } .heading-side { justify-content: flex-end; } .table-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; } h2 { margin: 0; font-size: 20px; } p { margin: 6px 0 0; color: var(--el-text-color-secondary); } .updated, .table-header span { color: var(--el-text-color-secondary); font-size: 13px; margin-left: 12px; } :deep(.el-date-editor), :deep(.el-select), :deep(.el-input-number) { width: 100%; } .actions :deep(.el-form-item__content) { justify-content: flex-end; flex-wrap: nowrap; } }
.kpi-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }.kpi-label { color: var(--el-text-color-secondary); font-size: 13px; }.kpi-value { margin: 10px 0 6px; font-size: 21px; font-weight: 650; }.kpi-note, .chart-note, .timeline-note { color: var(--el-text-color-secondary); font-size: 12px; }.chart-grid { display: grid; grid-template-columns: 2fr 3fr; gap: 16px; margin-bottom: 16px; }.chart { height: 300px; }.chart-note { text-align: center; }.status-list { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }.status-item { display: flex; justify-content: space-between; gap: 10px; padding: 10px 12px; background: var(--el-fill-color-light); border-radius: 6px; }.tags { display: flex; flex-wrap: wrap; gap: 4px; }.pagination { display: flex; justify-content: flex-end; padding-top: 16px; }.summary-descriptions { margin-bottom: 22px; }.detail-group { margin: 22px 0; h3 { margin: 0 0 10px; font-size: 15px; } }.drill-actions { display: flex; gap: 10px; }
@media (max-width: 1200px) { .kpi-grid { grid-template-columns: repeat(3, 1fr); } .chart-grid { grid-template-columns: 1fr; } .status-list { grid-template-columns: repeat(3, 1fr); } } @media (max-width: 700px) { .kpi-grid, .status-list { grid-template-columns: 1fr 1fr; } .lifecycle-page .heading, .lifecycle-page .heading-side { align-items: flex-start; flex-direction: column; } }
</style>
