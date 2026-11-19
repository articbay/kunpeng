<template>
  <div class="return-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" label-width="92px" class="search-form">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="店铺">
              <PlatformShopSelect
                v-model="filters.shop_id"
                platform="ozon"
                @update:model-value="handleSearch"
                @shops-loaded="shops = $event"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="7">
            <el-form-item label="统计时间">
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
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="退货 ID">
              <el-input-number
                v-model="filters.return_id"
                :min="1"
                :controls="false"
                placeholder="请输入"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="Ozon SKU">
              <el-input-number
                v-model="filters.nm_id"
                :min="1"
                :controls="false"
                placeholder="请输入"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="13" style="order: 1">
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

          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="配货单号">
              <el-input
                v-model.trim="filters.posting_number"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="订单 ID">
              <el-input-number
                v-model="filters.order_id"
                :min="1"
                :controls="false"
                placeholder="请输入"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="订单编号">
              <el-input
                v-model.trim="filters.order_number"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="商家货号">
              <el-input
                v-model.trim="filters.offer_id"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="品牌">
              <el-input
                v-model.trim="filters.brand_name"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="商品品类">
              <el-input
                v-model.trim="filters.category_name"
                placeholder="支持中俄文查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>

          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="商品名称">
              <el-input
                v-model.trim="filters.product_name"
                placeholder="支持中俄文查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="状态">
              <el-input
                v-model.trim="filters.status"
                placeholder="名称或状态编码"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="退货类型">
              <el-input
                v-model.trim="filters.return_type"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="发货模式">
              <el-select v-model="filters.schema" placeholder="全部" clearable>
                <el-option label="FBO" value="Fbo" />
                <el-option label="FBS" value="Fbs" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="24" :lg="8">
            <el-form-item label="关键词">
              <el-input
                v-model.trim="filters.keyword"
                placeholder="退货、订单、商品、条码、原因或地点"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
        </el-row>

      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="table-header">
          <div>
            <span class="title">Ozon 退货</span>
            <span class="meta">共 {{ total }} 条，已选 {{ selectedRows.length }} 条</span>
          </div>
          <div class="table-actions">
            <el-radio-group v-model="filters.sort_order" size="small" @change="handleSearch">
              <el-radio-button value="desc">日期倒序</el-radio-button>
              <el-radio-button value="asc">日期正序</el-radio-button>
            </el-radio-group>
            <el-dropdown split-button type="success" :loading="exporting"
              @click="handleExportFiltered" @command="handleExportCommand">
              导出
              <template #dropdown><el-dropdown-menu>
                <el-dropdown-item command="filtered">导出筛选结果</el-dropdown-item>
                <el-dropdown-item command="selected" :disabled="!selectedRows.length">导出已选（{{ selectedRows.length }}）</el-dropdown-item>
              </el-dropdown-menu></template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="returns"
        :row-key="rowKey"
        border
        stripe
        height="calc(100vh - 300px)"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" fixed="left" reserve-selection />
        <el-table-column prop="shop_id" label="店铺ID" width="100" />
        <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ getShopName(row.shop_id) }}</template>
        </el-table-column>
        <el-table-column
          v-for="column in tableColumns"
          :key="column.key"
          :prop="column.key"
          :label="column.label"
          :width="column.width"
          :min-width="column.minWidth"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            {{ formatColumnValue(row[column.key], column.format) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="84" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无 Ozon 退货数据" />
        </template>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="fetchReturns"
        />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" title="Ozon 退货详情" size="820px">
      <el-descriptions v-if="currentRow" :column="2" border>
        <el-descriptions-item label="店铺ID">{{ currentRow.shop_id }}</el-descriptions-item>
        <el-descriptions-item label="店铺名称">{{ getShopName(currentRow.shop_id) }}</el-descriptions-item>
        <el-descriptions-item
          v-for="column in tableColumns"
          :key="column.key"
          :label="column.label"
          :span="column.detailSpan || 1"
        >
          <div :class="{ 'long-text': column.detailSpan === 2 }">
            {{ formatColumnValue(currentRow[column.key], column.format) }}
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, type TableInstance } from 'element-plus'
import { ArrowDown, ArrowUp, RefreshLeft, Search } from '@element-plus/icons-vue'
import PlatformShopSelect from '@/components/PlatformShopSelect.vue'
import type { Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'
import {
  ozonReturnApi,
  type OzonReturn,
  type OzonReturnExportScope,
  type OzonReturnFilters,
  type OzonReturnKey
} from '@/api/modules/ozonReturn'

type ReturnFilterForm = OzonReturnFilters & {
  sort_order: 'asc' | 'desc'
}
type ColumnFormat = 'datetime' | 'boolean' | 'schema'
type ReturnColumn = {
  key: keyof OzonReturn
  label: string
  width?: number
  minWidth?: number
  format?: ColumnFormat
  detailSpan?: 1 | 2
}

const tableColumns: ReturnColumn[] = [
  { key: 'schema', label: '模式', width: 90, format: 'schema' },
  { key: 'product_name', label: '商品名称', minWidth: 240, detailSpan: 2 },
  { key: 'product_name_cn', label: '商品名称（中文）', minWidth: 240, detailSpan: 2 },
  { key: 'posting_number', label: '货件编号', minWidth: 170 },
  { key: 'offer_id', label: '货号', minWidth: 150 },
  { key: 'nm_id', label: 'OZON SKU ID', minWidth: 135 },
  { key: 'order_date', label: '下订单日期', minWidth: 180, format: 'datetime' },
  { key: 'return_date', label: '退货日期', minWidth: 180, format: 'datetime' },
  { key: 'status_display_name', label: '退货状态', minWidth: 180 },
  { key: 'status_display_name_cn', label: '退货状态（中文）', minWidth: 180 },
  {
    key: 'status_change_at',
    label: '状态日期',
    minWidth: 180,
    format: 'datetime'
  },
  { key: 'compensation_status_display_name', label: '赔偿状态', minWidth: 190 },
  {
    key: 'compensation_status_display_name_cn',
    label: '赔偿状态（中文）',
    minWidth: 190
  },
  {
    key: 'compensation_status_change_at',
    label: '赔偿状态日期',
    minWidth: 190,
    format: 'datetime'
  },
  { key: 'return_reason_name', label: '退货原因', minWidth: 220, detailSpan: 2 },
  {
    key: 'return_reason_name_cn',
    label: '退货原因（中文）',
    minWidth: 220,
    detailSpan: 2
  },
  { key: 'buyer_comment', label: '买家评论', minWidth: 220, detailSpan: 2 },
  {
    key: 'buyer_comment_cn',
    label: '买家评论（中文）',
    minWidth: 220,
    detailSpan: 2
  },
  { key: 'quantity', label: '退货数量', width: 105 },
  { key: 'is_opened', label: '货件已打开', width: 115, format: 'boolean' },
  { key: 'target_place_name', label: '目的地', minWidth: 190 },
  { key: 'target_place_name_cn', label: '目的地（中文）', minWidth: 190 },
  { key: 'target_place_address', label: '存储地址', minWidth: 250, detailSpan: 2 },
  {
    key: 'target_place_address_cn',
    label: '存储地址（中文）',
    minWidth: 250,
    detailSpan: 2
  },
  {
    key: 'ready_to_pickup_at',
    label: '转到“到达取货点”',
    minWidth: 190,
    format: 'datetime'
  },
  { key: 'place_name', label: '位置', minWidth: 180 },
  { key: 'place_name_cn', label: '位置（中文）', minWidth: 180 },
  {
    key: 'picked_up_at',
    label: '向卖家退货日期',
    minWidth: 190,
    format: 'datetime'
  },
  { key: 'storage_days', label: '存储天数', width: 105 },
  {
    key: 'storage_expire_at',
    label: '免费存储的最后一天',
    minWidth: 210,
    format: 'datetime'
  },
  { key: 'logistic_barcode', label: '退货条形码', minWidth: 180 },
  { key: 'storage_fee_amount', label: '仓储费用', minWidth: 120 },
  { key: 'storage_fee_currency', label: '仓储费用币种', minWidth: 135 },
  { key: 'utilization_fee_amount', label: '销毁费用', minWidth: 120 },
  { key: 'utilization_fee_currency', label: '销毁费用币种', minWidth: 135 },
  { key: 'price_amount', label: '商品价格', minWidth: 120 },
  { key: 'price_currency', label: '商品价格币种', minWidth: 135 },
  { key: 'commission_percent', label: '佣金百分比', minWidth: 125 },
  { key: 'commission_amount', label: '佣金', minWidth: 110 },
  { key: 'commission_currency', label: '佣金币种', minWidth: 110 },
  {
    key: 'price_without_commission_amount',
    label: '不含佣金的价格',
    minWidth: 150
  },
  {
    key: 'price_without_commission_currency',
    label: '不含佣金价格币种',
    minWidth: 160
  }
]

const loading = ref(false)
const route = useRoute()
const showAdvancedFilters = ref(false)
const exporting = ref(false)
const returns = ref<OzonReturn[]>([])
const shops = ref<Shop[]>([])
const total = ref(0)
const dateRange = ref<string[]>([])
const selectedRows = ref<OzonReturn[]>([])
const tableRef = ref<TableInstance>()
const drawerVisible = ref(false)
const currentRow = ref<OzonReturn | null>(null)

const createFilters = (): ReturnFilterForm => ({ sort_order: 'desc' })
const filters = reactive<ReturnFilterForm>(createFilters())
const pagination = reactive({ page: 1, page_size: 20 })

const rowKey = (row: OzonReturn) => `${row.shop_id}:${row.return_id}:${row.nm_id}`
const getShopName = (shopId: number) => shops.value.find((shop) => shop.id === shopId)?.name || '-'

function activeFilters(): OzonReturnFilters {
  return {
    shop_id: filters.shop_id ?? undefined,
    date_from: dateRange.value[0] || undefined,
    date_to: dateRange.value[1] || undefined,
    return_id: filters.return_id ?? undefined,
    nm_id: filters.nm_id ?? undefined,
    posting_number: filters.posting_number || undefined,
    order_id: filters.order_id ?? undefined,
    order_number: filters.order_number || undefined,
    offer_id: filters.offer_id || undefined,
    brand_name: filters.brand_name || undefined,
    category_name: filters.category_name || undefined,
    product_name: filters.product_name || undefined,
    status: filters.status || undefined,
    return_type: filters.return_type || undefined,
    schema: filters.schema || undefined,
    keyword: filters.keyword || undefined,
    sort_order: filters.sort_order
  }
}

let fetchRequestId = 0

async function fetchReturns() {
  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const response = await ozonReturnApi.list({
      ...activeFilters(),
      page: pagination.page,
      page_size: pagination.page_size
    })
    if (requestId === fetchRequestId) {
      returns.value = response.items
      total.value = response.total
    }
  } finally {
    if (requestId === fetchRequestId) loading.value = false
  }
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

function handleSearch() {
  showAdvancedFilters.value = false
  pagination.page = 1
  clearSelection()
  fetchReturns()
}

function handleReset() {
  showAdvancedFilters.value = false
  Object.assign(filters, createFilters())
  dateRange.value = []
  pagination.page = 1
  clearSelection()
  fetchReturns()
}

function handleSizeChange() {
  pagination.page = 1
  fetchReturns()
}

function handleSelectionChange(rows: OzonReturn[]) {
  selectedRows.value = rows
}

function openDetail(row: OzonReturn) {
  currentRow.value = row
  drawerVisible.value = true
}

function displayValue(value: OzonReturn[keyof OzonReturn]) {
  return value === null || value === undefined || value === '' ? '-' : String(value)
}

function formatMoscowTime(value: OzonReturn[keyof OzonReturn]) {
  if (!value || typeof value !== 'string') return '-'
  return value.replace('T', ' ').replace(/(\+|-)\d{2}:\d{2}$/, '')
}

function formatColumnValue(value: OzonReturn[keyof OzonReturn], format?: ColumnFormat) {
  if (format === 'datetime') return formatMoscowTime(value)
  if (format === 'boolean') {
    if (value === null || value === undefined) return '-'
    return value ? '是' : '否'
  }
  if (format === 'schema' && typeof value === 'string') return value.toUpperCase()
  return displayValue(value)
}

async function exportReturns(scope: OzonReturnExportScope) {
  if (scope === 'selected' && !selectedRows.value.length) {
    ElMessage.warning('请先勾选需要导出的 Ozon 退货记录')
    return
  }
  exporting.value = true
  try {
    const selectedKeys: OzonReturnKey[] = selectedRows.value.map((row) => ({
      shop_id: row.shop_id,
      return_id: row.return_id,
      nm_id: row.nm_id
    }))
    const blob = await ozonReturnApi.export({
      scope,
      filters: activeFilters(),
      selected_keys: scope === 'selected' ? selectedKeys : []
    })
    downloadExcel(blob, 'Ozon退货')
    ElMessage.success(scope === 'selected' ? '已导出选中退货记录' : '已导出筛选结果')
  } finally {
    exporting.value = false
  }
}

function handleExportFiltered() {
  exportReturns('filtered')
}

function handleExportCommand(command: OzonReturnExportScope) {
  exportReturns(command)
}

function hydrateRouteFilters() {
  const query = route.query
  const numeric = (value: unknown) => value ? Number(value) : undefined
  filters.shop_id = numeric(query.shop_id)
  filters.nm_id = numeric(query.sku)
  filters.posting_number = typeof query.posting_number === 'string' ? query.posting_number : undefined
  filters.order_number = typeof query.order_number === 'string' ? query.order_number : undefined
  filters.offer_id = typeof query.offer_id === 'string' ? query.offer_id : undefined
  if (query.fulfillment_type === 'FBS' || query.fulfillment_type === 'FBO') {
    filters.schema = query.fulfillment_type === 'FBS' ? 'Fbs' : 'Fbo'
  }
  if (typeof query.date_from === 'string' && typeof query.date_to === 'string') {
    dateRange.value = [query.date_from, query.date_to]
  }
}

onMounted(() => { hydrateRouteFilters(); fetchReturns() })
</script>

<style scoped lang="scss">
.return-page {
  .search-card {
    margin-bottom: 16px;
  }

  .search-form {
    :deep(.el-form-item) {
      margin-bottom: 16px;
    }

    :deep(.el-date-editor),
    :deep(.el-select),
    :deep(.el-input-number) {
      width: 100%;
    }

    .actions :deep(.el-form-item__content) {
      flex-wrap: nowrap;
    }

  }

  .table-card {
    .table-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }

    .table-actions {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .title {
      color: #1f2329;
      font-weight: 600;
    }

    .meta {
      margin-left: 12px;
      color: #8a9099;
      font-size: 13px;
    }
  }

  .pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
    overflow-x: auto;
  }

  .long-text {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.7;
  }
}

@media (max-width: 768px) {
  .return-page {
    .search-form .actions {
      :deep(.el-form-item__content) {
        flex-wrap: wrap;
        gap: 8px;
      }

      :deep(.el-button + .el-button) {
        margin-left: 0;
      }
    }

    .table-card :deep(.el-card__body) {
      padding: 12px;
    }
  }
}
</style>
