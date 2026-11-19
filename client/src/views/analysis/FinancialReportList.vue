<template>
  <div class="financial-report-list">
    <AnalyticsPageHeader
      title="财务报表周明细"
      description="查看 Wildberries 周度结算明细、费用及卖家应收金额"
    />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span>明细数据</span>
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
        <el-form-item label="报告日期">
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
            <el-form-item label="商家编码">
              <el-input
                v-model.trim="filters.vendorCode"
                placeholder="支持模糊查询"
                clearable
              />
            </el-form-item>
            <el-form-item label="业务类型">
              <el-input
                v-model.trim="filters.sellerOperName"
                placeholder="请输入业务类型"
                clearable
              />
            </el-form-item>
          </div>
        </el-collapse-transition>
      </el-form>

      <el-table
        v-loading="loading"
        :data="reportList"
        :height="tableHeight"
        border
        stripe
        empty-text="暂无财务明细数据"
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
        <el-table-column prop="date_from" label="报告周开始日期" width="130" fixed />
        <el-table-column prop="rrd_id" label="明细编号" width="145" />
        <el-table-column prop="vendor_code" label="商家编码" width="150" show-overflow-tooltip />
        <el-table-column prop="nm_id" label="WB商品编号" width="130" />
        <el-table-column prop="title" label="商品名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="subject_name" label="商品品类" width="150" show-overflow-tooltip />
        <el-table-column prop="sku" label="条形码" width="150" show-overflow-tooltip />
        <el-table-column prop="tech_size" label="尺码" width="90" show-overflow-tooltip />
        <el-table-column
          prop="seller_oper_name"
          label="业务类型"
          width="150"
          show-overflow-tooltip
        />
        <el-table-column
          prop="doc_type_name"
          label="单据类型"
          width="130"
          show-overflow-tooltip
        />
        <el-table-column prop="quantity" label="数量" width="80" align="right" />
        <el-table-column label="销售金额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.retail_amount) }}</template>
        </el-table-column>
        <el-table-column label="佣金比例" width="110" align="right">
          <template #default="{ row }">{{ formatPercent(row.commission_percent) }}</template>
        </el-table-column>
        <el-table-column label="销售佣金" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.ppvz_sales_commission) }}</template>
        </el-table-column>
        <el-table-column label="收单费" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.acquiring_fee) }}</template>
        </el-table-column>
        <el-table-column label="物流费" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.delivery_service) }}</template>
        </el-table-column>
        <el-table-column label="仓储费" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.paid_storage) }}</template>
        </el-table-column>
        <el-table-column label="罚款" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.penalty) }}</template>
        </el-table-column>
        <el-table-column label="扣款" width="110" align="right">
          <template #default="{ row }">{{ formatMoney(row.deduction) }}</template>
        </el-table-column>
        <el-table-column label="卖家应收" width="120" align="right" fixed="right">
          <template #default="{ row }">{{ formatMoney(row.for_pay) }}</template>
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
          @current-change="fetchReports"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ArrowDown,
  ArrowUp,
  Download,
  Refresh,
  Search
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AnalyticsPageHeader from '@/components/analytics/AnalyticsPageHeader.vue'
import {
  financialReportApi,
  type FinancialReportDetail,
  type FinancialReportExportQuery,
  type FinancialReportQuery
} from '@/api/modules/financialReport'
import { shopApi, type Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'

interface FilterForm {
  shopId?: number
  dateRange: string[]
  nmId: string
  vendorCode: string
  sellerOperName: string
}

const loading = ref(false)
const exporting = ref(false)
const showAdvancedFilters = ref(false)
const reportList = ref<FinancialReportDetail[]>([])
const wildberriesShops = ref<Shop[]>([])
const tableHeight = computed(() =>
  showAdvancedFilters.value
    ? 'calc(100vh - 360px)'
    : 'calc(100vh - 300px)'
)

const filters = reactive<FilterForm>({
  shopId: undefined,
  dateRange: [],
  nmId: '',
  vendorCode: '',
  sellerOperName: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const optionalPositiveNumber = (value: string): number | undefined => {
  if (!value.trim()) return undefined
  const numberValue = Number(value)
  return Number.isInteger(numberValue) && numberValue > 0 ? numberValue : undefined
}

const buildExportQuery = (): FinancialReportExportQuery | null => {
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
    seller_oper_name: filters.sellerOperName || undefined
  }
}

const buildListQuery = (): FinancialReportQuery | null => {
  const query = buildExportQuery()
  if (!query) return null
  return {
    ...query,
    page: pagination.page,
    page_size: pagination.pageSize
  }
}

let fetchRequestId = 0

const fetchReports = async () => {
  const query = buildListQuery()
  if (!query) return

  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const result = await financialReportApi.list(query)
    if (requestId === fetchRequestId) {
      reportList.value = result.items
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
  fetchReports()
}

const handleReset = () => {
  filters.dateRange = []
  filters.nmId = ''
  filters.vendorCode = ''
  filters.sellerOperName = ''
  showAdvancedFilters.value = false
  pagination.page = 1
  pagination.pageSize = 20
  fetchReports()
}

const handleSizeChange = () => {
  pagination.page = 1
  fetchReports()
}

const handleExport = async () => {
  const query = buildExportQuery()
  if (!query) return

  exporting.value = true
  try {
    const content = await financialReportApi.export(query)
    downloadExcel(content, 'WB财务报告周明细')
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

onMounted(async () => {
  try {
    await fetchShops()
    if (filters.shopId) {
      await fetchReports()
    }
  } catch {
    // 请求拦截器统一展示错误信息
  }
})
</script>

<style scoped lang="scss">
.financial-report-list {
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
