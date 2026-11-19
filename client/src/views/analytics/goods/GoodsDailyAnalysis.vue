<template>
  <div class="analysis-page">
    <el-card shadow="never" class="heading-card">
      <div class="heading">
        <div>
          <h2>商品日分析</h2>
          <p>按平台、店铺、商品和日期汇总流量、订单、退货与广告经营数据。</p>
        </div>
        <div class="heading-side">
          <el-radio-group v-model="platform" @change="changePlatform">
            <el-radio-button value="ozon">Ozon</el-radio-button>
            <el-radio-button value="wildberries">Wildberries</el-radio-button>
          </el-radio-group>
          <div class="updated">数据更新时间：{{ formatDateTime(summary?.updated_at) }}</div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" label-width="84px">
        <el-row :gutter="14">
          <el-col :xs="24" :sm="12" :lg="4"><el-form-item label="店铺"><PlatformShopSelect :key="platform" v-model="filters.shop_id" :platform="platform" @update:model-value="search" @shops-loaded="shops = $event" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="7"><el-form-item label="日期范围"><el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="4"><el-form-item :label="productIdLabel"><el-input-number v-model="filters.product_id" :controls="false" :min="1" clearable /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="4"><el-form-item label="卖家货号"><el-input v-model.trim="filters.seller_code" clearable @keyup.enter="search" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="5"><el-form-item label-width="0" class="actions"><el-button type="primary" :icon="Search" @click="search">查询</el-button><el-button :icon="RefreshLeft" @click="reset">重置</el-button></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="5"><el-form-item label="数据状态"><el-select v-model="filters.data_status" clearable placeholder="全部"><el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="5"><el-form-item label="异常筛选"><el-select v-model="filters.anomaly" clearable placeholder="全部"><el-option v-for="item in anomalyOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :sm="24" :lg="9"><el-form-item label="商品关键词"><el-input v-model.trim="filters.keyword" :placeholder="platform === 'ozon' ? '商品名称或品类' : '商品名称、品牌或品类'" clearable @keyup.enter="search" /></el-form-item></el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-alert v-if="summary?.metrics.has_currency_conflict" title="当前筛选结果存在混币或币种缺失，金额合计仅供核查，请缩小店铺范围。" type="warning" :closable="false" show-icon class="notice" />
    <el-alert v-if="platform === 'ozon' && trafficUnavailable" title="当前结果未取得 Ozon 流量指标，流量字段显示“未返回”，不代表实际为 0。" type="info" :closable="false" show-icon class="notice" />
    <el-alert v-if="platform === 'wildberries' && clickScopeConflict" title="当前结果存在广告点击大于商品总点击的口径冲突；估算自然点击仅供核查，不代表平台直接返回值。" type="warning" :closable="false" show-icon class="notice" />

    <div class="kpi-grid" v-loading="summaryLoading">
      <el-card v-for="card in kpiCards" :key="card.label" shadow="never" class="kpi-card"><div class="kpi-label">{{ card.label }}</div><div class="kpi-value">{{ card.value }}</div><div class="kpi-note">{{ card.note }}</div></el-card>
    </div>

    <div class="chart-grid">
      <el-card shadow="never"><template #header><strong>商品经营趋势</strong></template><VChart class="chart" :option="trendOption" autoresize /></el-card>
      <el-card shadow="never"><template #header><div class="chart-header"><div><strong>商品经营排行</strong><span class="chart-hint">点击横柱查看商品信息</span></div><el-select v-model="rankingMetric" size="small" style="width: 135px" @change="fetchSummary"><el-option v-for="item in rankingOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></div></template><VChart class="chart ranking-chart" :option="rankingOption" autoresize @click="openRankingDetail" /></el-card>
    </div>

    <el-card shadow="never" class="table-card">
      <template #header><div class="table-header"><div><strong>商品日明细</strong><span>共 {{ total }} 条，已选 {{ selected.length }} 条</span></div><div class="table-actions"><el-popover placement="bottom-end" :width="240" trigger="click"><template #reference><el-button :icon="Setting">列设置</el-button></template><el-checkbox-group v-model="extraColumns" class="column-settings"><el-checkbox label="category">商品品类</el-checkbox><el-checkbox v-if="platform === 'wildberries'" label="ratings">评分</el-checkbox><el-checkbox label="funnel">漏斗指标</el-checkbox><el-checkbox label="traffic">流量指标</el-checkbox><el-checkbox v-if="platform === 'wildberries'" label="returns">退货状态</el-checkbox><el-checkbox v-else label="fees">退货费用</el-checkbox></el-checkbox-group></el-popover><el-dropdown split-button type="success" :loading="exporting" @click="exportRows('filtered')" @command="exportRows"><span>导出</span><template #dropdown><el-dropdown-menu><el-dropdown-item command="filtered">导出筛选结果（最多5万行）</el-dropdown-item><el-dropdown-item command="selected" :disabled="!selected.length">导出已选（{{ selected.length }}）</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div></div></template>
      <el-table ref="tableRef" v-loading="loading" :data="rows" :row-key="rowKey" border stripe height="560" @selection-change="selected = $event">
        <el-table-column type="selection" width="48" fixed="left" reserve-selection />
        <el-table-column label="操作" width="70" fixed="left"><template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">详情</el-button></template></el-table-column>
        <el-table-column label="基础信息">
          <el-table-column prop="stat_date" label="日期" width="112" />
          <el-table-column prop="shop_id" label="店铺ID" width="92" />
          <el-table-column label="店铺名称" min-width="140" show-overflow-tooltip><template #default="{ row }">{{ shopName(row.shop_id) }}</template></el-table-column>
          <el-table-column prop="product_id" :label="productIdLabel" width="130" />
          <el-table-column prop="seller_code" label="货号" min-width="130" show-overflow-tooltip />
          <el-table-column prop="product_name" label="商品名称" min-width="210" show-overflow-tooltip />
          <el-table-column v-if="extraColumns.includes('category')" prop="category_name" label="品类" min-width="150" show-overflow-tooltip />
          <el-table-column v-if="platform === 'wildberries' && extraColumns.includes('ratings')" label="商品/评论评分" width="125"><template #default="{ row }">{{ metric(row.product_rating) }} / {{ metric(row.feedback_rating) }}</template></el-table-column>
        </el-table-column>
        <el-table-column label="订单交易">
          <el-table-column prop="order_qty" label="下单件数" width="95" />
          <el-table-column :label="platform === 'ozon' ? '销售金额' : '折后订单金额'" width="130"><template #default="{ row }">{{ money(row.sales_amount, row.sales_currency) }}</template></el-table-column>
          <el-table-column v-if="platform === 'wildberries'" label="取消率" width="90"><template #default="{ row }">{{ percent(row.order_cancel_rate) }}</template></el-table-column>
        </el-table-column>
        <el-table-column label="退货售后">
          <el-table-column prop="return_qty" label="退货件数" width="95" />
          <el-table-column label="退货率" width="92"><template #default="{ row }">{{ percent(row.return_rate) }}</template></el-table-column>
          <el-table-column v-if="platform === 'ozon' && extraColumns.includes('fees')" label="仓储/销毁费" width="150"><template #default="{ row }">{{ metric(rawValue(row, 'storage_fee_sum')) }} / {{ metric(rawValue(row, 'utilization_fee_sum')) }}</template></el-table-column>
          <el-table-column v-if="platform === 'wildberries' && extraColumns.includes('returns')" label="准备/领取/过期" width="145"><template #default="{ row }">{{ rawValue(row, 'return_ready_cnt') }} / {{ rawValue(row, 'return_completed_cnt') }} / {{ rawValue(row, 'return_expired_cnt') }}</template></el-table-column>
        </el-table-column>
        <el-table-column v-if="extraColumns.includes('funnel')" label="销售漏斗">
          <el-table-column label="漏斗下单" width="100"><template #default="{ row }">{{ sourceMetric(row.has_funnel_data, row.funnel_order_qty) }}</template></el-table-column>
          <el-table-column v-if="platform === 'wildberries'" label="售出件数" width="95"><template #default="{ row }">{{ sourceMetric(row.has_funnel_data, row.funnel_buyout_qty) }}</template></el-table-column>
          <el-table-column label="漏斗金额" width="110"><template #default="{ row }">{{ sourceMetric(row.has_funnel_data, row.funnel_amount) }}</template></el-table-column>
        </el-table-column>
        <el-table-column v-if="extraColumns.includes('traffic')" label="流量表现">
          <el-table-column :label="platform === 'ozon' ? '浏览' : '商品点击'" width="95"><template #default="{ row }">{{ sourceMetric(row.has_traffic_data, row.traffic_primary) }}</template></el-table-column>
          <el-table-column :label="platform === 'ozon' ? '访问' : '收藏'" width="85"><template #default="{ row }">{{ sourceMetric(row.has_traffic_data, row.traffic_secondary) }}</template></el-table-column>
          <el-table-column label="加购" width="85"><template #default="{ row }">{{ sourceMetric(row.has_traffic_data, row.traffic_cart) }}</template></el-table-column>
        </el-table-column>
        <el-table-column label="广告表现">
          <el-table-column label="曝光" width="90"><template #default="{ row }">{{ sourceMetric(row.has_ad_data, row.ad_views) }}</template></el-table-column>
          <el-table-column label="点击" width="85"><template #default="{ row }">{{ sourceMetric(row.has_ad_data, row.ad_clicks) }}</template></el-table-column>
          <el-table-column label="加购" width="85"><template #default="{ row }">{{ sourceMetric(row.has_ad_data, row.ad_to_cart) }}</template></el-table-column>
          <el-table-column label="广告花费" width="115"><template #default="{ row }">{{ sourceMetric(row.has_ad_data, row.ad_spend) }}</template></el-table-column>
          <el-table-column label="ROAS" width="85"><template #default="{ row }">{{ sourceMetric(row.has_ad_data, row.ad_roas) }}</template></el-table-column>
        </el-table-column>
        <el-table-column label="数据状态" width="160"><template #default="{ row }"><div class="tags"><el-tag v-if="row.has_order_data" size="small">订单</el-tag><el-tag v-if="row.has_return_data" size="small" type="warning">退货</el-tag><el-tag v-if="row.has_funnel_data" size="small" type="success">漏斗</el-tag><el-tag v-if="row.has_ad_data" size="small" type="danger">广告</el-tag></div></template></el-table-column>
      </el-table>
      <div class="pagination"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20, 50, 100]" :total="total" layout="total, sizes, prev, pager, next, jumper" @size-change="search" @current-change="fetchRows" /></div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="`${platformName} 商品日分析详情`" size="760px">
      <template v-if="current"><section v-for="group in detailGroups" :key="group.title" class="detail-group"><h3>{{ group.title }}</h3><el-descriptions :column="2" border><el-descriptions-item v-for="field in group.fields" :key="field.key" :label="field.label">{{ detailValue(field.key) }}</el-descriptions-item></el-descriptions></section><div class="drill-actions"><el-button type="primary" plain @click="goOrders">查看来源订单</el-button><el-button type="warning" plain @click="goReturns">查看来源退货</el-button><el-button type="success" plain @click="goFunnel">查看销售漏斗</el-button><el-button type="danger" plain @click="goAdverts">查看广告效率</el-button></div></template>
    </el-drawer>

    <el-drawer v-model="rankingDrawerVisible" :title="`${platformName} 商品经营详情`" size="760px">
      <div v-loading="rankingDetailLoading" class="ranking-detail">
        <template v-if="rankingDetail">
          <section class="detail-group">
            <h3>商品信息</h3>
            <el-descriptions :column="2" border>
              <el-descriptions-item :label="productIdLabel">{{ rankingDetail.product_id }}</el-descriptions-item>
              <el-descriptions-item label="卖家货号">{{ display(rankingDetail.seller_code) }}</el-descriptions-item>
              <el-descriptions-item label="商品名称（中文）">{{ display(rankingDetail.product_name_cn) }}</el-descriptions-item>
              <el-descriptions-item label="商品名称">{{ display(rankingDetail.product_name) }}</el-descriptions-item>
              <el-descriptions-item v-if="platform === 'wildberries'" label="品牌">{{ display(rankingDetail.brand_name) }}</el-descriptions-item>
              <el-descriptions-item label="品类（中文）">{{ display(rankingDetail.category_name_cn) }}</el-descriptions-item>
              <el-descriptions-item label="品类">{{ display(rankingDetail.category_name) }}</el-descriptions-item>
              <el-descriptions-item label="统计周期">{{ rankingDetail.period_from }} 至 {{ rankingDetail.period_to }}</el-descriptions-item>
            </el-descriptions>
          </section>
          <section class="detail-group">
            <h3>周期经营指标</h3>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="销售金额">{{ number(rankingDetail.metrics.sales_amount) }}</el-descriptions-item>
              <el-descriptions-item label="下单件数">{{ number(rankingDetail.metrics.order_qty) }}</el-descriptions-item>
              <el-descriptions-item label="退货件数">{{ number(rankingDetail.metrics.return_qty) }}</el-descriptions-item>
              <el-descriptions-item label="退货率">{{ percent(rankingDetail.metrics.return_rate) }}</el-descriptions-item>
              <el-descriptions-item label="广告花费">{{ number(rankingDetail.metrics.ad_spend) }}</el-descriptions-item>
              <el-descriptions-item label="广告归因销售额">{{ number(rankingDetail.metrics.ad_attributed_sales) }}</el-descriptions-item>
              <el-descriptions-item label="ROAS">{{ metric(rankingDetail.metrics.ad_roas) }}</el-descriptions-item>
            </el-descriptions>
          </section>
          <section class="detail-group">
            <h3>所属店铺</h3>
            <el-table :data="rankingDetail.shops" border size="small">
              <el-table-column prop="shop_id" label="店铺ID" width="90" />
              <el-table-column label="店铺名称" min-width="150"><template #default="{ row }">{{ display(row.shop_name) }}</template></el-table-column>
              <el-table-column label="销售金额" width="120"><template #default="{ row }">{{ number(row.metrics.sales_amount) }}</template></el-table-column>
              <el-table-column label="下单件数" width="95"><template #default="{ row }">{{ number(row.metrics.order_qty) }}</template></el-table-column>
              <el-table-column label="退货率" width="90"><template #default="{ row }">{{ percent(row.metrics.return_rate) }}</template></el-table-column>
            </el-table>
          </section>
          <div class="drill-actions"><el-button type="primary" plain @click="goRankingOrders">查看来源订单</el-button><el-button type="warning" plain @click="goRankingReturns">查看来源退货</el-button><el-button type="success" plain @click="goRankingFunnel">查看销售漏斗</el-button><el-button type="danger" plain @click="goRankingAdverts">查看广告效率</el-button></div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type TableInstance } from 'element-plus'
