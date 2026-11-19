<template>
  <div class="statistics-order-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" label-width="90px" class="search-form">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="店铺">
              <PlatformShopSelect
                v-model="filters.shop_id"
                platform="wildberries"
                @update:model-value="handleSearch"
                @shops-loaded="handleShopsLoaded"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="8">
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
            <el-form-item label="WB商品ID">
              <el-input-number
                v-model="filters.nm_id"
                :min="1"
                :controls="false"
                placeholder="请输入"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="是否取消">
              <el-select v-model="filters.is_cancel" placeholder="全部" clearable>
                <el-option label="是" :value="true" />
                <el-option label="否" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12" style="order: 1">
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
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="8">
            <el-form-item label="系统订单号">
              <el-input
                v-model.trim="filters.srid"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="卖家货号">
              <el-input
                v-model.trim="filters.supplier_article"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="仓库名称">
              <el-input
                v-model.trim="filters.warehouse_name"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="国家">
              <el-input
                v-model.trim="filters.country_name"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="地区">
              <el-input
                v-model.trim="filters.region_name"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="商品分类">
              <el-input
                v-model.trim="filters.category"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="商品品类">
              <el-input
                v-model.trim="filters.subject_name"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="联邦管区">
              <el-input
                v-model.trim="filters.oblast_okrug_name"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :lg="12">
            <el-form-item label="关键词">
              <el-input
                v-model.trim="filters.keyword"
                placeholder="订单号、仓库、地区、货号、条码、商品、贴纸或订单组号"
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
            <span class="title">Wildberries 统计订单</span>
            <span class="meta">共 {{ total }} 条，已选 {{ selectedRows.length }} 条</span>
          </div>
          <div class="table-actions">
            <el-radio-group v-model="filters.sort_order" size="small" @change="handleSearch">
              <el-radio-button value="desc">时间倒序</el-radio-button>
              <el-radio-button value="asc">时间正序</el-radio-button>
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
        :data="orders"
        :row-key="rowKey"
        border
        stripe
        height="calc(100vh - 300px)"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" fixed="left" reserve-selection />
        <el-table-column prop="shop_id" label="店铺ID" width="92" />
        <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ getShopName(row.shop_id) }}</template>
        </el-table-column>
        <el-table-column prop="srid" label="系统订单号" min-width="220" show-overflow-tooltip />
        <el-table-column label="下单时间（莫斯科）" min-width="190">
          <template #default="{ row }">{{ formatLocalTime(row.order_date) }}</template>
        </el-table-column>
        <el-table-column label="最后修改时间（莫斯科）" min-width="210">
          <template #default="{ row }">{{ formatLocalTime(row.last_change_date) }}</template>
        </el-table-column>
        <el-table-column prop="warehouse_name" label="仓库名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="warehouse_name_cn" label="仓库名称（中文）" min-width="180" show-overflow-tooltip />
        <el-table-column prop="country_name" label="国家" min-width="140" show-overflow-tooltip />
        <el-table-column prop="country_name_cn" label="国家（中文）" min-width="150" show-overflow-tooltip />
        <el-table-column prop="oblast_okrug_name" label="联邦管区" min-width="180" show-overflow-tooltip />
        <el-table-column prop="oblast_okrug_name_cn" label="联邦管区（中文）" min-width="195" show-overflow-tooltip />
        <el-table-column prop="region_name" label="地区" min-width="180" show-overflow-tooltip />
        <el-table-column prop="region_name_cn" label="地区（中文）" min-width="190" show-overflow-tooltip />
        <el-table-column prop="supplier_article" label="卖家货号" min-width="170" show-overflow-tooltip />
        <el-table-column prop="nm_id" label="WB商品ID" min-width="130" />
        <el-table-column prop="barcode" label="条码" min-width="160" show-overflow-tooltip />
        <el-table-column prop="category" label="商品分类" min-width="140" show-overflow-tooltip />
        <el-table-column prop="category_cn" label="商品分类（中文）" min-width="165" show-overflow-tooltip />
        <el-table-column prop="subject_name" label="商品品类" min-width="140" show-overflow-tooltip />
        <el-table-column prop="subject_name_cn" label="商品品类（中文）" min-width="165" show-overflow-tooltip />
        <el-table-column prop="tech_size" label="尺码" min-width="100" />
        <el-table-column prop="tech_size_cn" label="尺码（中文）" min-width="125" show-overflow-tooltip />
        <el-table-column prop="total_price" label="原价" min-width="105" />
        <el-table-column prop="discount_percent" label="折扣百分比" min-width="115" />
        <el-table-column prop="price_with_disc" label="折后价格" min-width="110" />
        <el-table-column prop="finished_price" label="最终价格" min-width="110" />
        <el-table-column label="是否取消" width="100">
          <template #default="{ row }">{{ formatBoolean(row.is_cancel) }}</template>
        </el-table-column>
        <el-table-column label="取消时间（莫斯科）" min-width="190">
          <template #default="{ row }">{{ formatLocalTime(row.cancel_date) }}</template>
        </el-table-column>
        <el-table-column prop="sticker_id" label="贴纸ID" min-width="170" show-overflow-tooltip />
        <el-table-column prop="g_number" label="订单组号" min-width="190" show-overflow-tooltip />
        <el-table-column label="操作" width="84" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无统计订单数据" />
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
          @current-change="fetchOrders"
        />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" title="统计订单详情" size="820px">
      <el-descriptions v-if="currentRow" :column="2" border>
        <el-descriptions-item label="店铺ID">{{ displayValue(currentRow.shop_id) }}</el-descriptions-item>
        <el-descriptions-item label="系统订单号">{{ displayValue(currentRow.srid) }}</el-descriptions-item>
        <el-descriptions-item label="下单时间">{{ formatLocalTime(currentRow.order_date) }}</el-descriptions-item>
        <el-descriptions-item label="最后修改时间">{{ formatLocalTime(currentRow.last_change_date) }}</el-descriptions-item>
        <el-descriptions-item label="仓库名称">{{ displayValue(currentRow.warehouse_name) }}</el-descriptions-item>
        <el-descriptions-item label="仓库名称（中文）">{{ displayValue(currentRow.warehouse_name_cn) }}</el-descriptions-item>
        <el-descriptions-item label="国家">{{ displayValue(currentRow.country_name) }}</el-descriptions-item>
        <el-descriptions-item label="国家（中文）">{{ displayValue(currentRow.country_name_cn) }}</el-descriptions-item>
        <el-descriptions-item label="联邦管区">{{ displayValue(currentRow.oblast_okrug_name) }}</el-descriptions-item>
        <el-descriptions-item label="联邦管区（中文）">{{ displayValue(currentRow.oblast_okrug_name_cn) }}</el-descriptions-item>
        <el-descriptions-item label="地区">{{ displayValue(currentRow.region_name) }}</el-descriptions-item>
        <el-descriptions-item label="地区（中文）">{{ displayValue(currentRow.region_name_cn) }}</el-descriptions-item>
        <el-descriptions-item label="卖家货号">{{ displayValue(currentRow.supplier_article) }}</el-descriptions-item>
        <el-descriptions-item label="WB商品ID">{{ displayValue(currentRow.nm_id) }}</el-descriptions-item>
        <el-descriptions-item label="条码">{{ displayValue(currentRow.barcode) }}</el-descriptions-item>
        <el-descriptions-item label="商品分类">{{ displayValue(currentRow.category) }}</el-descriptions-item>
        <el-descriptions-item label="商品分类（中文）">{{ displayValue(currentRow.category_cn) }}</el-descriptions-item>
        <el-descriptions-item label="商品品类">{{ displayValue(currentRow.subject_name) }}</el-descriptions-item>
        <el-descriptions-item label="商品品类（中文）">{{ displayValue(currentRow.subject_name_cn) }}</el-descriptions-item>
        <el-descriptions-item label="尺码">{{ displayValue(currentRow.tech_size) }}</el-descriptions-item>
        <el-descriptions-item label="尺码（中文）">{{ displayValue(currentRow.tech_size_cn) }}</el-descriptions-item>
        <el-descriptions-item label="原价">{{ displayValue(currentRow.total_price) }}</el-descriptions-item>
        <el-descriptions-item label="折扣百分比">{{ displayValue(currentRow.discount_percent) }}</el-descriptions-item>
        <el-descriptions-item label="折后价格">{{ displayValue(currentRow.price_with_disc) }}</el-descriptions-item>
        <el-descriptions-item label="最终价格">{{ displayValue(currentRow.finished_price) }}</el-descriptions-item>
        <el-descriptions-item label="是否取消">{{ formatBoolean(currentRow.is_cancel) }}</el-descriptions-item>
        <el-descriptions-item label="取消时间">{{ formatLocalTime(currentRow.cancel_date) }}</el-descriptions-item>
        <el-descriptions-item label="贴纸ID">{{ displayValue(currentRow.sticker_id) }}</el-descriptions-item>
        <el-descriptions-item label="订单组号">{{ displayValue(currentRow.g_number) }}</el-descriptions-item>
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
  wbOrderStatisticsApi,
  type ExportScope,
  type WBOrderStatistics,
  type WBOrderStatisticsFilters,
  type WBOrderStatisticsKey
} from '@/api/modules/wbOrderStatistics'

