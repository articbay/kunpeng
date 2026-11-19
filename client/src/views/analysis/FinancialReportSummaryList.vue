<template>
  <div class="financial-report-summary-list">
    <AnalyticsPageHeader
      title="财务报表周汇总"
      description="查看 Wildberries 周度结算汇总、费用构成及应付总额"
    />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span>汇总数据</span>
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
            <el-form-item label="生成日期">
              <el-date-picker
                v-model="filters.createDateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
            <el-form-item label="报告编号">
              <el-input
                v-model="filters.reportId"
                placeholder="请输入报告编号"
                clearable
                class="number-input"
              />
            </el-form-item>
            <el-form-item label="法人">
              <el-input
                v-model.trim="filters.sellerFinanceName"
                placeholder="支持模糊查询"
                clearable
              />
            </el-form-item>
            <el-form-item label="报告类型">
              <el-input
                v-model="filters.reportType"
                placeholder="请输入报告类型"
                clearable
                class="number-input"
              />
            </el-form-item>
            <el-form-item label="货币">
              <el-input
                v-model.trim="filters.currency"
                placeholder="请输入货币"
                clearable
                class="currency-input"
              />
            </el-form-item>
          </div>
        </el-collapse-transition>
      </el-form>

      <el-table
        v-loading="loading"
        :data="summaryList"
        :height="tableHeight"
        border
        stripe
        empty-text="暂无财务报表周汇总数据"
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
        <el-table-column prop="report_id" label="报告编号" width="145" />
        <el-table-column
          prop="seller_finance_name"
          label="法人"
          width="180"
          show-overflow-tooltip
        />
        <el-table-column prop="date_from" label="开始日期" width="120" />
        <el-table-column prop="date_to" label="结束日期" width="120" />
        <el-table-column prop="create_date" label="生成日期" width="120" />
        <el-table-column prop="report_type" label="报告类型" width="100" align="right" />
        <el-table-column label="销售" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.retail_amount_sum) }}</template>
        </el-table-column>
        <el-table-column label="包括忠诚度计划的折扣赔偿" width="210" align="right">
          <template #default="{ row }">
            {{ formatMoney(row.cashback_discount_sum) }}
          </template>
        </el-table-column>
        <el-table-column label="应支付商品金额" width="150" align="right">
          <template #default="{ row }">{{ formatMoney(row.for_pay_sum) }}</template>
        </el-table-column>
        <el-table-column label="协商折扣(%)" width="130" align="right">
          <template #default="{ row }">{{ formatPercent(row.avg_sale_percent) }}</template>
        </el-table-column>
        <el-table-column label="物流费用" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.delivery_service_sum) }}</template>
        </el-table-column>
        <el-table-column label="仓储费用" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.paid_storage_sum) }}</template>
        </el-table-column>
        <el-table-column label="入库验收费用" width="140" align="right">
          <template #default="{ row }">{{ formatMoney(row.paid_acceptance_sum) }}</template>
        </el-table-column>
        <el-table-column label="其他扣款/付款" width="140" align="right">
          <template #default="{ row }">{{ formatMoney(row.deduction_sum) }}</template>
        </el-table-column>
        <el-table-column label="罚款总额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.penalty_sum) }}</template>
        </el-table-column>
        <el-table-column label="WB佣金调整" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.additional_payment_sum) }}</template>
        </el-table-column>
        <el-table-column label="忠诚度计划参与费用" width="180" align="right">
          <template #default="{ row }">
            {{ formatMoney(row.cashback_commission_change_sum) }}
          </template>
        </el-table-column>
        <el-table-column label="已扣除的忠诚度积分金额" width="200" align="right">
          <template #default="{ row }">{{ formatMoney(row.cashback_amount_sum) }}</template>
        </el-table-column>
        <el-table-column label="一次性结算周期变更" width="180" align="right">
          <template #default="{ row }">{{ formatMoney(row.payment_schedule) }}</template>
        </el-table-column>
        <el-table-column label="应付总额" width="130" align="right">
          <template #default="{ row }">{{ formatMoney(row.bank_payment_sum) }}</template>
        </el-table-column>
        <el-table-column prop="currency" label="货币" width="90" />
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
          @current-change="fetchSummaries"
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
  financialReportSummaryApi,
  type FinancialReportSummary,
  type FinancialReportSummaryExportQuery,
  type FinancialReportSummaryQuery
} from '@/api/modules/financialReportSummary'
import { shopApi, type Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'

interface FilterForm {
  shopId?: number
  dateRange: string[]
  createDateRange: string[]
  reportId: string
  sellerFinanceName: string
  reportType: string
  currency: string
}

const loading = ref(false)
const exporting = ref(false)
const showAdvancedFilters = ref(false)
const summaryList = ref<FinancialReportSummary[]>([])
const wildberriesShops = ref<Shop[]>([])
const tableHeight = computed(() =>
  showAdvancedFilters.value
    ? 'calc(100vh - 410px)'
    : 'calc(100vh - 300px)'
)

const filters = reactive<FilterForm>({
  shopId: undefined,
  dateRange: [],
  createDateRange: [],
  reportId: '',
  sellerFinanceName: '',
  reportType: '',
  currency: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const optionalInteger = (
  value: string,
  minimum: number
): number | undefined => {
  if (!value.trim()) return undefined
  const numberValue = Number(value)
  return Number.isInteger(numberValue) && numberValue >= minimum
    ? numberValue
    : undefined
}

const buildExportQuery = (): FinancialReportSummaryExportQuery | null => {
  if (!filters.shopId) {
    ElMessage.warning('请先选择店铺')
    return null
  }

  return {
    shop_id: filters.shopId,
    date_from: filters.dateRange[0] || undefined,
    date_to: filters.dateRange[1] || undefined,
    create_date_from: filters.createDateRange[0] || undefined,
    create_date_to: filters.createDateRange[1] || undefined,
    report_id: optionalInteger(filters.reportId, 1),
    seller_finance_name: filters.sellerFinanceName || undefined,
    report_type: optionalInteger(filters.reportType, 0),
    currency: filters.currency || undefined
  }
}

const buildListQuery = (): FinancialReportSummaryQuery | null => {
  const query = buildExportQuery()
  if (!query) return null
  return {
    ...query,
    page: pagination.page,
    page_size: pagination.pageSize
  }
}

let fetchRequestId = 0

const fetchSummaries = async () => {
  const query = buildListQuery()
  if (!query) return

  const requestId = ++fetchRequestId
  loading.value = true
  try {
    const result = await financialReportSummaryApi.list(query)
    if (requestId === fetchRequestId) {
      summaryList.value = result.items
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

const validateFilters = (): boolean => {
  const reportId = filters.reportId.trim()
  if (reportId && optionalInteger(reportId, 1) === undefined) {
    ElMessage.warning('报告编号必须是正整数')
    return false
  }

  const reportType = filters.reportType.trim()
  if (reportType && optionalInteger(reportType, 0) === undefined) {
    ElMessage.warning('报告类型必须是非负整数')
    return false
  }
  return true
}

const handleSearch = () => {
  if (!validateFilters()) return
  showAdvancedFilters.value = false
  pagination.page = 1
  fetchSummaries()
}

const handleReset = () => {
  filters.dateRange = []
  filters.createDateRange = []
  filters.reportId = ''
  filters.sellerFinanceName = ''
  filters.reportType = ''
  filters.currency = ''
  showAdvancedFilters.value = false
  pagination.page = 1
  pagination.pageSize = 20
  fetchSummaries()
}

const handleSizeChange = () => {
  pagination.page = 1
  fetchSummaries()
}

const handleExport = async () => {
  if (!validateFilters()) return
  const query = buildExportQuery()
  if (!query) return

  exporting.value = true
  try {
    const content = await financialReportSummaryApi.export(query)
    downloadExcel(content, 'WB财务报告周汇总')
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

const formatDateTime = (value?: string): string => {
  if (!value) return '-'
  return value.replace('T', ' ').replace(/(\.\d+)?([+-]\d{2}:\d{2}|Z)$/, '')
}

onMounted(async () => {
  try {
    await fetchShops()
    if (filters.shopId) {
      await fetchSummaries()
    }
  } catch {
    // 请求拦截器统一展示错误信息
  }
})
</script>

<style scoped lang="scss">
.financial-report-summary-list {
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

    .currency-input {
      width: 120px;
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