import { RefreshLeft, Search, Setting } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import PlatformShopSelect from '@/components/PlatformShopSelect.vue'
import type { Shop } from '@/api/modules/shop'
import { downloadExcel } from '@/utils/download'
import { ozonGoodsDailyAnalysisApi, type ExportScope, type GoodsDailyFilters, type GoodsDailySummary, type GoodsPeriodMetrics, type GoodsProductShopDetail, type OzonGoodsDailyItem, type OzonGoodsProductDetail, type RankingMetric } from '@/api/modules/ozonGoodsDailyAnalysis'
import { wbGoodsDailyAnalysisApi, type WBGoodsDailyFilters, type WBGoodsDailyItem, type WBGoodsDailySummary, type WBGoodsProductDetail } from '@/api/modules/wbGoodsDailyAnalysis'

use([CanvasRenderer, BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent])
type Platform = 'ozon' | 'wildberries'
type RawRow = OzonGoodsDailyItem | WBGoodsDailyItem
interface Filters { shop_id?: number; product_id?: number; seller_code?: string; keyword?: string; data_status?: string; anomaly?: string; sort_order: 'asc' | 'desc' }
interface UnifiedRow { stat_date: string; shop_id: number; product_id: number; seller_code: string | null; product_name: string | null; category_name: string | null; product_rating: unknown; feedback_rating: unknown; has_order_data: boolean; has_return_data: boolean; has_funnel_data: boolean; has_traffic_data: boolean; has_ad_data: boolean; order_qty: number; sales_amount: unknown; sales_currency: string | null; order_cancel_rate: unknown; return_qty: number; return_rate: unknown; funnel_order_qty: number | null; funnel_buyout_qty: number | null; funnel_amount: unknown; traffic_primary: number | null; traffic_secondary: number | null; traffic_cart: number | null; ad_views: number | null; ad_clicks: number | null; ad_to_cart: number | null; ad_spend: unknown; ad_roas: unknown; click_scope_conflict: boolean; raw: RawRow }
interface UnifiedRanking { product_id: number; seller_code: string | null; product_name: string | null; product_name_cn: string | null; sales_amount: unknown; order_qty: number; return_qty: number; return_rate: unknown; ad_spend: unknown; ad_roas: unknown }
interface UnifiedSummary { metrics: GoodsDailySummary['metrics']; trend: GoodsDailySummary['trend']; ranking: UnifiedRanking[]; updated_at: string | null }
interface UnifiedProductDetail { product_id: number; seller_code: string | null; product_name: string | null; product_name_cn: string | null; brand_name: string | null; category_name: string | null; category_name_cn: string | null; period_from: string; period_to: string; metrics: GoodsPeriodMetrics; shops: GoodsProductShopDetail[] }
interface RankingClickParams { dataIndex?: number; seriesType?: string }

