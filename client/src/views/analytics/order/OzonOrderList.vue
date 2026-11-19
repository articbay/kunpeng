<template>
  <div class="order-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" label-width="90px" class="search-form">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="店铺">
              <PlatformShopSelect
                v-model="filters.shop_id"
                platform="ozon"
                @update:model-value="handleSearch"
                @shops-loaded="handleShopsLoaded"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="7">
            <el-form-item label="处理日期">
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="履约方式">
              <el-select v-model="filters.fulfillment_type" placeholder="全部" clearable>
                <el-option label="FBS（我的仓库）" value="FBS" />
                <el-option label="FBO（Ozon仓库）" value="FBO" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="9">
            <el-form-item label-width="0" class="actions">
              <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
              <el-button :icon="RefreshLeft" @click="handleReset">重置</el-button>
              <el-button
                text
                :icon="showAdvancedFilters ? ArrowUp : ArrowDown"
                @click="showAdvancedFilters = !showAdvancedFilters"
              >
                {{ showAdvancedFilters ? '收起条件' : '更多条件' }}
              </el-button>
            </el-form-item>
          </el-col>

          <template v-if="showAdvancedFilters">
            <el-col v-for="field in textFilterFields" :key="field.key" :xs="24" :sm="12" :lg="4">
              <el-form-item :label="field.label">
                <el-input
                  v-model.trim="filters[field.key]"
                  :placeholder="field.placeholder || '支持模糊查询'"
                  clearable
                  @keyup.enter="handleSearch"
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="4">
              <el-form-item label="订单ID">
                <el-input-number
                  v-model="filters.order_id"
                  :min="1"
                  :controls="false"
                  placeholder="精确查询"
                  clearable
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="4">
              <el-form-item label="Ozon SKU">
                <el-input-number
                  v-model="filters.sku"
                  :min="1"
                  :controls="false"
                  placeholder="精确查询"
                  clearable
                />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-form-item label="关键词">
                <el-input
                  v-model.trim="filters.keyword"
                  placeholder="发货号、订单号、商品、货号、状态、仓库、地区或买家"
                  clearable
                  @keyup.enter="handleSearch"
                />
              </el-form-item>
            </el-col>
          </template>
        </el-row>

      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="table-header">
          <div>
            <span class="title">Ozon FBS / FBO 统一订单</span>
            <span class="meta">共 {{ total }} 条，已选 {{ selectedRows.length }} 条</span>
          </div>
          <div class="table-actions">
            <el-radio-group v-model="filters.sort_order" size="small" @change="handleSearch">
              <el-radio-button value="desc">时间倒序</el-radio-button>
              <el-radio-button value="asc">时间正序</el-radio-button>
            </el-radio-group>
            <el-dropdown split-button type="success" :loading="exporting"
              @click="handleExport('filtered')" @command="handleExport">
              导出
              <template #dropdown><el-dropdown-menu>
                <el-dropdown-item command="filtered">导出筛选结果（最多5万行）</el-dropdown-item>
                <el-dropdown-item command="selected" :disabled="!selectedRows.length">导出已选（{{ selectedRows.length }}）</el-dropdown-item>
              </el-dropdown-menu></template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="orders"
        :row-key="rowKey"
        border
        stripe
        height="calc(100vh - 370px)"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" fixed="left" reserve-selection />
        <el-table-column label="操作" width="78" fixed="left">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetails(row)">详情</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="shop_id" label="店铺ID" width="90" />
        <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ getShopName(row.shop_id) }}</template>
        </el-table-column>
        <el-table-column label="履约方式" width="105">
          <template #default="{ row }">
            <el-tag :type="row.fulfillment_type === 'FBS' ? 'success' : 'primary'">
              {{ row.fulfillment_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="posting_number" label="发货号码" min-width="180" show-overflow-tooltip />
        <el-table-column prop="order_number" label="订单号" min-width="170" show-overflow-tooltip />
        <el-table-column label="正在处理中" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.in_process_at) }}</template>
        </el-table-column>
        <el-table-column prop="status_name_cn" label="状态" min-width="125" show-overflow-tooltip />
        <el-table-column prop="status_code" label="状态编码" min-width="145" show-overflow-tooltip />
        <el-table-column prop="product_name_cn" label="商品名称（中文）" min-width="220" show-overflow-tooltip />
        <el-table-column prop="product_name" label="商品名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="sku" label="Ozon SKU" min-width="130" />
        <el-table-column prop="offer_id" label="货号" min-width="150" show-overflow-tooltip />
        <el-table-column prop="quantity" label="数量" width="82" />
        <el-table-column label="您的价格" width="110">
          <template #default="{ row }">{{ formatAmount(row.seller_price, row.product_currency) }}</template>
        </el-table-column>
        <el-table-column label="买家支付" width="115">
          <template #default="{ row }">{{ formatAmount(row.buyer_paid_amount, row.buyer_currency) }}</template>
        </el-table-column>
        <el-table-column label="仓库" min-width="165" show-overflow-tooltip>
          <template #default="{ row }">{{ row.seller_warehouse_name || row.ozon_warehouse_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="delivery_region" label="配送地区" min-width="150" show-overflow-tooltip />
        <el-table-column prop="delivery_city" label="配送城市" min-width="140" show-overflow-tooltip />
        <el-table-column prop="delivery_city_cn" label="配送城市（中文）" min-width="160" show-overflow-tooltip />
      </el-table>

      <div class="pagination-row">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="fetchOrders"
        />
      </div>
    </el-card>

    <el-drawer v-model="detailVisible" title="Ozon 订单详情" size="72%">
      <el-alert
        title="买家信息按原始数据展示，当前未脱敏"
        type="warning"
        :closable="false"
        show-icon
        class="privacy-alert"
      />
      <section v-for="group in detailGroups" :key="group.title" class="detail-group">
        <h3>{{ group.title }}</h3>
        <el-descriptions :column="3" border>
          <el-descriptions-item v-for="field in group.fields" :key="field.key" :label="field.label">
            <span class="detail-value">{{ detailValue(field.key) }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </section>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type TableInstance } from 'element-plus'