type StatisticsFilterForm = WBOrderStatisticsFilters & {
  sort_order: 'asc' | 'desc'
}

const loading = ref(false)
const showAdvancedFilters = ref(false)
const shopNames = ref<Record<number, string>>({})
const exporting = ref(false)
const orders = ref<WBOrderStatistics[]>([])
const total = ref(0)
const dateRange = ref<string[]>([])
const selectedRows = ref<WBOrderStatistics[]>([])
const tableRef = ref<TableInstance>()
const drawerVisible = ref(false)
const currentRow = ref<WBOrderStatistics | null>(null)
const route = useRoute()

const createFilters = (): StatisticsFilterForm => ({ sort_order: 'desc' })
const filters = reactive<StatisticsFilterForm>(createFilters())
const pagination = reactive({ page: 1, page_size: 20 })
const rowKey = (row: WBOrderStatistics) => `${row.shop_id}:${row.srid}`

function queryText(key: string): string | undefined {
  const value = route.query[key]
  return typeof value === 'string' && value ? value : undefined
}

function hydrateRouteFilters() {
  const shopId = Number(queryText('shop_id'))
  const nmId = Number(queryText('nm_id'))
  if (shopId > 0) filters.shop_id = shopId
  if (nmId > 0) filters.nm_id = nmId
  filters.supplier_article = queryText('vendor_code')
  const dateFrom = queryText('date_from')
  const dateTo = queryText('date_to')
  if (dateFrom && dateTo) dateRange.value = [dateFrom, dateTo]
}