const route = useRoute(), router = useRouter()
const platform = ref<Platform>(route.query.platform === 'wildberries' ? 'wildberries' : 'ozon')
const loading = ref(false), summaryLoading = ref(false), exporting = ref(false)
const rows = ref<UnifiedRow[]>([]), selected = ref<UnifiedRow[]>([]), shops = ref<Shop[]>([])
const summary = ref<UnifiedSummary>(), current = ref<UnifiedRow>(), drawerVisible = ref(false)
const rankingDetail = ref<UnifiedProductDetail>(), rankingDrawerVisible = ref(false), rankingDetailLoading = ref(false)
const page = ref(1), pageSize = ref(20), total = ref(0), tableRef = ref<TableInstance>()
const rankingMetric = ref<RankingMetric>('sales_amount'), extraColumns = ref<string[]>(['funnel'])
const filters = reactive<Filters>({ sort_order: 'desc' })
const dateRange = ref<[string, string]>(defaultRange())
let rowsRequestId = 0
let summaryRequestId = 0
const platformName = computed(() => platform.value === 'ozon' ? 'Ozon' : 'WB')
const productIdLabel = computed(() => platform.value === 'ozon' ? 'Ozon SKU' : 'WB 商品ID')
const commonStatuses = [{ label: '有订单数据', value: 'has_orders' }, { label: '有退货数据', value: 'has_returns' }, { label: '有漏斗数据', value: 'has_funnel' }, { label: '有广告数据', value: 'has_ad' }]
const statusOptions = computed(() => platform.value === 'ozon' ? [...commonStatuses, { label: '流量指标已返回', value: 'has_traffic' }] : commonStatuses)
const commonAnomalies = [{ label: '有广告花费但无归因订单', value: 'ad_spend_no_orders' }, { label: '高退货率（≥20%）', value: 'high_return_rate' }, { label: '有点击无加购', value: 'clicks_no_cart' }, { label: '有加购无订单', value: 'cart_no_orders' }]
const anomalyOptions = computed(() => platform.value === 'ozon' ? commonAnomalies : [...commonAnomalies, { label: '高取消率（≥20%）', value: 'high_cancel_rate' }, { label: '广告点击大于商品总点击', value: 'click_scope_conflict' }, { label: '广告金额存在混币', value: 'ad_currency_conflict' }])
const rankingOptions = [{ label: '订单金额', value: 'sales_amount' }, { label: '下单件数', value: 'order_qty' }, { label: '广告花费', value: 'ad_spend' }, { label: 'ROAS', value: 'ad_roas' }, { label: '退货率', value: 'return_rate' }]

