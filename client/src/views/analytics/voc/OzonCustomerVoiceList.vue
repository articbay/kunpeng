<template>
  <div class="voice-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" label-width="88px">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="5">
            <el-form-item label="店铺">
              <PlatformShopSelect v-model="filters.shop_id" platform="ozon" @update:model-value="search" @shops-loaded="shops = $event" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="7">
            <el-form-item label="发布日期">
              <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
                range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="评分">
              <el-select v-model="filters.rating" clearable placeholder="全部">
                <el-option v-for="score in 5" :key="score" :label="`${score} 星`" :value="score" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="8">
            <el-form-item label="关键词">
              <el-input v-model.trim="filters.keyword" clearable placeholder="商品名、评价或状态"
                @keyup.enter="search" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="5">
            <el-form-item label="货号">
              <el-input v-model.trim="filters.offer_id" clearable @keyup.enter="search" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="5">
            <el-form-item label="SKU">
              <el-input-number v-model="filters.sku" :controls="false" :min="1" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="14">
            <el-form-item label-width="0" class="actions">
              <el-button type="primary" :icon="Search" @click="search">查询</el-button>
              <el-button :icon="RefreshLeft" @click="reset">重置</el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="header">
          <div><b>Ozon 客户声音</b><span>共 {{ total }} 条，已选 {{ selected.length }} 条</span></div>
          <el-dropdown split-button type="success" :loading="exporting"
            @click="exportRows('filtered')" @command="exportRows">
            导出
            <template #dropdown><el-dropdown-menu>
              <el-dropdown-item command="filtered">导出筛选结果</el-dropdown-item>
              <el-dropdown-item command="selected" :disabled="!selected.length">导出已选（{{ selected.length }}）</el-dropdown-item>
            </el-dropdown-menu></template>
          </el-dropdown>
        </div>
      </template>
      <el-table ref="tableRef" v-loading="loading" :data="items" :row-key="rowKey" border stripe
        height="calc(100vh - 330px)" @selection-change="selected = $event">
        <el-table-column type="selection" width="48" fixed="left" reserve-selection />
        <el-table-column prop="shop_id" label="店铺ID" width="100" />
        <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ getShopName(row.shop_id) }}</template>
        </el-table-column>
        <el-table-column v-for="column in columns" :key="column.key" :prop="column.key"
          :label="column.label" :width="column.width" :min-width="column.minWidth" show-overflow-tooltip>
          <template #default="{ row }">{{ format(row[column.key], column.datetime) }}</template>
        </el-table-column>
        <template #empty><el-empty description="暂无 Ozon 客户声音数据" /></template>
      </el-table>
      <div class="pagination">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]" :total="total"
          layout="total, sizes, prev, pager, next, jumper" @change="fetchItems" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type TableInstance } from 'element-plus'
import { RefreshLeft, Search } from '@element-plus/icons-vue'
import PlatformShopSelect from '@/components/PlatformShopSelect.vue'
import type { Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'
import {
  ozonCustomerVoiceApi,
  type OzonCustomerVoice,
  type OzonCustomerVoiceExportScope,
  type OzonCustomerVoiceFilters
} from '@/api/modules/ozonCustomerVoice'

type Column = { key: keyof OzonCustomerVoice; label: string; width?: number; minWidth?: number; datetime?: boolean }
const columns: Column[] = [
  { key: 'month', label: '月份', width: 100 },
  { key: 'offer_id', label: '货号', minWidth: 150 },
  { key: 'sku', label: 'SKU', minWidth: 130 },
  { key: 'product_name', label: '商品名称', minWidth: 240 },
  { key: 'product_name_cn', label: '商品名称（中文）', minWidth: 240 },
  { key: 'posting_number', label: '订单号', minWidth: 160 },
  { key: 'order_status', label: '收货状态', minWidth: 150 },
  { key: 'order_status_cn', label: '收货状态（中文）', minWidth: 170 },
  { key: 'review_text', label: '检讨文本', minWidth: 260 },
  { key: 'review_text_cn', label: '检讨文本（中文）', minWidth: 260 },
  { key: 'published_at', label: '发布日期', minWidth: 180, datetime: true },
  { key: 'review_status', label: '评价状态', minWidth: 150 },
  { key: 'review_status_cn', label: '评价状态（中文）', minWidth: 170 },
  { key: 'rating', label: '评分', width: 90 },
  { key: 'photos_amount', label: '照片数量', width: 105 },
  { key: 'videos_amount', label: '视频数量', width: 105 },
  { key: 'comments_amount', label: '对检讨的回应数目', minWidth: 165 }
]

const loading = ref(false)
const exporting = ref(false)
const items = ref<OzonCustomerVoice[]>([])
const selected = ref<OzonCustomerVoice[]>([])
const shops = ref<Shop[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref<string[]>([])
const tableRef = ref<TableInstance>()
const filters = reactive<OzonCustomerVoiceFilters>({ sort_order: 'desc' })
let fetchRequestId = 0
const rowKey = (row: OzonCustomerVoice) => `${row.shop_id}:${row.review_id}`
const getShopName = (shopId: number) => shops.value.find((shop) => shop.id === shopId)?.name || '-'

function activeFilters(): OzonCustomerVoiceFilters {
  return {
    ...filters,
    date_from: dateRange.value[0] || undefined,
    date_to: dateRange.value[1] || undefined
  }
}

async function fetchItems() {
  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const response = await ozonCustomerVoiceApi.list({ ...activeFilters(), page: page.value, page_size: pageSize.value })
    if (requestId === fetchRequestId) {
      items.value = response.items
      total.value = response.total
    }
  } finally { if (requestId === fetchRequestId) loading.value = false }
}

function search() { page.value = 1; tableRef.value?.clearSelection(); fetchItems() }
function reset() {
  Object.keys(filters).forEach((key) => delete filters[key as keyof OzonCustomerVoiceFilters])
  filters.sort_order = 'desc'; dateRange.value = []; search()
}
function format(value: OzonCustomerVoice[keyof OzonCustomerVoice], datetime?: boolean) {
  if (value === null || value === undefined || value === '') return '-'
  return datetime && typeof value === 'string' ? value.replace('T', ' ').replace(/([+-]\d{2}:\d{2})$/, '') : String(value)
}
async function exportRows(scope: OzonCustomerVoiceExportScope) {
  if (scope === 'selected' && !selected.value.length) { ElMessage.warning('请先选择评价'); return }
  exporting.value = true
  try {
    const blob = await ozonCustomerVoiceApi.export({
      scope,
      filters: activeFilters(),
      selected_keys: scope === 'selected' ? selected.value.map(({ shop_id, review_id }) => ({ shop_id, review_id })) : []
    })
    downloadExcel(blob, 'Ozon客户声音')
    ElMessage.success('导出成功')
  } finally { exporting.value = false }
}

onMounted(fetchItems)
</script>

<style scoped lang="scss">
.search-card { margin-bottom: 16px; }
:deep(.el-date-editor), :deep(.el-select), :deep(.el-input-number) { width: 100%; }
.actions :deep(.el-form-item__content) { display: flex; gap: 8px; flex-wrap: wrap; }
.actions :deep(.el-button + .el-button) { margin-left: 0; }
.header { display: flex; gap: 16px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.header span { color: #8a9099; font-size: 13px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; overflow-x: auto; }
</style>