import { ArrowDown, ArrowUp, RefreshLeft, Search } from '@element-plus/icons-vue'
import type { Shop } from '@/api/modules/shop'
import {
  ozonOrderApi,
  type OzonOrder,
  type OzonOrderExportScope,
  type OzonOrderFilters,
  type OzonOrderKey
} from '@/api/modules/ozonOrder'
import PlatformShopSelect from '@/components/PlatformShopSelect.vue'
import { downloadExcel } from '@/utils/download'

type TextFilterKey =
  | 'posting_number'
  | 'order_number'
  | 'offer_id'
  | 'status_code'
  | 'substatus_code'
  | 'warehouse_name'
  | 'delivery_region'
  | 'delivery_city'
  | 'payment_type'

interface DetailField {
  key: keyof OzonOrder
  label: string
}

const textFilterFields: Array<{ key: TextFilterKey; label: string; placeholder?: string }> = [
  { key: 'posting_number', label: '发货号码' },
  { key: 'order_number', label: '订单号' },
  { key: 'offer_id', label: '货号' },
  { key: 'status_code', label: '订单状态' },
  { key: 'substatus_code', label: '订单子状态' },
  { key: 'warehouse_name', label: '仓库' },
  { key: 'delivery_region', label: '配送地区' },
  { key: 'delivery_city', label: '配送城市' },
  { key: 'payment_type', label: '付款方式' }
]