function ymd(value: Date) { return value.toISOString().slice(0, 10) }
function defaultRange(): [string, string] { const end = new Date(); const start = new Date(); start.setDate(end.getDate() - 29); return [ymd(start), ymd(end)] }
function ozonFilters(): GoodsDailyFilters { return { shop_id: filters.shop_id, date_from: dateRange.value?.[0], date_to: dateRange.value?.[1], sku: filters.product_id, offer_id: filters.seller_code, keyword: filters.keyword, data_status: filters.data_status as GoodsDailyFilters['data_status'], anomaly: filters.anomaly as GoodsDailyFilters['anomaly'], sort_order: filters.sort_order } }
function wbFilters(): WBGoodsDailyFilters { return { shop_id: filters.shop_id, date_from: dateRange.value?.[0], date_to: dateRange.value?.[1], nm_id: filters.product_id, vendor_code: filters.seller_code, keyword: filters.keyword, data_status: filters.data_status as WBGoodsDailyFilters['data_status'], anomaly: filters.anomaly as WBGoodsDailyFilters['anomaly'], sort_order: filters.sort_order } }
function normalizeOzon(row: OzonGoodsDailyItem): UnifiedRow { return { stat_date: row.stat_date, shop_id: row.shop_id, product_id: row.sku, seller_code: row.offer_id, product_name: row.product_name_cn || row.product_name, category_name: row.category_name_cn || row.category_name, product_rating: null, feedback_rating: null, has_order_data: row.order_qty > 0, has_return_data: row.return_qty > 0, has_funnel_data: row.has_funnel_data, has_traffic_data: row.has_traffic_metrics, has_ad_data: row.has_ad_data, order_qty: row.order_qty, sales_amount: row.sales_amount_sum, sales_currency: row.sales_currency, order_cancel_rate: row.order_qty ? row.cancelled_qty / row.order_qty : null, return_qty: row.return_qty, return_rate: row.return_rate_ordered, funnel_order_qty: row.funnel_ordered_units, funnel_buyout_qty: null, funnel_amount: row.funnel_revenue, traffic_primary: row.traffic_views, traffic_secondary: row.traffic_visitors, traffic_cart: row.traffic_to_cart, ad_views: row.ad_views, ad_clicks: row.ad_clicks, ad_to_cart: row.ad_to_cart, ad_spend: row.ad_spend_amount, ad_roas: row.ad_roas, click_scope_conflict: false, raw: row } }
function normalizeWB(row: WBGoodsDailyItem): UnifiedRow { return { stat_date: row.stat_date, shop_id: row.shop_id, product_id: row.nm_id, seller_code: row.vendor_code, product_name: row.product_title_cn || row.product_title, category_name: row.subject_name_cn || row.subject_name, product_rating: row.product_rating, feedback_rating: row.feedback_rating, has_order_data: row.has_order_data, has_return_data: row.has_return_data, has_funnel_data: row.has_funnel_data, has_traffic_data: row.has_funnel_data, has_ad_data: row.has_ad_data, order_qty: row.order_qty, sales_amount: row.order_amount_sum, sales_currency: null, order_cancel_rate: row.order_cancel_rate, return_qty: row.return_qty, return_rate: row.return_rate_ordered, funnel_order_qty: row.funnel_order_qty, funnel_buyout_qty: row.funnel_buyout_qty, funnel_amount: row.funnel_order_amount, traffic_primary: row.traffic_clicks, traffic_secondary: row.traffic_wishlist_qty, traffic_cart: row.traffic_cart_qty, ad_views: row.ad_views, ad_clicks: row.ad_clicks, ad_to_cart: row.ad_to_cart, ad_spend: row.ad_spend_amount, ad_roas: row.ad_roas, click_scope_conflict: row.has_click_scope_conflict, raw: row } }
function normalizeSummary(value: GoodsDailySummary | WBGoodsDailySummary): UnifiedSummary { const ranking = value.ranking.map((item) => 'sku' in item ? { product_id: item.sku, seller_code: item.offer_id, product_name: item.product_name, product_name_cn: item.product_name_cn, sales_amount: item.sales_amount, order_qty: item.order_qty, return_qty: item.return_qty, return_rate: item.return_rate, ad_spend: item.ad_spend, ad_roas: item.ad_roas } : { product_id: item.nm_id, seller_code: item.vendor_code, product_name: item.product_title, product_name_cn: item.product_title_cn, sales_amount: item.sales_amount, order_qty: item.order_qty, return_qty: item.return_qty, return_rate: item.return_rate, ad_spend: item.ad_spend, ad_roas: item.ad_roas }); return { metrics: value.metrics, trend: value.trend, ranking, updated_at: value.updated_at } }
function normalizeProductDetail(value: OzonGoodsProductDetail | WBGoodsProductDetail): UnifiedProductDetail { return 'sku' in value ? { product_id: value.sku, seller_code: value.offer_id, product_name: value.product_name, product_name_cn: value.product_name_cn, brand_name: null, category_name: value.category_name, category_name_cn: value.category_name_cn, period_from: value.period_from, period_to: value.period_to, metrics: value.metrics, shops: value.shops } : { product_id: value.nm_id, seller_code: value.vendor_code, product_name: value.product_title, product_name_cn: value.product_title_cn, brand_name: value.brand_name, category_name: value.subject_name, category_name_cn: value.subject_name_cn, period_from: value.period_from, period_to: value.period_to, metrics: value.metrics, shops: value.shops } }
async function fetchRows() { const requestId = ++rowsRequestId; loading.value = true; try { if (platform.value === 'ozon') { const result = await ozonGoodsDailyAnalysisApi.list({ ...ozonFilters(), page: page.value, page_size: pageSize.value }); if (requestId !== rowsRequestId) return; rows.value = result.items.map(normalizeOzon); total.value = result.total } else { const result = await wbGoodsDailyAnalysisApi.list({ ...wbFilters(), page: page.value, page_size: pageSize.value }); if (requestId !== rowsRequestId) return; rows.value = result.items.map(normalizeWB); total.value = result.total } } catch { if (requestId === rowsRequestId) ElMessage.error(`${platformName.value} 商品日分析加载失败`) } finally { if (requestId === rowsRequestId) loading.value = false } }
async function fetchSummary() { const requestId = ++summaryRequestId; summaryLoading.value = true; try { const result = platform.value === 'ozon' ? await ozonGoodsDailyAnalysisApi.summary({ ...ozonFilters(), ranking_metric: rankingMetric.value }) : await wbGoodsDailyAnalysisApi.summary({ ...wbFilters(), ranking_metric: rankingMetric.value }); if (requestId === summaryRequestId) summary.value = normalizeSummary(result) } catch { if (requestId === summaryRequestId) ElMessage.error(`${platformName.value} 商品日汇总加载失败`) } finally { if (requestId === summaryRequestId) summaryLoading.value = false } }
function search() { page.value = 1; tableRef.value?.clearSelection(); selected.value = []; void Promise.all([fetchRows(), fetchSummary()]) }
function reset() { filters.shop_id = undefined; filters.product_id = undefined; filters.seller_code = undefined; filters.keyword = undefined; filters.data_status = undefined; filters.anomaly = undefined; filters.sort_order = 'desc'; dateRange.value = defaultRange(); rankingMetric.value = 'sales_amount'; search() }
function changePlatform() { filters.shop_id = undefined; filters.product_id = undefined; filters.seller_code = undefined; filters.data_status = undefined; filters.anomaly = undefined; rows.value = []; selected.value = []; summary.value = undefined; current.value = undefined; drawerVisible.value = false; rankingDetail.value = undefined; rankingDrawerVisible.value = false; extraColumns.value = ['funnel']; void router.replace({ path: '/analytics/goods/daily', query: { platform: platform.value } }); search() }
async function exportRows(scope: ExportScope) { if (scope === 'selected' && !selected.value.length) return; exporting.value = true; try { let blob: Blob; if (platform.value === 'ozon') { const selected_keys = selected.value.map((row) => ({ stat_date: row.stat_date, shop_id: row.shop_id, sku: row.product_id })); blob = await ozonGoodsDailyAnalysisApi.export({ scope, filters: ozonFilters(), selected_keys }) } else { const selected_keys = selected.value.map((row) => ({ stat_date: row.stat_date, shop_id: row.shop_id, nm_id: row.product_id })); blob = await wbGoodsDailyAnalysisApi.export({ scope, filters: wbFilters(), selected_keys }) } downloadExcel(blob, `${platformName.value}商品日分析`); ElMessage.success('导出成功') } finally { exporting.value = false } }
function rowKey(row: UnifiedRow) { return `${platform.value}:${row.stat_date}:${row.shop_id}:${row.product_id}` }
function shopName(id: number) { return shops.value.find((shop) => shop.id === id)?.name || `店铺 ${id}` }
function number(value: unknown) { const n = Number(value || 0); return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }
function metric(value: unknown) { return value === null || value === undefined ? '—' : number(value) }
function display(value: unknown) { return value === null || value === undefined || value === '' ? '暂无数据' : String(value) }
function sourceMetric(hasSource: boolean, value: unknown) { return hasSource ? metric(value) : '未返回' }
function money(value: unknown, currency?: string | null) { return value === null || value === undefined ? '—' : `${number(value)}${currency ? ` ${currency}` : ''}` }
function percent(value: unknown) { return value === null || value === undefined ? '—' : `${(Number(value) * 100).toFixed(1)}%` }
function formatDateTime(value?: string | null) { return value ? value.replace('T', ' ').replace(/(Z|[+-]\d{2}:\d{2})$/, '') : '—' }
const trafficUnavailable = computed(() => rows.value.length > 0 && rows.value.every((row) => !row.has_traffic_data))
const clickScopeConflict = computed(() => rows.value.some((row) => row.click_scope_conflict))
const kpiCards = computed(() => { const m = summary.value?.metrics; if (!m) return []; return [
  { label: platform.value === 'ozon' ? '销售金额' : '折后订单金额', value: money(m.sales_amount, m.sales_currency), note: platform.value === 'ozon' ? '订单明细口径' : 'WB订单统计折后金额口径' },
  { label: '下单件数', value: number(m.order_qty), note: m.has_funnel_data ? `订单明细：${number(m.order_qty)}；漏斗：${number(m.funnel_order_qty)}；差异：${number(m.order_qty - m.funnel_order_qty)}` : '订单明细口径；漏斗数据未返回' },
  { label: '退货件数 / 退货率', value: `${number(m.return_qty)} / ${percent(m.return_rate)}`, note: '退货件数 ÷ 下单件数' },
  { label: '广告花费', value: money(m.ad_spend, m.ad_currency), note: '广告数据口径' },
  { label: '广告归因销售额', value: number(m.ad_attributed_sales), note: '广告归因口径' },
  { label: 'ROAS / DRR', value: `${metric(m.ad_roas)} / ${percent(m.ad_drr)}`, note: '归因销售额与花费' }
] })
const trendOption = computed(() => ({ tooltip: { trigger: 'axis' }, legend: { top: 0 }, grid: { left: 24, right: 24, top: 42, bottom: 30, containLabel: true }, xAxis: { type: 'category', data: summary.value?.trend.map((x) => x.stat_date) || [] }, yAxis: [{ type: 'value', name: '金额' }, { type: 'value', name: '件数/比率' }], series: [
  { name: platform.value === 'ozon' ? '销售金额' : '折后订单金额', type: 'bar', data: summary.value?.trend.map((x) => Number(x.sales_amount)) || [] },
  { name: '广告花费', type: 'bar', data: summary.value?.trend.map((x) => Number(x.ad_spend)) || [] },
  { name: '下单件数', type: 'line', yAxisIndex: 1, data: summary.value?.trend.map((x) => x.order_qty) || [] },
  { name: '退货率', type: 'line', yAxisIndex: 1, data: summary.value?.trend.map((x) => Number(x.return_rate) * 100) || [] }
] }))
const rankingOption = computed(() => ({ tooltip: { trigger: 'axis' }, grid: { left: 100, right: 25, top: 15, bottom: 25 }, xAxis: { type: 'value' }, yAxis: { type: 'category', inverse: true, data: summary.value?.ranking.map((x) => x.seller_code || String(x.product_id)) || [] }, series: [{ type: 'bar', cursor: 'pointer', data: summary.value?.ranking.map((x) => Number(x[rankingMetric.value])) || [], itemStyle: { color: platform.value === 'ozon' ? '#409eff' : '#7b4fc9' } }] }))