function handleShopsLoaded(shops: Shop[]) {
  shopNames.value = Object.fromEntries(shops.map((shop) => [shop.id, shop.name]))
}

function getShopName(shopId: number) {
  return shopNames.value[shopId] ?? '-'
}

function activeFilters(): WBOrderStatisticsFilters {
  return {
    shop_id: filters.shop_id ?? undefined,
    date_from: dateRange.value[0] || undefined,
    date_to: dateRange.value[1] || undefined,
    srid: filters.srid || undefined,
    warehouse_name: filters.warehouse_name || undefined,
    country_name: filters.country_name || undefined,
    oblast_okrug_name: filters.oblast_okrug_name || undefined,
    region_name: filters.region_name || undefined,
    supplier_article: filters.supplier_article || undefined,
    nm_id: filters.nm_id ?? undefined,
    category: filters.category || undefined,
    subject_name: filters.subject_name || undefined,
    is_cancel: filters.is_cancel ?? undefined,
    keyword: filters.keyword || undefined,
    sort_order: filters.sort_order
  }
}

let fetchRequestId = 0

async function fetchOrders() {
  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const response = await wbOrderStatisticsApi.list({
      ...activeFilters(),
      page: pagination.page,
      page_size: pagination.page_size
    })
    if (requestId === fetchRequestId) {
      orders.value = response.items
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
  fetchOrders()
}

function handleReset() {
  showAdvancedFilters.value = false
  Object.assign(filters, createFilters())
  dateRange.value = []
  pagination.page = 1
  clearSelection()
  fetchOrders()
}

function handleSizeChange() {
  pagination.page = 1
  fetchOrders()
}

function handleSelectionChange(rows: WBOrderStatistics[]) {
  selectedRows.value = rows
}

function openDetail(row: WBOrderStatistics) {
  currentRow.value = row
  drawerVisible.value = true
}

function displayValue(value: string | number | null | undefined) {
  return value === null || value === undefined || value === '' ? '-' : value
}

function formatBoolean(value: boolean | null) {
  if (value === null) return '-'
  return value ? '是' : '否'
}

function formatLocalTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').replace(/(\+|-)\d{2}:\d{2}$/, '')
}

async function exportOrders(scope: ExportScope) {
  if (scope === 'selected' && !selectedRows.value.length) {
    ElMessage.warning('请先勾选需要导出的统计订单')
    return
  }
  exporting.value = true
  try {
    const selectedKeys: WBOrderStatisticsKey[] = selectedRows.value.map((row) => ({
      shop_id: row.shop_id,
      srid: row.srid
    }))
    const blob = await wbOrderStatisticsApi.export({
      scope,
      filters: activeFilters(),
      selected_keys: scope === 'selected' ? selectedKeys : []
    })
    downloadExcel(blob, 'WB统计订单')
    ElMessage.success(scope === 'selected' ? '已导出选中统计订单' : '已导出筛选结果')
  } finally {
    exporting.value = false
  }
}

function handleExportFiltered() { exportOrders('filtered') }
function handleExportCommand(command: ExportScope) { exportOrders(command) }

onMounted(() => { hydrateRouteFilters(); fetchOrders() })
</script>

<style scoped lang="scss">
.statistics-order-page {
  .search-card { margin-bottom: 16px; }
  .search-form {
    :deep(.el-form-item) { margin-bottom: 16px; }
    :deep(.el-date-editor), :deep(.el-select), :deep(.el-input-number) { width: 100%; }
    .actions :deep(.el-form-item__content) { flex-wrap: nowrap; }
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
    .title { color: #1f2329; font-weight: 600; }
    .meta { margin-left: 12px; color: #8a9099; font-size: 13px; }
  }
  .pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
    overflow-x: auto;
  }
}

@media (max-width: 768px) {
  .statistics-order-page {
    .search-form .actions {
      :deep(.el-form-item__content) { flex-wrap: wrap; gap: 8px; }
      :deep(.el-button + .el-button) { margin-left: 0; }
    }
    .table-card :deep(.el-card__body) { padding: 12px; }
  }
}
</style>