const detailGroups: Array<{ title: string; fields: DetailField[] }> = [
  {
    title: '订单标识与状态',
    fields: fields([
      ['shop_id', '店铺ID'], ['order_type_name', '订单类型'], ['fulfillment_type', '履约方式'],
      ['posting_number', '发货号码'], ['order_id', 'Ozon订单ID'], ['order_number', '订单号'],
      ['status_code', '订单状态编码'], ['substatus_code', '订单子状态编码'], ['status_name_cn', '状态']
    ])
  },
  {
    title: '处理、发运与配送时间',
    fields: fields([
      ['in_process_month', '正在处理中（月）'], ['in_process_date', '正在处理中（日）'],
      ['in_process_hour', '正在处理中（时）'], ['in_process_at', '正在处理中'],
      ['shipment_date', '发运日期'], ['delivery_date', '配送日期'],
      ['transferred_to_delivery_at', '实际转移配送日期'],
      ['promised_delivery_at', '规定配送至买家的时间'],
      ['shipment_date_without_delay', '不逾期的发运日期'], ['cancellation_at', '取消日期'],
      ['delivery_duration_1_hours', '配送用时1（小时）'],
      ['delivery_duration_2_hours', '配送用时2（小时）'],
      ['delivery_level_1', 'level配送用时1'], ['delivery_level_2', 'level配送用时2']
    ])
  },
  {
    title: '商品与金额',
    fields: fields([
      ['product_name', '商品名称'], ['product_name_cn', '商品名称（中文）'], ['sku', 'Ozon SKU'],
      ['offer_id', '货号'], ['product_color', '商品颜色'], ['product_size', '商品尺寸'],
      ['quantity', '数量'], ['seller_price', '您的价格'], ['product_currency', '商品币种'],
      ['shipment_amount', '发货金额'], ['shipment_currency', '货件币种'],
      ['buyer_paid_amount', '已由买家支付'], ['buyer_currency', '买家币种'],
      ['delivery_fee', '运费'], ['old_price', '打折前价格'], ['discount_percent', '折扣百分比'],
      ['discount_amount', '折扣（卢布）'], ['promotion_actions', '促销活动'],
      ['is_marketplace_buyout', '商品认购'], ['product_volume_weight', '商品体积重量（公斤）']
    ])
  },
  {
    title: '仓库与物流',
    fields: fields([
      ['related_posting_number', '关联货件'], ['cluster_from', '发运集群'], ['cluster_to', '配送集群'],
      ['shipment_assessment', '发运评估'], ['ozon_warehouse_name', 'Ozon官仓'],
      ['seller_warehouse_name', '第三方仓'], ['shipment_method', '发运方法'],
      ['logistics_company', '物流公司'], ['delivery_method_name', '方式名称'],
      ['delivery_type', '配送方式'], ['delivery_region', '配送地区'], ['delivery_city', '配送城市'],
      ['delivery_city_cn', '配送城市（中文）'],
      ['declared_total_weight', '申报总重量'], ['actual_total_weight', '实际总重量'],
      ['shipment_volume_weight', '货件总体积重量']
    ])
  },
  {
    title: '买家与收件信息（未脱敏）',
    fields: fields([
      ['is_premium', '是否Premium'], ['is_legal', '是否法人'], ['payment_type', '付款方式'],
      ['buyer_name', '买家姓名'], ['buyer_email', '买家邮箱'], ['buyer_phone', '收件人电话'],
      ['buyer_address', '买家地址'], ['addressee_name', '收件人姓名'],
      ['delivery_address', '配送地址'], ['postal_code', '邮政编码']
    ])
  }
]