async function openRankingDetail(params: RankingClickParams) { if (params.seriesType !== 'bar' || params.dataIndex === undefined) return; const ranking = summary.value?.ranking[params.dataIndex]; if (!ranking) return; rankingDetail.value = undefined; rankingDrawerVisible.value = true; rankingDetailLoading.value = true; try { if (platform.value === 'ozon') { const query = ozonFilters(); delete query.sku; rankingDetail.value = normalizeProductDetail(await ozonGoodsDailyAnalysisApi.productDetail(ranking.product_id, query)) } else { const query = wbFilters(); delete query.nm_id; rankingDetail.value = normalizeProductDetail(await wbGoodsDailyAnalysisApi.productDetail(ranking.product_id, query)) } } catch { rankingDrawerVisible.value = false; ElMessage.error(`${platformName.value} 商品经营详情加载失败`) } finally { rankingDetailLoading.value = false } }

interface DetailField { key: string; label: string }
const ozonGroups: Array<{ title: string; fields: DetailField[] }> = [
  { title: '商品信息', fields: [['stat_date', '统计日期'], ['shop_id', '店铺ID'], ['sku', 'Ozon SKU'], ['offer_id', '卖家货号'], ['product_name_cn', '商品名称（中文）'], ['product_name', '商品名称'], ['category_name_cn', '品类（中文）'], ['category_name', '品类']].map(field) },
  { title: '订单交易', fields: [['order_cnt', '发货单数'], ['order_line_cnt', '商品行数'], ['order_qty', '下单件数'], ['delivered_qty', '已送达件数'], ['cancelled_qty', '已取消件数'], ['sales_amount_sum', '销售金额'], ['sales_currency', '销售币种']].map(field) },
  { title: '退货售后', fields: [['return_cnt', '退货单数'], ['return_qty', '退货件数'], ['return_rate_ordered', '按下单件数退货率'], ['return_rate_delivered', '按送达件数退货率'], ['return_amount_sum', '退货金额'], ['storage_fee_sum', '仓储费'], ['utilization_fee_sum', '销毁费'], ['commission_amount_sum', '退货佣金']].map(field) },
  { title: '销售漏斗与流量', fields: [['has_funnel_data', '存在漏斗数据'], ['has_traffic_metrics', '流量指标已返回'], ['funnel_ordered_units', '漏斗下单件数'], ['funnel_revenue', '漏斗下单金额'], ['traffic_views', '浏览次数'], ['traffic_visitors', '访问用户'], ['traffic_to_cart', '加购次数'], ['traffic_cart_rate', '流量加购率']].map(field) },
  { title: '广告效率', fields: [['has_ad_data', '存在广告数据'], ['ad_campaign_cnt', '广告活动数'], ['ad_views', '广告展现'], ['ad_clicks', '广告点击'], ['ad_to_cart', '广告加购'], ['ad_spend_amount', '广告花费'], ['ad_attributed_order_cnt', '归因订单'], ['ad_attributed_sales_amount', '归因销售额'], ['ad_roas', 'ROAS'], ['ad_drr', 'DRR']].map(field) },
  { title: '数据质量', fields: [['has_currency_conflict', '金额存在混币或缺币种'], ['create_time', '创建时间'], ['update_time', '更新时间']].map(field) }
]
const wbGroups: Array<{ title: string; fields: DetailField[] }> = [
  { title: '商品信息', fields: [['stat_date', '统计日期'], ['shop_id', '店铺ID'], ['nm_id', 'WB商品ID'], ['vendor_code', '卖家货号'], ['product_title_cn', '商品名称（中文）'], ['product_title', '商品名称'], ['brand_name', '品牌'], ['subject_name_cn', '品类（中文）'], ['product_rating', '商品评分'], ['feedback_rating', '评论评分']].map(field) },
  { title: '订单交易', fields: [['order_cnt', '订单数'], ['order_qty', '下单件数'], ['cancelled_order_cnt', '取消订单数'], ['cancelled_qty', '取消件数'], ['order_amount_sum', '折后订单金额'], ['finished_amount_sum', '最终价格合计'], ['order_cancel_rate', '取消率']].map(field) },
  { title: '退货售后', fields: [['return_cnt', '退货记录数'], ['return_qty', '退货件数'], ['return_ready_cnt', '已准备退货数'], ['return_completed_cnt', '已领取退货数'], ['return_expired_cnt', '已过期退货数'], ['return_rate_ordered', '按下单件数退货率'], ['return_rate_buyout', '按售出件数退货率']].map(field) },
  { title: '销售漏斗与流量', fields: [['traffic_clicks', '商品点击'], ['traffic_cart_qty', '商品加购'], ['traffic_wishlist_qty', '商品收藏'], ['funnel_order_qty', '漏斗下单件数'], ['funnel_buyout_qty', '售出件数'], ['funnel_cancel_qty', '取消件数'], ['funnel_order_amount', '漏斗订单金额'], ['funnel_buyout_amount', '售出金额'], ['traffic_cart_rate', '加购率'], ['traffic_order_rate', '下单率'], ['traffic_buyout_rate', '售出率']].map(field) },
  { title: '广告效率', fields: [['ad_campaign_cnt', '广告活动数'], ['ad_views', '广告曝光'], ['ad_clicks', '广告点击'], ['ad_to_cart', '广告加购'], ['ad_order_cnt', '归因订单'], ['ad_sales_qty', '归因销量'], ['ad_spend_amount', '广告花费'], ['ad_attributed_sales_amount', '归因销售额'], ['ad_ctr', 'CTR'], ['ad_cvr', 'CVR'], ['ad_cpc', 'CPC'], ['ad_cpo', 'CPO'], ['ad_roas', 'ROAS'], ['ad_drr', 'DRR']].map(field) },
  { title: '数据质量', fields: [['has_ad_currency_conflict', '广告币种冲突'], ['has_click_scope_conflict', '点击口径冲突'], ['estimated_organic_clicks', '估算自然点击'], ['create_time', '创建时间'], ['update_time', '更新时间']].map(field) }
]
function field(value: string[]): DetailField { return { key: value[0], label: value[1] } }
const detailGroups = computed(() => platform.value === 'ozon' ? ozonGroups : wbGroups)
function rawValue(row: UnifiedRow, key: string): unknown { return (row.raw as unknown as Record<string, unknown>)[key] }
function openDetail(row: UnifiedRow) { current.value = row; drawerVisible.value = true }
function detailValue(key: string) { if (!current.value) return '—'; const value = rawValue(current.value, key); if (typeof value === 'boolean') return value ? '是' : '否'; if (key.includes('rate') || ['ad_drr', 'ad_ctr', 'ad_cvr', 'ad_click_share'].includes(key)) return percent(value); return value === null || value === undefined || value === '' ? '—' : String(value) }
function drillQuery() { return { platform: platform.value, shop_id: String(current.value?.shop_id || ''), date_from: current.value?.stat_date, date_to: current.value?.stat_date, sku: platform.value === 'ozon' ? String(current.value?.product_id || '') : undefined, nm_id: platform.value === 'wildberries' ? String(current.value?.product_id || '') : undefined, offer_id: platform.value === 'ozon' ? current.value?.seller_code || undefined : undefined, vendor_code: platform.value === 'wildberries' ? current.value?.seller_code || undefined : undefined } }
function goOrders() { router.push({ path: platform.value === 'ozon' ? '/analytics/orders' : '/analytics/orders/statistics', query: drillQuery() }) }
function goReturns() { router.push({ path: '/analytics/returns', query: drillQuery() }) }
function goFunnel() { router.push({ path: '/analysis/traffic/sales-funnel', query: drillQuery() }) }
function goAdverts() { router.push({ path: platform.value === 'ozon' ? '/analytics/adverts/ozon-efficiency' : '/analytics/adverts/adverts-report', query: drillQuery() }) }
function rankingDrillQuery() { return { platform: platform.value, shop_id: filters.shop_id ? String(filters.shop_id) : undefined, date_from: dateRange.value?.[0], date_to: dateRange.value?.[1], sku: platform.value === 'ozon' ? String(rankingDetail.value?.product_id || '') : undefined, nm_id: platform.value === 'wildberries' ? String(rankingDetail.value?.product_id || '') : undefined, offer_id: platform.value === 'ozon' ? rankingDetail.value?.seller_code || undefined : undefined, vendor_code: platform.value === 'wildberries' ? rankingDetail.value?.seller_code || undefined : undefined } }
function goRankingOrders() { router.push({ path: platform.value === 'ozon' ? '/analytics/orders' : '/analytics/orders/statistics', query: rankingDrillQuery() }) }
function goRankingReturns() { router.push({ path: '/analytics/returns', query: rankingDrillQuery() }) }
function goRankingFunnel() { router.push({ path: '/analysis/traffic/sales-funnel', query: rankingDrillQuery() }) }
function goRankingAdverts() { router.push({ path: platform.value === 'ozon' ? '/analytics/adverts/ozon-efficiency' : '/analytics/adverts/adverts-report', query: rankingDrillQuery() }) }
onMounted(search)
</script>

