<template>
  <div class="sales-funnel-list">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span>Wildberries 销售漏斗</span>
            <span class="record-count">共 {{ pagination.total }} 条</span>
          </div>
          <el-button
            type="success"
            :icon="Download"
            :loading="exporting"
            :disabled="!filters.shopId"
            @click="handleExport"
          >
            导出
          </el-button>
        </div>
      </template>

      <el-form :model="filters" inline class="filter-form">
        <el-form-item label="店铺">
          <el-select
            v-model="filters.shopId"
            placeholder="请选择店铺"
            filterable
            class="shop-select"
            @change="handleSearch"
          >
            <el-option
              v-for="shop in wildberriesShops"
              :key="shop.id"
              :label="shop.name"
              :value="shop.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="统计日期">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">
            查询
          </el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          <el-button
            text
            :icon="showAdvancedFilters ? ArrowUp : ArrowDown"
            @click="showAdvancedFilters = !showAdvancedFilters"
          >
            {{ showAdvancedFilters ? '收起条件' : '更多条件' }}
          </el-button>
        </el-form-item>
        <el-collapse-transition>
          <div v-show="showAdvancedFilters" class="advanced-filters">
            <el-form-item label="WB商品编号">
              <el-input
                v-model="filters.nmId"
                placeholder="请输入WB商品编号"
                clearable
                class="number-input"
              />
            </el-form-item>
            <el-form-item label="卖家商品编号">
              <el-input
                v-model.trim="filters.vendorCode"
                placeholder="支持模糊查询"
                clearable
              />
            </el-form-item>
            <el-form-item label="商品名称">
              <el-input
                v-model.trim="filters.title"
                placeholder="支持模糊查询"
                clearable
              />
            </el-form-item>
            <el-form-item label="项目">
              <el-input
                v-model.trim="filters.subjectName"
                placeholder="支持模糊查询"
                clearable
              />
            </el-form-item>
            <el-form-item label="品牌">
              <el-input
                v-model.trim="filters.brandName"
                placeholder="支持模糊查询"
                clearable
              />
            </el-form-item>
          </div>
        </el-collapse-transition>
      </el-form>

      <el-table
        v-loading="loading"
        :data="funnelList"
        :height="tableHeight"
        border
        stripe
        empty-text="暂无销售漏斗数据"
      >
        <el-table-column label="序号" width="70" align="center" fixed>
          <template #default="{ $index }">
            {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="shop_id" label="店铺ID" width="90" />
        <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ getShopName(row.shop_id) }}</template>
        </el-table-column>
        <el-table-column prop="date_from" label="统计开始日期" width="120" />
        <el-table-column prop="date_to" label="统计结束日期" width="120" />
        <el-table-column
          prop="vendor_code"
          label="卖家商品编号"
          width="150"
          show-overflow-tooltip
        />
        <el-table-column prop="nm_id" label="WB商品编号" width="130" />
        <el-table-column prop="title" label="名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="subject_name" label="项目" width="140" show-overflow-tooltip />
        <el-table-column prop="brand_name" label="品牌" width="130" show-overflow-tooltip />
        <el-table-column label="商品标签" width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ formatTags(row.tags) }}</template>
        </el-table-column>
        <el-table-column prop="product_rating" label="商品详情页评分" width="130" align="right" />
        <el-table-column prop="feedback_rating" label="评论评分" width="100" align="right" />
        <el-table-column prop="open_count" label="商品点击" width="100" align="right" />
        <el-table-column prop="cart_count" label="商品加购" width="100" align="right" />
        <el-table-column prop="add_to_wishlist" label="加入收藏夹" width="110" align="right" />
        <el-table-column prop="order_count" label="下单商品量" width="110" align="right" />
        <el-table-column prop="buyout_count" label="售出件数" width="100" align="right" />
        <el-table-column prop="cancel_count" label="取消订单商品量" width="130" align="right" />
        <el-table-column label="加购转化率" width="110" align="right">
          <template #default="{ row }">{{ formatPercent(row.add_to_cart_percent) }}</template>
        </el-table-column>
        <el-table-column label="下单转化率" width="110" align="right">
          <template #default="{ row }">{{ formatPercent(row.cart_to_order_percent) }}</template>
        </el-table-column>
        <el-table-column label="购买转化率" width="110" align="right">
          <template #default="{ row }">{{ formatPercent(row.buyout_percent) }}</template>
        </el-table-column>
        <el-table-column label="订单金额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.order_sum) }}</template>
        </el-table-column>
        <el-table-column label="售出金额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.buyout_sum) }}</template>
        </el-table-column>
        <el-table-column label="取消订单金额" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.cancel_sum) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.update_time) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="fetchFunnels"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowDown,
  ArrowUp,
  Download,
  Refresh,
  Search
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  salesFunnelApi,
  type SalesFunnelDetail,
  type SalesFunnelExportQuery,
  type SalesFunnelQuery
} from '@/api/modules/salesFunnel'
import { shopApi, type Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'

interface FilterForm {
  shopId?: number
  dateRange: string[]
  nmId: string
  vendorCode: string
  title: string
  subjectName: string
  brandName: string
}

const loading = ref(false)
const exporting = ref(false)
const showAdvancedFilters = ref(false)
const funnelList = ref<SalesFunnelDetail[]>([])
const wildberriesShops = ref<Shop[]>([])
const route = useRoute()
const tableHeight = computed(() =>
  showAdvancedFilters.value
    ? 'calc(100vh - 410px)'
    : 'calc(100vh - 300px)'
)

const filters = reactive<FilterForm>({
  shopId: undefined,
  dateRange: [],
  nmId: '',
  vendorCode: '',
  title: '',
  subjectName: '',
  brandName: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

function queryText(key: string): string | undefined {
  const value = route.query[key]
  return typeof value === 'string' && value ? value : undefined
}

function hydrateRouteFilters() {
  const shopId = Number(queryText('shop_id'))
  if (shopId > 0) filters.shopId = shopId
  filters.nmId = queryText('nm_id') || ''
  filters.vendorCode = queryText('vendor_code') || ''
  const dateFrom = queryText('date_from')
  const dateTo = queryText('date_to')
  if (dateFrom && dateTo) filters.dateRange = [dateFrom, dateTo]
}

const optionalPositiveNumber = (value: string): number | undefined => {
  if (!value.trim()) return undefined
  const numberValue = Number(value)
  return Number.isInteger(numberValue) && numberValue > 0 ? numberValue : undefined
}

const buildExportQuery = (): SalesFunnelExportQuery | null => {
  if (!filters.shopId) {
    ElMessage.warning('请先选择店铺')
    return null
  }

  return {
    shop_id: filters.shopId,
    date_from: filters.dateRange[0] || undefined,
    date_to: filters.dateRange[1] || undefined,
    nm_id: optionalPositiveNumber(filters.nmId),
    vendor_code: filters.vendorCode || undefined,
    title: filters.title || undefined,
    subject_name: filters.subjectName || undefined,
    brand_name: filters.brandName || undefined
  }
}

const buildListQuery = (): SalesFunnelQuery | null => {
  const query = buildExportQuery()
  if (!query) return null
  return {
    ...query,
    page: pagination.page,
    page_size: pagination.pageSize
  }
}

let fetchRequestId = 0

const fetchFunnels = async () => {
  const query = buildListQuery()
  if (!query) return

  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const result = await salesFunnelApi.list(query)
    if (requestId === fetchRequestId) {
      funnelList.value = result.items
      pagination.total = result.total
    }
  } finally {
    if (requestId === fetchRequestId) loading.value = false
  }
}

const fetchShops = async () => {
  const shops = await shopApi.list()
  wildberriesShops.value = shops.filter((shop) => shop.platform === 'wildberries')
  if (!filters.shopId && wildberriesShops.value.length > 0) {
    filters.shopId = wildberriesShops.value[0].id
  }
}

const getShopName = (shopId: number): string =>
  wildberriesShops.value.find((shop) => shop.id === shopId)?.name ?? '-'

const handleSearch = () => {
  const nmId = filters.nmId.trim()
  if (nmId && !optionalPositiveNumber(nmId)) {
    ElMessage.warning('WB商品编号必须是正整数')
    return
  }
  showAdvancedFilters.value = false
  pagination.page = 1
  fetchFunnels()
}

const handleReset = () => {
  filters.dateRange = []
  filters.nmId = ''
  filters.vendorCode = ''
  filters.title = ''
  filters.subjectName = ''
  filters.brandName = ''
  showAdvancedFilters.value = false
  pagination.page = 1
  pagination.pageSize = 20
  fetchFunnels()
}

const handleSizeChange = () => {
  pagination.page = 1
  fetchFunnels()
}

const handleExport = async () => {
  const query = buildExportQuery()
  if (!query) return

  exporting.value = true
  try {
    const content = await salesFunnelApi.export(query)
    downloadExcel(content, 'WB销售漏斗明细')
    ElMessage.success('导出成功')
  } finally {
    exporting.value = false
  }
}

const formatMoney = (value?: string): string => {
  if (value === undefined || value === null || value === '') return '-'
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return value
  return numberValue.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const formatPercent = (value?: string): string => {
  if (value === undefined || value === null || value === '') return '-'
  return `${value}%`
}

const formatTags = (value: unknown): string => {
  if (value === undefined || value === null || value === '') return '-'
  if (Array.isArray(value)) return value.join('、')
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

const formatDateTime = (value?: string): string => {
  if (!value) return '-'
  return value.replace('T', ' ').replace(/(\.\d+)?([+-]\d{2}:\d{2}|Z)$/, '')
}

onMounted(async () => {
  try {
    hydrateRouteFilters()
    await fetchShops()
    if (filters.shopId) {
      await fetchFunnels()
    }
  } catch {
    // 请求拦截器统一展示错误信息
  }
})
</script>

<style scoped lang="scss">
.sales-funnel-list {
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 600;

    .record-count {
      margin-left: 12px;
      color: var(--el-text-color-secondary);
      font-size: 13px;
      font-weight: 400;
    }
  }

  .filter-form {
    margin-bottom: 4px;

    .shop-select {
      width: 200px;
    }

    .number-input {
      width: 180px;
    }

    .advanced-filters {
      display: flex;
      flex-wrap: wrap;
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
    overflow-x: auto;
  }
}
</style>