const loading = ref(false)
const route = useRoute()
const exporting = ref(false)
const showAdvancedFilters = ref(false)
const orders = ref<OzonOrder[]>([])
const selectedRows = ref<OzonOrder[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref<[string, string]>()
const tableRef = ref<TableInstance>()
const shops = ref<Shop[]>([])
const detailVisible = ref(false)
const detailOrder = ref<OzonOrder>()
const filters = reactive<OzonOrderFilters>({ sort_order: 'desc' })

function fields(values: Array<[keyof OzonOrder, string]>): DetailField[] {
  return values.map(([key, label]) => ({ key, label }))
}

function buildFilters(): OzonOrderFilters {
  return {
    ...filters,
    date_from: dateRange.value?.[0],
    date_to: dateRange.value?.[1]
  }
}

let fetchRequestId = 0

async function fetchOrders() {
  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const result = await ozonOrderApi.list({
      ...buildFilters(),
      page: page.value,
      page_size: pageSize.value
    })
    if (requestId === fetchRequestId) {
      orders.value = result.items
      total.value = result.total
    }
  } catch {
    if (requestId === fetchRequestId) ElMessage.error('Ozon 订单加载失败，请稍后重试')
  } finally {
    if (requestId === fetchRequestId) loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  clearSelection()
  fetchOrders()
}

function handleReset() {
  Object.keys(filters).forEach((key) => delete filters[key as keyof OzonOrderFilters])
  filters.sort_order = 'desc'
  dateRange.value = undefined
  page.value = 1
  clearSelection()
  fetchOrders()
}

function handlePageSizeChange() {
  page.value = 1
  fetchOrders()
}

function handleSelectionChange(rows: OzonOrder[]) {
  selectedRows.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

function rowKey(row: OzonOrder) {
  return `${row.shop_id}:${row.fulfillment_type}:${row.posting_number}:${row.sku}`
}

function selectedKeys(): OzonOrderKey[] {
  return selectedRows.value.map(({ shop_id, fulfillment_type, posting_number, sku }) => ({
    shop_id,
    fulfillment_type,
    posting_number,
    sku
  }))
}

async function handleExport(scope: OzonOrderExportScope) {
  if (scope === 'selected' && !selectedRows.value.length) {
    ElMessage.warning('请先选择要导出的订单')
    return
  }
  exporting.value = true
  try {
    const blob = await ozonOrderApi.export({
      scope,
      filters: buildFilters(),
      selected_keys: scope === 'selected' ? selectedKeys() : []
    })
    downloadExcel(blob, 'Ozon统一订单')
    ElMessage.success(scope === 'selected' ? '已导出选中订单' : '已导出筛选结果')
  } catch {
    ElMessage.error('导出失败；如数据超过5万行，请缩小日期或店铺范围')
  } finally {
    exporting.value = false
  }
}

function handleShopsLoaded(value: Shop[]) {
  shops.value = value
}

function getShopName(shopId: number) {
  return shops.value.find((shop) => shop.id === shopId)?.name || '-'
}

function openDetails(row: OzonOrder) {
  detailOrder.value = row
  detailVisible.value = true
}

function detailValue(key: keyof OzonOrder) {
  return formatValue(detailOrder.value?.[key])
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    return formatDateTime(value)
  }
  return String(value)
}

function formatDateTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').replace(/(Z|[+-]\d{2}:\d{2})$/, '')
}

function formatAmount(value: string | number | null, currency: string | null) {
  if (value === null || value === undefined) return '-'
  return `${value}${currency ? ` ${currency}` : ''}`
}

function hydrateRouteFilters() {
  const query = route.query
  const numeric = (value: unknown) => value ? Number(value) : undefined
  filters.shop_id = numeric(query.shop_id)
  filters.sku = numeric(query.sku)
  filters.fulfillment_type = query.fulfillment_type === 'FBS' || query.fulfillment_type === 'FBO'
    ? query.fulfillment_type : undefined
  filters.posting_number = typeof query.posting_number === 'string' ? query.posting_number : undefined
  filters.order_number = typeof query.order_number === 'string' ? query.order_number : undefined
  filters.offer_id = typeof query.offer_id === 'string' ? query.offer_id : undefined
  if (typeof query.date_from === 'string' && typeof query.date_to === 'string') {
    dateRange.value = [query.date_from, query.date_to]
  }
}

onMounted(() => { hydrateRouteFilters(); fetchOrders() })
</script>

<style scoped lang="scss">
.order-page {
  .search-card {
    margin-bottom: 16px;
  }

  .search-form :deep(.el-select),
  .search-form :deep(.el-input-number),
  .search-form :deep(.el-date-editor) {
    width: 100%;
  }

  .actions :deep(.el-form-item__content) {
    justify-content: flex-end;
  }

  .table-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .table-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .title {
    font-weight: 600;
  }

  .meta {
    margin-left: 14px;
    color: var(--el-text-color-secondary);
    font-size: 13px;
  }

  .pagination-row {
    display: flex;
    justify-content: flex-end;
    padding-top: 16px;
  }
}

.privacy-alert {
  margin-bottom: 18px;
}

.detail-group {
  margin-bottom: 24px;

  h3 {
    margin: 0 0 10px;
    font-size: 15px;
  }
}

.detail-value {
  white-space: pre-wrap;
  word-break: break-all;
}

@media (max-width: 800px) {
  .order-page .table-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
