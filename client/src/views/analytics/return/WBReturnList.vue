<template>
  <div class="return-page">
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
            <el-form-item label="配货单号">
              <el-input-number
                v-model="filters.order_id"
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
            <el-form-item label="品牌">
              <el-input
                v-model.trim="filters.brand"
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
            <el-form-item label="状态">
              <el-input
                v-model.trim="filters.status"
                placeholder="支持模糊查询"
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
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="24" :lg="8">
            <el-form-item label="关键词">
              <el-input
                v-model.trim="filters.keyword"
                placeholder="条码、标签、系统订单号、原因或地址"
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
            <span class="title">Wildberries 退货</span>
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
        <el-table-column prop="shop_id" label="店铺ID" width="92" />
        <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ getShopName(row.shop_id) }}</template>
        </el-table-column>
        <el-table-column prop="brand" label="品牌" min-width="130" show-overflow-tooltip />
        <el-table-column prop="subject_name" label="商品品类" min-width="140" show-overflow-tooltip />
        <el-table-column prop="subject_name_cn" label="商品品类（中文）" min-width="140" show-overflow-tooltip />
        <el-table-column prop="barcode" label="条形码（barcode）" min-width="160" show-overflow-tooltip />
        <el-table-column prop="nm_id" label="WB商品ID" min-width="125" />
        <el-table-column prop="bar_code" label="条码（bar_code）" min-width="160" show-overflow-tooltip />
        <el-table-column prop="sticker_id" label="标签ID" min-width="170" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" min-width="150" show-overflow-tooltip />
        <el-table-column prop="status_cn" label="状态（中文）" min-width="150" show-overflow-tooltip />
        <el-table-column label="准备好取货时间（莫斯科）" min-width="210">
          <template #default="{ row }">{{ formatMoscowTime(row.ready_to_return_dt) }}</template>
        </el-table-column>
        <el-table-column label="已被领取时间（莫斯科）" min-width="210">
          <template #default="{ row }">{{ formatMoscowTime(row.completed_dt) }}</template>
        </el-table-column>
        <el-table-column label="过期时间（莫斯科）" min-width="190">
          <template #default="{ row }">{{ formatMoscowTime(row.expired_dt) }}</template>
        </el-table-column>
        <el-table-column prop="return_type" label="退货类型" min-width="150" show-overflow-tooltip />
        <el-table-column prop="return_type_cn" label="退货类型（中文）" min-width="150" show-overflow-tooltip />
        <el-table-column prop="order_date" label="下单日期" width="120" />
        <el-table-column prop="reason" label="退货原因" min-width="220" show-overflow-tooltip />
        <el-table-column prop="reason_cn" label="退货原因（中文）" min-width="220" show-overflow-tooltip />
        <el-table-column prop="order_id" label="配货单号" min-width="150" />
        <el-table-column prop="srid" label="系统订单号" min-width="220" show-overflow-tooltip />
        <el-table-column
          prop="dst_office_address"
          label="地址"
          min-width="240"
          show-overflow-tooltip
        />
        <el-table-column
          prop="dst_office_address_cn"
          label="地址（中文）"
          min-width="240"
          show-overflow-tooltip
        />
        <el-table-column prop="dst_office_id" label="地址ID" min-width="120" />
        <el-table-column label="操作" width="84" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无退货数据" />
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

    <el-drawer v-model="drawerVisible" title="退货详情" size="760px">
      <el-descriptions v-if="currentRow" :column="2" border>
        <el-descriptions-item label="店铺ID">{{ displayValue(currentRow.shop_id) }}</el-descriptions-item>
        <el-descriptions-item label="品牌">{{ displayValue(currentRow.brand) }}</el-descriptions-item>
        <el-descriptions-item label="商品品类">{{ displayValue(currentRow.subject_name) }}</el-descriptions-item>
        <el-descriptions-item label="商品品类（中文）">{{ displayValue(currentRow.subject_name_cn) }}</el-descriptions-item>
        <el-descriptions-item label="条形码（barcode）">{{ displayValue(currentRow.barcode) }}</el-descriptions-item>
        <el-descriptions-item label="WB商品ID">{{ displayValue(currentRow.nm_id) }}</el-descriptions-item>
        <el-descriptions-item label="条码（bar_code）">{{ displayValue(currentRow.bar_code) }}</el-descriptions-item>
        <el-descriptions-item label="标签ID">{{ displayValue(currentRow.sticker_id) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ displayValue(currentRow.status) }}</el-descriptions-item>
        <el-descriptions-item label="状态（中文）">{{ displayValue(currentRow.status_cn) }}</el-descriptions-item>
        <el-descriptions-item label="准备好取货时间">
          {{ formatMoscowTime(currentRow.ready_to_return_dt) }}
        </el-descriptions-item>
        <el-descriptions-item label="已被领取时间">
          {{ formatMoscowTime(currentRow.completed_dt) }}
        </el-descriptions-item>
        <el-descriptions-item label="过期时间">
          {{ formatMoscowTime(currentRow.expired_dt) }}
        </el-descriptions-item>
        <el-descriptions-item label="退货类型">{{ displayValue(currentRow.return_type) }}</el-descriptions-item>
        <el-descriptions-item label="退货类型（中文）">{{ displayValue(currentRow.return_type_cn) }}</el-descriptions-item>
        <el-descriptions-item label="下单日期">{{ displayValue(currentRow.order_date) }}</el-descriptions-item>
        <el-descriptions-item label="配货单号">{{ displayValue(currentRow.order_id) }}</el-descriptions-item>
        <el-descriptions-item label="系统订单号" :span="2">
          {{ displayValue(currentRow.srid) }}
        </el-descriptions-item>
        <el-descriptions-item label="退货原因" :span="2">
          <div class="long-text">{{ displayValue(currentRow.reason) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="退货原因（中文）" :span="2">
          <div class="long-text">{{ displayValue(currentRow.reason_cn) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="地址" :span="2">
          <div class="long-text">{{ displayValue(currentRow.dst_office_address) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="地址（中文）" :span="2">
          <div class="long-text">{{ displayValue(currentRow.dst_office_address_cn) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="地址ID">{{ displayValue(currentRow.dst_office_id) }}</el-descriptions-item>
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
  wbReturnApi,
  type ExportScope,
  type WBReturn,
  type WBReturnFilters,
  type WBReturnKey
} from '@/api/modules/wbReturn'

type ReturnFilterForm = WBReturnFilters & {
  sort_order: 'asc' | 'desc'
}

const loading = ref(false)
const showAdvancedFilters = ref(false)
const shopNames = ref<Record<number, string>>({})
const exporting = ref(false)
const returns = ref<WBReturn[]>([])
const total = ref(0)
const dateRange = ref<string[]>([])
const selectedRows = ref<WBReturn[]>([])
const tableRef = ref<TableInstance>()
const drawerVisible = ref(false)
const currentRow = ref<WBReturn | null>(null)
const route = useRoute()

const createFilters = (): ReturnFilterForm => ({
  sort_order: 'desc'
})

const filters = reactive<ReturnFilterForm>(createFilters())
const pagination = reactive({
  page: 1,
  page_size: 20
})

const rowKey = (row: WBReturn) => `${row.shop_id}:${row.srid}`

function queryText(key: string): string | undefined {
  const value = route.query[key]
  return typeof value === 'string' && value ? value : undefined
}

function hydrateRouteFilters() {
  const shopId = Number(queryText('shop_id'))
  const nmId = Number(queryText('nm_id'))
  if (shopId > 0) filters.shop_id = shopId
  if (nmId > 0) filters.nm_id = nmId
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

function activeFilters(): WBReturnFilters {
  return {
    shop_id: filters.shop_id ?? undefined,
    date_from: dateRange.value[0] || undefined,
    date_to: dateRange.value[1] || undefined,
    nm_id: filters.nm_id ?? undefined,
    order_id: filters.order_id ?? undefined,
    brand: filters.brand || undefined,
    subject_name: filters.subject_name || undefined,
    status: filters.status || undefined,
    return_type: filters.return_type || undefined,
    keyword: filters.keyword || undefined,
    sort_order: filters.sort_order
  }
}

let fetchRequestId = 0

async function fetchReturns() {
  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const response = await wbReturnApi.list({
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

function handleSelectionChange(rows: WBReturn[]) {
  selectedRows.value = rows
}

function openDetail(row: WBReturn) {
  currentRow.value = row
  drawerVisible.value = true
}

function displayValue(value: string | number | null | undefined) {
  return value === null || value === undefined || value === '' ? '-' : value
}

function formatMoscowTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').replace(/(\+|-)\d{2}:\d{2}$/, '')
}

async function exportReturns(scope: ExportScope) {
  if (scope === 'selected' && !selectedRows.value.length) {
    ElMessage.warning('请先勾选需要导出的退货记录')
    return
  }
  exporting.value = true
  try {
    const selectedKeys: WBReturnKey[] = selectedRows.value.map((row) => ({
      shop_id: row.shop_id,
      srid: row.srid
    }))
    const blob = await wbReturnApi.export({
      scope,
      filters: activeFilters(),
      selected_keys: scope === 'selected' ? selectedKeys : []
    })
    downloadExcel(blob, 'WB退货')
    ElMessage.success(scope === 'selected' ? '已导出选中退货记录' : '已导出筛选结果')
  } finally {
    exporting.value = false
  }
}

function handleExportFiltered() {
  exportReturns('filtered')
}

function handleExportCommand(command: ExportScope) {
  exportReturns(command)
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

