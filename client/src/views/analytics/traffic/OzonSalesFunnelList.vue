<template>
  <div class="funnel-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" label-width="88px">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="5">
            <el-form-item label="店铺">
              <PlatformShopSelect v-model="filters.shop_id" platform="ozon" @update:model-value="search" @shops-loaded="shops = $event" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="7">
            <el-form-item label="统计日期">
              <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
                range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="5">
            <el-form-item label="Ozon SKU">
              <el-input-number v-model="filters.sku" :controls="false" :min="1" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="7">
            <el-form-item label="卖家货号">
              <el-input v-model.trim="filters.offer_id" clearable @keyup.enter="search" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="10">
            <el-form-item label="关键词">
              <el-input v-model.trim="filters.keyword" clearable
                placeholder="商品名称或商品品类" @keyup.enter="search" />
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

    <el-alert class="metric-note" type="info" :closable="false" show-icon
      title="Ozon原生指标直接展示；“加购至下单转化率”是 ordered_units ÷ hits_tocart 的项目计算指标。" />

    <el-card shadow="never">
      <template #header>
        <div class="header">
          <div><b>Ozon 销售漏斗</b><span>共 {{ total }} 条，已选 {{ selected.length }} 条</span></div>
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
        height="calc(100vh - 385px)" @selection-change="selected = $event">
        <el-table-column type="selection" width="48" fixed="left" reserve-selection />
        <el-table-column prop="shop_id" label="店铺ID" width="95" />
        <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ getShopName(row.shop_id) }}</template>
        </el-table-column>
        <el-table-column v-for="column in columns" :key="column.key" :prop="column.key"
          :label="column.label" :width="column.width" :min-width="column.minWidth"
          show-overflow-tooltip>
          <template #default="{ row }">{{ format(row[column.key], column.digits) }}</template>
        </el-table-column>
        <template #empty><el-empty description="暂无 Ozon 销售漏斗数据" /></template>
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
import { useRoute } from 'vue-router'
import { ElMessage, type TableInstance } from 'element-plus'
import { RefreshLeft, Search } from '@element-plus/icons-vue'
import PlatformShopSelect from '@/components/PlatformShopSelect.vue'
import type { Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'
import {
  ozonSalesFunnelApi,
  type OzonSalesFunnel,
  type OzonSalesFunnelExportScope,
  type OzonSalesFunnelFilters
} from '@/api/modules/ozonSalesFunnel'

type Column = {
  key: keyof OzonSalesFunnel
  label: string
  width?: number
  minWidth?: number
  digits?: number
}

const columns: Column[] = [
  { key: 'offer_id', label: '卖家商品编号', minWidth: 155 },
  { key: 'sku', label: 'Ozon SKU', minWidth: 135 },
  { key: 'product_name', label: '商品名称', minWidth: 240 },
  { key: 'product_name_cn', label: '商品名称（中文）', minWidth: 240 },
  { key: 'category_name', label: '商品品类', minWidth: 170 },
  { key: 'category_name_cn', label: '商品品类（中文）', minWidth: 180 },
  { key: 'stat_date', label: '统计日期', width: 120 },
  { key: 'hits_view_search', label: '搜索和类目展示次数', minWidth: 160 },
  { key: 'hits_view_pdp', label: '商品详情页浏览次数', minWidth: 165 },
  { key: 'hits_view', label: '总展示/浏览次数', minWidth: 145 },
  { key: 'session_view_search', label: '搜索和类目访问用户数', minWidth: 175 },
  { key: 'session_view_pdp', label: '商品详情页访问用户数', minWidth: 180 },
  { key: 'session_view', label: '总访问用户数', minWidth: 130 },
  { key: 'hits_tocart_search', label: '搜索和类目加购次数', minWidth: 165 },
  { key: 'hits_tocart_pdp', label: '商品详情页加购次数', minWidth: 170 },
  { key: 'hits_tocart', label: '总加购次数', minWidth: 120 },
  { key: 'conv_tocart_search', label: '搜索和类目加购转化率（%）', minWidth: 210, digits: 2 },
  { key: 'conv_tocart_pdp', label: '商品详情页加购转化率（%）', minWidth: 220, digits: 2 },
  { key: 'conv_tocart', label: '总加购转化率（%）', minWidth: 165, digits: 2 },
  { key: 'ordered_units', label: '下单商品件数', minWidth: 125 },
  { key: 'revenue', label: '下单金额（₽）', minWidth: 125, digits: 2 },
  { key: 'delivered_units', label: '送达商品件数', minWidth: 125 },
  { key: 'cancellations', label: '取消商品件数', minWidth: 125 },
  { key: 'returns', label: '退货商品件数', minWidth: 125 },
  { key: 'position_category', label: '搜索和类目平均位置', minWidth: 165, digits: 2 },
  { key: 'cart_to_order_rate', label: '加购至下单转化率（项目计算，%）', minWidth: 245, digits: 2 }
]

const loading = ref(false)
const route = useRoute()
const exporting = ref(false)
const items = ref<OzonSalesFunnel[]>([])
const selected = ref<OzonSalesFunnel[]>([])
const shops = ref<Shop[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref<string[]>([])
const tableRef = ref<TableInstance>()
const filters = reactive<OzonSalesFunnelFilters>({ sort_order: 'desc' })
let fetchRequestId = 0
const rowKey = (row: OzonSalesFunnel) => `${row.shop_id}:${row.stat_date}:${row.sku}`
const getShopName = (shopId: number) => shops.value.find((shop) => shop.id === shopId)?.name || '-'

function activeFilters(): OzonSalesFunnelFilters {
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
    const response = await ozonSalesFunnelApi.list({
      ...activeFilters(), page: page.value, page_size: pageSize.value
    })
    if (requestId === fetchRequestId) {
      items.value = response.items
      total.value = response.total
    }
  } finally { if (requestId === fetchRequestId) loading.value = false }
}

function search() { page.value = 1; tableRef.value?.clearSelection(); fetchItems() }
function reset() {
  Object.keys(filters).forEach((key) => delete filters[key as keyof OzonSalesFunnelFilters])
  filters.sort_order = 'desc'; dateRange.value = []; search()
}
function format(value: OzonSalesFunnel[keyof OzonSalesFunnel], digits?: number) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (digits !== undefined && !Number.isNaN(Number(value))) return Number(value).toFixed(digits)
  return String(value)
}
async function exportRows(scope: OzonSalesFunnelExportScope) {
  if (scope === 'selected' && !selected.value.length) {
    ElMessage.warning('请先选择销售漏斗明细'); return
  }
  exporting.value = true
  try {
    const blob = await ozonSalesFunnelApi.export({
      scope,
      filters: activeFilters(),
      selected_keys: scope === 'selected'
        ? selected.value.map(({ shop_id, stat_date, sku }) => ({ shop_id, stat_date, sku }))
        : []
    })
    downloadExcel(blob, 'Ozon销售漏斗')
    ElMessage.success('导出成功')
  } finally { exporting.value = false }
}

function hydrateRouteFilters() {
  const query = route.query
  filters.shop_id = query.shop_id ? Number(query.shop_id) : undefined
  filters.sku = query.sku ? Number(query.sku) : undefined
  filters.offer_id = typeof query.offer_id === 'string' ? query.offer_id : undefined
  if (typeof query.date_from === 'string' && typeof query.date_to === 'string') {
    dateRange.value = [query.date_from, query.date_to]
  }
}

onMounted(() => { hydrateRouteFilters(); fetchItems() })
</script>

<style scoped lang="scss">
.search-card, .metric-note { margin-bottom: 16px; }
:deep(.el-date-editor), :deep(.el-input-number) { width: 100%; }
.actions :deep(.el-form-item__content) { display: flex; gap: 8px; flex-wrap: wrap; }
.actions :deep(.el-button + .el-button) { margin-left: 0; }
.header { display: flex; gap: 16px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.header span { color: #8a9099; font-size: 13px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; overflow-x: auto; }
</style>
