<template>
  <div class="order-page">
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
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="供货 ID">
              <el-input
                v-model.trim="filters.supply_id"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="贴纸 ID">
              <el-input
                v-model.trim="filters.sticker_id"
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
            <el-form-item label="仓库 ID">
              <el-input-number
                v-model="filters.warehouse_id"
                :min="1"
                :controls="false"
                placeholder="请输入"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="WB状态">
              <el-input
                v-model.trim="filters.wb_status"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="是否B2B">
              <el-select v-model="filters.is_b2b" placeholder="全部" clearable>
                <el-option label="是" :value="true" />
                <el-option label="否" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="配送类型">
              <el-input
                v-model.trim="filters.delivery_type"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="卖家状态">
              <el-input
                v-model.trim="filters.supplier_status"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="是否可取消">
              <el-select v-model="filters.is_cancellable" placeholder="全部" clearable>
                <el-option label="是" :value="true" />
                <el-option label="否" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="4">
            <el-form-item label="是否零订单">
              <el-select v-model="filters.is_zero_order" placeholder="全部" clearable>
                <el-option label="是" :value="true" />
                <el-option label="否" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :lg="8">
            <el-form-item label="关键词">
              <el-input
                v-model.trim="filters.keyword"
                placeholder="供货、贴纸、商品、尺寸、颜色、条码、货号、仓库或地址"
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
            <span class="title">Wildberries 履约订单</span>
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
        <el-table-column prop="order_id" label="订单ID（工作编号）" min-width="170" />
        <el-table-column prop="supply_id" label="供货ID" min-width="170" show-overflow-tooltip />
        <el-table-column prop="sticker_id" label="贴纸ID" min-width="170" show-overflow-tooltip />
        <el-table-column label="订单创建时间（莫斯科）" min-width="210">
          <template #default="{ row }">{{ formatMoscowTime(row.order_dt) }}</template>
        </el-table-column>
        <el-table-column prop="title" label="商品名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="title_cn" label="商品名称（中文）" min-width="220" show-overflow-tooltip />
        <el-table-column prop="tech_size" label="尺寸" min-width="100" show-overflow-tooltip />
        <el-table-column prop="tech_size_cn" label="尺寸（中文）" min-width="120" show-overflow-tooltip />
        <el-table-column prop="color" label="颜色" min-width="110" show-overflow-tooltip />
        <el-table-column prop="color_cn" label="颜色（中文）" min-width="130" show-overflow-tooltip />
        <el-table-column prop="barcode_ori" label="原生条形码" min-width="160" show-overflow-tooltip />
        <el-table-column prop="barcode_hand" label="手调条形码" min-width="160" show-overflow-tooltip />
        <el-table-column prop="retail_price" label="零售价" min-width="110" />
        <el-table-column prop="currency" label="币种" min-width="90" />
        <el-table-column prop="nm_id" label="WB商品ID" min-width="130" />
        <el-table-column
          prop="supplier_article"
          label="卖家货号"
          min-width="170"
          show-overflow-tooltip
        />
        <el-table-column prop="warehouse_id" label="卖家仓库ID" min-width="130" />
        <el-table-column
          prop="warehouse_name"
          label="卖家仓库"
          min-width="160"
          show-overflow-tooltip
        />
        <el-table-column
          prop="warehouse_name_cn"
          label="卖家仓库（中文）"
          min-width="180"
          show-overflow-tooltip
        />
        <el-table-column prop="wb_status" label="WB状态" min-width="120" show-overflow-tooltip />
        <el-table-column prop="wb_status_cn" label="WB状态（中文）" min-width="145" show-overflow-tooltip />
        <el-table-column prop="address" label="地址" min-width="220" show-overflow-tooltip />
        <el-table-column prop="address_cn" label="地址（中文）" min-width="220" show-overflow-tooltip />
        <el-table-column label="是否B2B" width="100">
          <template #default="{ row }">{{ formatBoolean(row.is_b2b) }}</template>
        </el-table-column>
        <el-table-column prop="delivery_type" label="配送类型" min-width="110" />
        <el-table-column
          prop="supplier_status"
          label="卖家处理状态"
          min-width="130"
          show-overflow-tooltip
        />
        <el-table-column
          prop="supplier_status_cn"
          label="卖家处理状态（中文）"
          min-width="175"
          show-overflow-tooltip
        />
        <el-table-column label="是否可取消" width="110">
          <template #default="{ row }">{{ formatBoolean(row.is_cancellable) }}</template>
        </el-table-column>
        <el-table-column prop="order_price" label="订单价格" min-width="110" />
        <el-table-column prop="currency_name" label="币种" min-width="90" />
        <el-table-column prop="office_id" label="配送办公点ID" min-width="135" />
        <el-table-column prop="cargo_type" label="货物类型" min-width="105" />
        <el-table-column prop="cross_border_type" label="跨境类型" min-width="105" />
        <el-table-column label="是否零订单" width="110">
          <template #default="{ row }">{{ formatBoolean(row.is_zero_order) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="84" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无订单数据" />
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

    <el-drawer v-model="drawerVisible" title="履约订单详情" size="820px">
      <el-descriptions v-if="currentRow" :column="2" border>
        <el-descriptions-item label="店铺ID">{{ displayValue(currentRow.shop_id) }}</el-descriptions-item>
        <el-descriptions-item label="订单ID（工作编号）">
          {{ displayValue(currentRow.order_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="供货ID">{{ displayValue(currentRow.supply_id) }}</el-descriptions-item>
        <el-descriptions-item label="贴纸ID">{{ displayValue(currentRow.sticker_id) }}</el-descriptions-item>
        <el-descriptions-item label="订单创建时间">
          {{ formatMoscowTime(currentRow.order_dt) }}
        </el-descriptions-item>
        <el-descriptions-item label="商品名称">{{ displayValue(currentRow.title) }}</el-descriptions-item>
        <el-descriptions-item label="商品名称（中文）">{{ displayValue(currentRow.title_cn) }}</el-descriptions-item>
        <el-descriptions-item label="尺寸">{{ displayValue(currentRow.tech_size) }}</el-descriptions-item>
        <el-descriptions-item label="尺寸（中文）">{{ displayValue(currentRow.tech_size_cn) }}</el-descriptions-item>
        <el-descriptions-item label="颜色">{{ displayValue(currentRow.color) }}</el-descriptions-item>
        <el-descriptions-item label="颜色（中文）">{{ displayValue(currentRow.color_cn) }}</el-descriptions-item>
        <el-descriptions-item label="原生条形码">
          {{ displayValue(currentRow.barcode_ori) }}
        </el-descriptions-item>
        <el-descriptions-item label="手调条形码">
          {{ displayValue(currentRow.barcode_hand) }}
        </el-descriptions-item>
        <el-descriptions-item label="零售价">{{ displayValue(currentRow.retail_price) }}</el-descriptions-item>
        <el-descriptions-item label="币种">
          {{ displayValue(currentRow.currency) }}
        </el-descriptions-item>
        <el-descriptions-item label="WB商品ID">{{ displayValue(currentRow.nm_id) }}</el-descriptions-item>
        <el-descriptions-item label="卖家货号">
          {{ displayValue(currentRow.supplier_article) }}
        </el-descriptions-item>
        <el-descriptions-item label="卖家仓库ID">
          {{ displayValue(currentRow.warehouse_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="卖家仓库">
          {{ displayValue(currentRow.warehouse_name) }}
        </el-descriptions-item>
        <el-descriptions-item label="卖家仓库（中文）">
          {{ displayValue(currentRow.warehouse_name_cn) }}
        </el-descriptions-item>
        <el-descriptions-item label="WB状态">{{ displayValue(currentRow.wb_status) }}</el-descriptions-item>
        <el-descriptions-item label="WB状态（中文）">{{ displayValue(currentRow.wb_status_cn) }}</el-descriptions-item>
        <el-descriptions-item label="是否B2B">{{ formatBoolean(currentRow.is_b2b) }}</el-descriptions-item>
        <el-descriptions-item label="配送类型">
          {{ displayValue(currentRow.delivery_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="卖家处理状态">
          {{ displayValue(currentRow.supplier_status) }}
        </el-descriptions-item>
        <el-descriptions-item label="卖家处理状态（中文）">
          {{ displayValue(currentRow.supplier_status_cn) }}
        </el-descriptions-item>
        <el-descriptions-item label="是否可取消">
          {{ formatBoolean(currentRow.is_cancellable) }}
        </el-descriptions-item>
        <el-descriptions-item label="订单价格">
          {{ displayValue(currentRow.order_price) }}
        </el-descriptions-item>
        <el-descriptions-item label="币种">
          {{ displayValue(currentRow.currency_name) }}
        </el-descriptions-item>
        <el-descriptions-item label="配送办公点ID">
          {{ displayValue(currentRow.office_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="货物类型">
          {{ displayValue(currentRow.cargo_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="跨境类型">
          {{ displayValue(currentRow.cross_border_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="是否零订单">
          {{ formatBoolean(currentRow.is_zero_order) }}
        </el-descriptions-item>
        <el-descriptions-item label="地址" :span="2">
          <div class="long-text">{{ displayValue(currentRow.address) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="地址（中文）" :span="2">
          <div class="long-text">{{ displayValue(currentRow.address_cn) }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type TableInstance } from 'element-plus'
import { ArrowDown, ArrowUp, RefreshLeft, Search } from '@element-plus/icons-vue'
import PlatformShopSelect from '@/components/PlatformShopSelect.vue'
import type { Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'
import {
  wbOrderApi,
  type ExportScope,
  type WBOrder,
  type WBOrderFilters,
  type WBOrderKey
} from '@/api/modules/wbOrder'

type OrderFilterForm = WBOrderFilters & {
  sort_order: 'asc' | 'desc'
}

const loading = ref(false)
const showAdvancedFilters = ref(false)
const shopNames = ref<Record<number, string>>({})
const exporting = ref(false)
const orders = ref<WBOrder[]>([])
const total = ref(0)
const dateRange = ref<string[]>([])
const selectedRows = ref<WBOrder[]>([])
const tableRef = ref<TableInstance>()
const drawerVisible = ref(false)
const currentRow = ref<WBOrder | null>(null)

const createFilters = (): OrderFilterForm => ({
  sort_order: 'desc'
})

const filters = reactive<OrderFilterForm>(createFilters())
const pagination = reactive({
  page: 1,
  page_size: 20
})

const rowKey = (row: WBOrder) => `${row.shop_id}:${row.order_id}`

function handleShopsLoaded(shops: Shop[]) {
  shopNames.value = Object.fromEntries(shops.map((shop) => [shop.id, shop.name]))
}

function getShopName(shopId: number) {
  return shopNames.value[shopId] ?? '-'
}

function activeFilters(): WBOrderFilters {
  return {
    shop_id: filters.shop_id ?? undefined,
    date_from: dateRange.value[0] || undefined,
    date_to: dateRange.value[1] || undefined,
    order_id: filters.order_id ?? undefined,
    supply_id: filters.supply_id || undefined,
    sticker_id: filters.sticker_id || undefined,
    nm_id: filters.nm_id ?? undefined,
    supplier_article: filters.supplier_article || undefined,
    warehouse_id: filters.warehouse_id ?? undefined,
    wb_status: filters.wb_status || undefined,
    supplier_status: filters.supplier_status || undefined,
    delivery_type: filters.delivery_type || undefined,
    is_cancellable: filters.is_cancellable ?? undefined,
    is_b2b: filters.is_b2b ?? undefined,
    is_zero_order: filters.is_zero_order ?? undefined,
    keyword: filters.keyword || undefined,
    sort_order: filters.sort_order
  }
}

let fetchRequestId = 0

async function fetchOrders() {
  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const response = await wbOrderApi.list({
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

function handleSelectionChange(rows: WBOrder[]) {
  selectedRows.value = rows
}

function openDetail(row: WBOrder) {
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

function formatMoscowTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').replace(/(\+|-)\d{2}:\d{2}$/, '')
}

async function exportOrders(scope: ExportScope) {
  if (scope === 'selected' && !selectedRows.value.length) {
    ElMessage.warning('请先勾选需要导出的订单')
    return
  }
  exporting.value = true
  try {
    const selectedKeys: WBOrderKey[] = selectedRows.value.map((row) => ({
      shop_id: row.shop_id,
      order_id: row.order_id
    }))
    const blob = await wbOrderApi.export({
      scope,
      filters: activeFilters(),
      selected_keys: scope === 'selected' ? selectedKeys : []
    })
    downloadExcel(blob, 'WB履约订单')
    ElMessage.success(scope === 'selected' ? '已导出选中订单' : '已导出筛选结果')
  } finally {
    exporting.value = false
  }
}

function handleExportFiltered() {
  exportOrders('filtered')
}

function handleExportCommand(command: ExportScope) {
  exportOrders(command)
}

onMounted(fetchOrders)
</script>

<style scoped lang="scss">
.order-page {
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

    .actions {
      :deep(.el-form-item__content) {
        flex-wrap: nowrap;
      }
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
  .order-page {
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
