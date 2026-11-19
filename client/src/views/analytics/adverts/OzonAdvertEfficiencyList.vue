<template>
  <div class="advert-page">
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
            <el-form-item label="SKU">
              <el-input-number v-model="filters.sku" :controls="false" :min="1" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="7">
            <el-form-item label="活动ID">
              <el-input v-model.trim="filters.campaign_id" clearable @keyup.enter="search" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="10">
            <el-form-item label="关键词">
              <el-input v-model.trim="filters.keyword" clearable
                placeholder="商品名、品类或广告活动名称" @keyup.enter="search" />
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
          <div><b>Ozon 广告效率</b><span>共 {{ total }} 条，已选 {{ selected.length }} 条</span></div>
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
          :label="column.label" :width="column.width" :min-width="column.minWidth"
          show-overflow-tooltip>
          <template #default="{ row }">{{ format(row[column.key], column.digits) }}</template>
        </el-table-column>
        <template #empty><el-empty description="暂无 Ozon 广告效率数据" /></template>
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
  ozonAdvertEfficiencyApi,
  type OzonAdvertEfficiency,
  type OzonAdvertEfficiencyExportScope,
  type OzonAdvertEfficiencyFilters
} from '@/api/modules/ozonAdvertEfficiency'

type Column = {
  key: keyof OzonAdvertEfficiency
  label: string
  width?: number
  minWidth?: number
  digits?: number
}
const columns: Column[] = [
  { key: 'stat_date', label: '统计日期', width: 120 },
  { key: 'sku', label: 'SKU', minWidth: 135 },
  { key: 'product_name', label: '商品名称', minWidth: 240 },
  { key: 'product_name_cn', label: '商品名称（中文）', minWidth: 240 },
  { key: 'category_name', label: '品类名称', minWidth: 170 },
  { key: 'category_name_cn', label: '品类名称（中文）', minWidth: 180 },
  { key: 'payment_type', label: '工具', minWidth: 130 },
  { key: 'placement', label: '投放位置', minWidth: 150 },
  { key: 'campaign_id', label: '广告活动 ID', minWidth: 145 },
  { key: 'campaign_name', label: '广告活动名称', minWidth: 220 },
  { key: 'money_spent', label: '费用，₽', width: 120, digits: 2 },
  { key: 'drr', label: '广告费用份额, %', minWidth: 155, digits: 2 },
  { key: 'orders_money', label: '销售额，₽', width: 125, digits: 2 },
  { key: 'orders', label: '订单，个', width: 105 },
  { key: 'ctr', label: 'CTR, %', width: 100, digits: 2 },
  { key: 'views', label: '展现量', width: 105 },
  { key: 'clicks', label: '点击次数', width: 105 },
  { key: 'to_cart', label: '添加到购物车', minWidth: 130 },
  { key: 'to_cart_conversion_rate', label: '添加到购物车的转化率， %', minWidth: 210, digits: 2 },
  { key: 'cost_per_order', label: '单笔费用，₽', minWidth: 125, digits: 2 },
  { key: 'cost_per_click', label: '每次点击成本，₽', minWidth: 145, digits: 2 }
]

const loading = ref(false)
const route = useRoute()
const exporting = ref(false)
const items = ref<OzonAdvertEfficiency[]>([])
const selected = ref<OzonAdvertEfficiency[]>([])
const shops = ref<Shop[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref<string[]>([])
const tableRef = ref<TableInstance>()
const filters = reactive<OzonAdvertEfficiencyFilters>({ sort_order: 'desc' })
let fetchRequestId = 0
const rowKey = (row: OzonAdvertEfficiency) =>
  `${row.shop_id}:${row.stat_date}:${row.campaign_id}:${row.sku}`
const getShopName = (shopId: number) => shops.value.find((shop) => shop.id === shopId)?.name || '-'

function activeFilters(): OzonAdvertEfficiencyFilters {
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
    const response = await ozonAdvertEfficiencyApi.list({
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
  Object.keys(filters).forEach((key) => delete filters[key as keyof OzonAdvertEfficiencyFilters])
  filters.sort_order = 'desc'; dateRange.value = []; search()
}
function format(value: OzonAdvertEfficiency[keyof OzonAdvertEfficiency], digits?: number) {
  if (value === null || value === undefined || value === '') return '-'
  if (digits !== undefined && !Number.isNaN(Number(value))) return Number(value).toFixed(digits)
  return String(value)
}
async function exportRows(scope: OzonAdvertEfficiencyExportScope) {
  if (scope === 'selected' && !selected.value.length) {
    ElMessage.warning('请先选择广告明细'); return
  }
  exporting.value = true
  try {
    const blob = await ozonAdvertEfficiencyApi.export({
      scope,
      filters: activeFilters(),
      selected_keys: scope === 'selected'
        ? selected.value.map(({ shop_id, stat_date, sku, campaign_id }) =>
          ({ shop_id, stat_date, sku, campaign_id }))
        : []
    })
    downloadExcel(blob, 'Ozon广告效率')
    ElMessage.success('导出成功')
  } finally { exporting.value = false }
}

function hydrateRouteFilters() {
  const query = route.query
  filters.shop_id = query.shop_id ? Number(query.shop_id) : undefined
  filters.sku = query.sku ? Number(query.sku) : undefined
  if (typeof query.date_from === 'string' && typeof query.date_to === 'string') {
    dateRange.value = [query.date_from, query.date_to]
  }
}

onMounted(() => { hydrateRouteFilters(); fetchItems() })
</script>

<style scoped lang="scss">
.search-card { margin-bottom: 16px; }
:deep(.el-date-editor), :deep(.el-input-number) { width: 100%; }
.actions :deep(.el-form-item__content) { display: flex; gap: 8px; flex-wrap: wrap; }
.actions :deep(.el-button + .el-button) { margin-left: 0; }
.header { display: flex; gap: 16px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.header span { color: #8a9099; font-size: 13px; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; overflow-x: auto; }
</style>
