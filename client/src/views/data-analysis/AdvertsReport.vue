<template>
  <div class="adverts-report">
    <AnalyticsPageHeader
      title="Wildberries 广告周报"
      description="按店铺、周度和广告查看曝光、点击、转化及花费表现"
    />
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span>广告列表</span>
            <span class="record-count">共 {{ total }} 条</span>
          </div>
          <el-button type="success" :loading="exportLoading" @click="handleExport">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
        </div>
      </template>

      <!-- 搜索区域 -->
      <el-form :model="searchForm" inline class="search-form">
        <el-form-item label="店铺">
          <el-select v-model="searchForm.shop_id" placeholder="请选择店铺" clearable style="width: 200px" @change="handleShopChange">
            <el-option
              v-for="shop in shopList"
              :key="shop.id"
              :label="shop.name"
              :value="shop.id"
              :disabled="shop.platform !== 'wildberries'"
            >
              <span class="shop-option">
                <span class="shop-option-name">{{ shop.name }}</span>
                <el-tag
                  :type="shop.platform === 'ozon' ? 'primary' : 'warning'"
                  effect="plain"
                  size="small"
                >
                  {{ shop.platform === 'ozon' ? 'Ozon（当前不支持）' : 'WB' }}
                </el-tag>
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="周度">
          <el-select v-model="searchForm.week" placeholder="请选择周度" clearable style="width: 200px">
            <el-option
              v-for="week in availableWeeks"
              :key="week"
              :label="week"
              :value="week"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="广告ID">
          <el-input-number v-model="searchForm.advert_id" :min="1" placeholder="请输入广告ID" clearable style="width: 200px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.advert_status" placeholder="请选择状态" clearable style="width: 200px">
            <el-option label="已删除" :value="-1" />
            <el-option label="待启动" :value="4" />
            <el-option label="进行中" :value="9" />
            <el-option label="已完成" :value="7" />
            <el-option label="已拒绝" :value="8" />
            <el-option label="已暂停" :value="11" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="shop_id" label="店铺ID" width="90" fixed />
        <el-table-column label="店铺名称" min-width="140" fixed show-overflow-tooltip>
          <template #default="{ row }">{{ getShopName(row.shop_id) }}</template>
        </el-table-column>
        <el-table-column prop="week" label="周度" width="130" fixed />
        <el-table-column prop="advert_id" label="广告ID" width="100" />
        <el-table-column prop="advert_name" label="广告名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="advert_status_label" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.advert_status)" size="small">
              {{ getStatusLabel(row.advert_status, row.advert_status_label) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="paid_views" label="付费曝光" width="110" align="right">
          <template #default="{ row }">
            {{ row.paid_views?.toLocaleString() ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="paid_clicks" label="付费点击" width="110" align="right">
          <template #default="{ row }">
            {{ row.paid_clicks?.toLocaleString() ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="ctr" label="CTR(%)" width="90" align="right">
          <template #default="{ row }">
            {{ row.ctr !== null && row.ctr !== undefined ? row.ctr.toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="cpc" label="CPC" width="90" align="right">
          <template #default="{ row }">
            {{ row.cpc !== null && row.cpc !== undefined ? row.cpc.toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="atbs" label="加购" width="90" align="right">
          <template #default="{ row }">
            {{ row.atbs?.toLocaleString() ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="orders" label="订单" width="90" align="right">
          <template #default="{ row }">
            {{ row.orders?.toLocaleString() ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="cr" label="CR(%)" width="90" align="right">
          <template #default="{ row }">
            {{ row.cr !== null && row.cr !== undefined ? row.cr.toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="sum_cost" label="花费" width="120" align="right">
          <template #default="{ row }">
            {{ row.sum_cost !== null && row.sum_cost !== undefined ? row.sum_cost.toFixed(2) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="sum_price" label="GMV" width="120" align="right">
          <template #default="{ row }">
            {{ row.sum_price !== null && row.sum_price !== undefined ? row.sum_price.toFixed(2) : '-' }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="searchForm.page"
          v-model:page-size="searchForm.page_size"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="handleCurrentPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Download, Refresh } from '@element-plus/icons-vue'
import AnalyticsPageHeader from '@/components/analytics/AnalyticsPageHeader.vue'
import { wildberriesApi, type AdvertsReportDetail } from '@/api/modules/wildberries'
import { shopApi, type Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'

const loading = ref(false)
const exportLoading = ref(false)
const shopList = ref<Shop[]>([])
const availableWeeks = ref<string[]>([])
const tableData = ref<AdvertsReportDetail[]>([])
const total = ref(0)
let dataRequestId = 0
let weeksRequestId = 0
const route = useRoute()

const searchForm = reactive({
  shop_id: undefined as number | undefined,
  week: undefined as string | undefined,
  advert_id: undefined as number | undefined,
  advert_status: undefined as number | undefined,
  page: 1,
  page_size: 20
})

function hydrateRouteFilters() {
  const value = route.query.shop_id
  const shopId = Number(typeof value === 'string' ? value : '')
  if (shopId > 0) searchForm.shop_id = shopId
}

const fetchShops = async () => {
  try {
    shopList.value = await shopApi.list()
  } catch (error) {
    // 错误已由 request 拦截器处理
  }
}

const getShopName = (shopId: number): string =>
  shopList.value.find((shop) => shop.id === shopId)?.name ?? '-'

const fetchAvailableWeeks = async () => {
  const requestId = ++weeksRequestId
  try {
    const weeks = await wildberriesApi.getAvailableWeeks(searchForm.shop_id)
    if (requestId === weeksRequestId) {
      availableWeeks.value = weeks
    }
  } catch (error) {
    // 错误已由 request 拦截器处理
  }
}

const fetchData = async () => {
  const requestId = ++dataRequestId
  loading.value = true
  try {
    const response = await wildberriesApi.getAdvertsReport({
      shop_id: searchForm.shop_id,
      week: searchForm.week,
      advert_id: searchForm.advert_id,
      advert_status: searchForm.advert_status,
      page: searchForm.page,
      page_size: searchForm.page_size
    })
    if (requestId === dataRequestId) {
      tableData.value = response.items
      total.value = response.total
    }
  } catch (error) {
    // 错误已由 request 拦截器处理
  } finally {
    if (requestId === dataRequestId) {
      loading.value = false
    }
  }
}

const handleSearch = () => {
  searchForm.page = 1
  fetchData()
}

const handlePageSizeChange = () => {
  searchForm.page = 1
  fetchData()
}

const handleCurrentPageChange = () => {
  fetchData()
}

const handleReset = () => {
  searchForm.shop_id = undefined
  searchForm.week = undefined
  searchForm.advert_id = undefined
  searchForm.advert_status = undefined
  searchForm.page = 1
  Promise.all([fetchAvailableWeeks(), fetchData()])
}

const handleExport = async () => {
  exportLoading.value = true
  try {
    const blob = await wildberriesApi.exportExcel({
      shop_id: searchForm.shop_id,
      week: searchForm.week,
      advert_id: searchForm.advert_id,
      advert_status: searchForm.advert_status
    })

    downloadExcel(blob, 'WB广告周报')

    ElMessage.success('导出成功')
  } catch (error) {
    // 错误已由 request 拦截器处理
  } finally {
    exportLoading.value = false
  }
}

// 监听店铺变化，刷新可用周度
const handleShopChange = async () => {
  searchForm.week = undefined
  searchForm.page = 1
  await Promise.all([fetchAvailableWeeks(), fetchData()])
}

// 状态映射
const STATUS_MAP: Record<number, { label: string; type: string }> = {
  [-1]: { label: '已删除', type: 'danger' },
  4: { label: '待启动', type: 'warning' },
  7: { label: '已完成', type: 'info' },
  8: { label: '已拒绝', type: 'danger' },
  9: { label: '进行中', type: 'success' },
  11: { label: '已暂停', type: 'info' }
}

const getStatusLabel = (status: number | null, fallbackLabel: string | null) => {
  if (status !== null && status !== undefined && STATUS_MAP[status]) {
    return STATUS_MAP[status].label
  }
  return fallbackLabel || '-'
}

const getStatusTagType = (status: number | null) => {
  if (status !== null && status !== undefined && STATUS_MAP[status]) {
    return STATUS_MAP[status].type as 'success' | 'warning' | 'danger' | 'info'
  }
  return 'info'
}

onMounted(async () => {
  hydrateRouteFilters()
  await Promise.all([fetchShops(), fetchAvailableWeeks(), fetchData()])
})
</script>

<style scoped lang="scss">
.adverts-report {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .record-count {
      margin-left: 12px;
      color: var(--el-text-color-secondary);
      font-size: 13px;
      font-weight: 400;
    }
  }

  .search-form {
    margin-bottom: 20px;
  }

  .shop-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;

    .shop-option-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
