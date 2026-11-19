<template>
  <div class="feedback-page">
    <el-card shadow="never" class="search-card">
      <el-form :model="filters" label-width="82px" class="search-form">
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
            <el-form-item label="星级">
              <el-select
                v-model="filters.product_valuations"
                multiple
                collapse-tags
                collapse-tags-tooltip
                placeholder="请选择"
                clearable
              >
                <el-option
                  v-for="rating in ratings"
                  :key="rating"
                  :label="`${rating} 星`"
                  :value="rating"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="8">
            <el-form-item label="关键词">
              <el-input
                v-model.trim="filters.keyword"
                placeholder="商品名称、评价、优缺点、用户名或回复"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="6">
            <el-form-item label="卖家货号">
              <el-input
                v-model.trim="filters.supplier_article"
                placeholder="支持模糊查询"
                clearable
                @keyup.enter="handleSearch"
              />
            </el-form-item>
          </el-col>
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="5">
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
          <el-col v-show="showAdvancedFilters" style="order: 2" :xs="24" :sm="12" :lg="5">
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
            <el-form-item label="回复状态">
              <el-select v-model="filters.answer_status" placeholder="全部" clearable>
                <el-option label="已回复" value="answered" />
                <el-option label="未回复" value="unanswered" />
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
        </el-row>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="table-header">
          <div>
            <span class="title">Wildberries 客户评价</span>
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
        :data="feedbacks"
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
        <el-table-column prop="feedback_id" label="评价ID" min-width="190" show-overflow-tooltip />
        <el-table-column label="评价时间（莫斯科）" min-width="176">
          <template #default="{ row }">{{ formatMoscowTime(row.created_date) }}</template>
        </el-table-column>
        <el-table-column prop="supplier_article" label="卖家货号" min-width="170" show-overflow-tooltip />
        <el-table-column prop="nm_id" label="WB商品ID" min-width="130" />
        <el-table-column prop="product_name" label="商品名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="product_name_cn" label="商品名称（中文）" min-width="220" show-overflow-tooltip />
        <el-table-column label="星级" width="190">
          <template #default="{ row }">
            <el-rate
              v-if="row.product_valuation"
              :model-value="row.product_valuation"
              disabled
              show-score
              score-template="{value} 星"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="brand_name" label="品牌" min-width="120" show-overflow-tooltip />
        <el-table-column prop="text" label="评价正文" min-width="220" show-overflow-tooltip />
        <el-table-column prop="text_cn" label="评价正文（中文）" min-width="220" show-overflow-tooltip />
        <el-table-column prop="pros" label="优点" min-width="180" show-overflow-tooltip />
        <el-table-column prop="pros_cn" label="优点（中文）" min-width="180" show-overflow-tooltip />
        <el-table-column prop="cons" label="缺点" min-width="180" show-overflow-tooltip />
        <el-table-column prop="cons_cn" label="缺点（中文）" min-width="180" show-overflow-tooltip />
        <el-table-column prop="user_name" label="用户姓名" min-width="120" show-overflow-tooltip />
        <el-table-column prop="color" label="颜色" min-width="120" show-overflow-tooltip />
        <el-table-column prop="color_cn" label="颜色（中文）" min-width="120" show-overflow-tooltip />
        <el-table-column prop="size" label="尺码" width="90" show-overflow-tooltip />
        <el-table-column prop="size_cn" label="尺码（中文）" min-width="110" show-overflow-tooltip />
        <el-table-column prop="answer" label="商家回复" min-width="240" show-overflow-tooltip />
        <el-table-column prop="answer_cn" label="商家回复（中文）" min-width="240" show-overflow-tooltip />
        <el-table-column
          prop="parent_feedback_id"
          label="初始评价ID"
          min-width="170"
          show-overflow-tooltip
        />
        <el-table-column
          prop="child_feedback_id"
          label="追加评价ID"
          min-width="170"
          show-overflow-tooltip
        />
        <el-table-column label="操作" width="84" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">查看</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无客户评价数据" />
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
          @current-change="fetchFeedbacks"
        />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" title="客户评价详情" size="720px">
      <el-descriptions v-if="currentRow" :column="2" border>
        <el-descriptions-item label="店铺ID">{{ displayValue(currentRow.shop_id) }}</el-descriptions-item>
        <el-descriptions-item label="店铺名称">{{ getShopName(currentRow.shop_id) }}</el-descriptions-item>
        <el-descriptions-item label="评价ID">{{ displayValue(currentRow.feedback_id) }}</el-descriptions-item>
        <el-descriptions-item label="评价时间">
          {{ formatMoscowTime(currentRow.created_date) }}
        </el-descriptions-item>
        <el-descriptions-item label="星级">
          {{ currentRow.product_valuation ? `${currentRow.product_valuation} 星` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="卖家货号">{{ displayValue(currentRow.supplier_article) }}</el-descriptions-item>
        <el-descriptions-item label="WB商品ID">{{ displayValue(currentRow.nm_id) }}</el-descriptions-item>
        <el-descriptions-item label="商品名称" :span="2">
          {{ displayValue(currentRow.product_name) }}
        </el-descriptions-item>
        <el-descriptions-item label="商品名称（中文）" :span="2">
          {{ displayValue(currentRow.product_name_cn) }}
        </el-descriptions-item>
        <el-descriptions-item label="品牌">{{ displayValue(currentRow.brand_name) }}</el-descriptions-item>
        <el-descriptions-item label="用户姓名">{{ displayValue(currentRow.user_name) }}</el-descriptions-item>
        <el-descriptions-item label="颜色">{{ displayValue(currentRow.color) }}</el-descriptions-item>
        <el-descriptions-item label="颜色（中文）">{{ displayValue(currentRow.color_cn) }}</el-descriptions-item>
        <el-descriptions-item label="尺码">{{ displayValue(currentRow.size) }}</el-descriptions-item>
        <el-descriptions-item label="尺码（中文）">{{ displayValue(currentRow.size_cn) }}</el-descriptions-item>
        <el-descriptions-item label="初始评价ID">
          {{ displayValue(currentRow.parent_feedback_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="追加评价ID">
          {{ displayValue(currentRow.child_feedback_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="评价正文" :span="2">
          <div class="long-text">{{ displayValue(currentRow.text) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="评价正文（中文）" :span="2">
          <div class="long-text">{{ displayValue(currentRow.text_cn) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="优点" :span="2">
          <div class="long-text">{{ displayValue(currentRow.pros) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="优点（中文）" :span="2">
          <div class="long-text">{{ displayValue(currentRow.pros_cn) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="缺点" :span="2">
          <div class="long-text">{{ displayValue(currentRow.cons) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="缺点（中文）" :span="2">
          <div class="long-text">{{ displayValue(currentRow.cons_cn) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="商家回复" :span="2">
          <div class="long-text">{{ displayValue(currentRow.answer) }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="商家回复（中文）" :span="2">
          <div class="long-text">{{ displayValue(currentRow.answer_cn) }}</div>
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
  vocFeedbackApi,
  type ExportScope,
  type WBVOCFeedback,
  type WBVOCFeedbackFilters,
  type WBVOCFeedbackKey
} from '@/api/modules/vocFeedback'

type FeedbackFilterForm = WBVOCFeedbackFilters & {
  product_valuations: number[]
  sort_order: 'asc' | 'desc'
}

const ratings = [1, 2, 3, 4, 5]
const loading = ref(false)
const showAdvancedFilters = ref(false)
const shopNames = ref<Record<number, string>>({})
const exporting = ref(false)
const feedbacks = ref<WBVOCFeedback[]>([])
const total = ref(0)
const dateRange = ref<string[]>([])
const selectedRows = ref<WBVOCFeedback[]>([])
const tableRef = ref<TableInstance>()
const drawerVisible = ref(false)
const currentRow = ref<WBVOCFeedback | null>(null)

const createFilters = (): FeedbackFilterForm => ({
  product_valuations: [],
  sort_order: 'desc'
})

const filters = reactive<FeedbackFilterForm>(createFilters())
const pagination = reactive({
  page: 1,
  page_size: 20
})

const rowKey = (row: WBVOCFeedback) => `${row.shop_id}:${row.feedback_id}`

function handleShopsLoaded(shops: Shop[]) {
  shopNames.value = Object.fromEntries(shops.map((shop) => [shop.id, shop.name]))
}

function getShopName(shopId: number) {
  return shopNames.value[shopId] ?? '-'
}

function activeFilters(): WBVOCFeedbackFilters {
  return {
    shop_id: filters.shop_id ?? undefined,
    date_from: dateRange.value[0] || undefined,
    date_to: dateRange.value[1] || undefined,
    product_valuations: filters.product_valuations.length
      ? [...filters.product_valuations]
      : undefined,
    supplier_article: filters.supplier_article || undefined,
    nm_id: filters.nm_id ?? undefined,
    brand_name: filters.brand_name || undefined,
    keyword: filters.keyword || undefined,
    answer_status: filters.answer_status || undefined,
    sort_order: filters.sort_order
  }
}

let fetchRequestId = 0

async function fetchFeedbacks() {
  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const response = await vocFeedbackApi.list({
      ...activeFilters(),
      page: pagination.page,
      page_size: pagination.page_size
    })
    if (requestId === fetchRequestId) {
      feedbacks.value = response.items
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
  fetchFeedbacks()
}

function handleReset() {
  showAdvancedFilters.value = false
  Object.assign(filters, createFilters())
  dateRange.value = []
  pagination.page = 1
  clearSelection()
  fetchFeedbacks()
}

function handleSizeChange() {
  pagination.page = 1
  fetchFeedbacks()
}

function handleSelectionChange(rows: WBVOCFeedback[]) {
  selectedRows.value = rows
}

function openDetail(row: WBVOCFeedback) {
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

async function exportFeedbacks(scope: ExportScope) {
  if (scope === 'selected' && !selectedRows.value.length) {
    ElMessage.warning('请先勾选需要导出的评价')
    return
  }
  exporting.value = true
  try {
    const selectedKeys: WBVOCFeedbackKey[] = selectedRows.value.map((row) => ({
      shop_id: row.shop_id,
      feedback_id: row.feedback_id
    }))
    const blob = await vocFeedbackApi.export({
      scope,
      filters: activeFilters(),
      selected_keys: scope === 'selected' ? selectedKeys : []
    })
    downloadExcel(blob, 'WB客户评价')
    ElMessage.success(scope === 'selected' ? '已导出选中评价' : '已导出筛选结果')
  } finally {
    exporting.value = false
  }
}

function handleExportFiltered() {
  exportFeedbacks('filtered')
}

function handleExportCommand(command: ExportScope) {
  exportFeedbacks(command)
}

onMounted(fetchFeedbacks)
</script>

<style scoped lang="scss">
.feedback-page {
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
  .feedback-page {
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