<style scoped lang="scss">
.analysis-page { .heading-card, .filter-card, .notice, .table-card { margin-bottom: 16px; } .heading, .table-header, .chart-header, .heading-side { display: flex; align-items: center; justify-content: space-between; gap: 16px; } .heading-side { justify-content: flex-end; } .table-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; } h2 { margin: 0; font-size: 20px; } p { margin: 6px 0 0; color: var(--el-text-color-secondary); } .updated, .table-header span, .chart-hint { color: var(--el-text-color-secondary); font-size: 13px; margin-left: 12px; } :deep(.el-date-editor), :deep(.el-select), :deep(.el-input-number) { width: 100%; } .actions :deep(.el-form-item__content) { justify-content: flex-end; } }
.kpi-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }.kpi-label { color: var(--el-text-color-secondary); font-size: 13px; }.kpi-value { margin: 10px 0 6px; font-size: 22px; font-weight: 650; }.kpi-note { color: var(--el-text-color-secondary); font-size: 12px; }.chart-grid { display: grid; grid-template-columns: 3fr 2fr; gap: 16px; margin-bottom: 16px; }.chart { height: 310px; }.column-settings { display: flex; flex-direction: column; }.tags { display: flex; flex-wrap: wrap; gap: 4px; }.pagination { display: flex; justify-content: flex-end; padding-top: 16px; }.detail-group { margin-bottom: 22px; h3 { margin: 0 0 10px; font-size: 15px; } }.drill-actions { display: flex; flex-wrap: wrap; gap: 8px; }
@media (max-width: 1200px) { .kpi-grid { grid-template-columns: repeat(3, 1fr); } .chart-grid { grid-template-columns: 1fr; } } @media (max-width: 700px) { .kpi-grid { grid-template-columns: 1fr 1fr; } .analysis-page .heading, .analysis-page .heading-side { align-items: flex-start; flex-direction: column; } }
</style>
