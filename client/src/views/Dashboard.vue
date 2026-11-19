<template>
  <div class="dashboard" v-loading="loading">
    <!-- 顶部：标题 + 筛选 -->
    <div class="toolbar">
      <div class="toolbar-title">
        <span class="title">经营总览</span>
        <span class="subtitle" v-if="summary">
          {{ summary.range.date_from }} ~ {{ summary.range.date_to }}
        </span>
      </div>
      <div class="toolbar-filters">
        <el-segmented v-model="platform" :options="platformOptions" @change="onPlatformChange" />
        <el-select
          v-model="shopId"
          class="shop-select"
          placeholder="全部店铺"
          clearable
          filterable
          @change="reload"
        >
          <el-option
            v-for="shop in shopOptions"
            :key="shop.id"
            :label="shop.name"
            :value="shop.id"
          >
            <span class="shop-option">
              <span class="shop-option-name">{{ shop.name }}</span>
              <el-tag
                :type="shop.platform === 'ozon' ? 'primary' : 'warning'"
                effect="plain"
                size="small"
              >
                {{ shop.platform === 'ozon' ? 'Ozon' : 'WB' }}
              </el-tag>
            </span>
          </el-option>
        </el-select>
        <el-radio-group v-model="days" @change="reload">
          <el-radio-button :value="7">近7天</el-radio-button>
          <el-radio-button :value="30">近30天</el-radio-button>
          <el-radio-button :value="90">近90天</el-radio-button>
          <el-radio-button :value="180">近半年</el-radio-button>
        </el-radio-group>
        <el-button :icon="Refresh" circle @click="reload" title="刷新" />
      </div>
    </div>

    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :xs="12" :sm="12" :md="6" v-for="card in kpiCards" :key="card.label">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" :style="{ backgroundColor: card.bg }">
              <el-icon :size="26" :color="card.color"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
              <div class="stat-sub" v-if="card.sub">{{ card.sub }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第一行：销售趋势(大) + 平台份额饼图 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header"><span>销售额与订单趋势</span></div>
          </template>
          <v-chart class="chart" :option="trendOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card shadow="never">
          <template #header>
            <div class="card-header"><span>平台销售额占比</span></div>
          </template>
          <v-chart class="chart" :option="platformPieOption" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行：广告花费/DRR + 退货趋势 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header"><span>广告花费与费比(DRR)</span></div>
          </template>
          <v-chart class="chart" :option="adOption" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header"><span>退货量趋势</span></div>
          </template>
          <v-chart class="chart" :option="returnsOption" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 第三行：店铺维度表 + Top 商品 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header"><span>店铺经营明细</span></div>
          </template>
          <el-table :data="summary?.shops || []" size="default" stripe>
            <el-table-column prop="shop_name" label="店铺" min-width="140" show-overflow-tooltip />
            <el-table-column label="平台" width="120">
              <template #default="{ row }">
                <el-tag :type="row.platform === 'ozon' ? 'primary' : 'warning'" effect="light" size="small">
                  {{ row.platform_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="销售额(₽)" align="right" min-width="120" sortable
              :sort-by="(r: ShopStat) => r.gmv">
              <template #default="{ row }">{{ formatMoney(row.gmv) }}</template>
            </el-table-column>
            <el-table-column prop="orders" label="订单" align="right" width="90" sortable />
            <el-table-column label="退货率" align="right" width="100" sortable :sort-by="(r: ShopStat) => r.return_rate">
              <template #default="{ row }">
                <span :class="row.return_rate > 20 ? 'danger-text' : ''">{{ row.return_rate }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="广告费(₽)" align="right" min-width="110">
              <template #default="{ row }">{{ formatMoney(row.ad_spend) }}</template>
            </el-table-column>
            <el-table-column label="DRR" align="right" width="90" sortable :sort-by="(r: ShopStat) => r.drr">
              <template #default="{ row }">{{ row.drr }}%</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card shadow="never">
          <template #header>
            <div class="card-header"><span>热销商品 Top{{ (summary?.top_products || []).length }}</span></div>
          </template>
          <div class="top-list">
            <div class="top-item" v-for="(p, i) in summary?.top_products || []" :key="p.platform + p.ext_id">
              <span class="rank" :class="'rank-' + (i < 3 ? i + 1 : 'n')">{{ i + 1 }}</span>
              <div class="top-main">
                <div class="top-name" :title="p.name">{{ p.name || p.ext_id }}</div>
                <div class="top-meta">
                  <el-tag :type="p.platform === 'ozon' ? 'primary' : 'warning'" effect="plain" size="small">
                    {{ p.platform_label }}
                  </el-tag>
                  <span class="top-units">{{ p.units }} 件</span>
                </div>
              </div>
              <span class="top-gmv">{{ formatMoney(p.gmv) }}</span>
            </div>
            <el-empty v-if="!(summary?.top_products || []).length" description="暂无数据" :image-size="80" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Wallet,
  ShoppingCart,
  RefreshLeft,
  Promotion,
} from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { dashboardApi, type DashboardSummary, type ShopStat } from '@/api/modules/dashboard'
import { shopApi, type Shop } from '@/api/modules/shop'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
])

const WB_COLOR = '#7C3AED'
const OZON_COLOR = '#2563EB'
const ACCENT = '#F59E0B'
const DANGER = '#EF4444'

const loading = ref(false)
const summary = ref<DashboardSummary | null>(null)
const days = ref(30)
const platform = ref('')
const shopId = ref<number | undefined>(undefined)
const shops = ref<Shop[]>([])

const platformOptions = [
  { label: '全部平台', value: '' },
  { label: 'Wildberries', value: 'wildberries' },
  { label: 'Ozon', value: 'ozon' },
]

const shopOptions = computed(() =>
  shops.value.filter((shop) => !platform.value || shop.platform === platform.value)
)

function onPlatformChange() {
  if (
    shopId.value !== undefined &&
    !shopOptions.value.some((shop) => shop.id === shopId.value)
  ) {
    shopId.value = undefined
  }
  reload()
}

async function loadShops() {
  try {
    shops.value = await shopApi.list()
  } catch {
    // 店铺列表加载失败不阻断仪表盘主数据展示。
  }
}

function formatMoney(v: number): string {
  return '₽ ' + Math.round(v || 0).toLocaleString('ru-RU')
}
function formatInt(v: number): string {
  return (v || 0).toLocaleString('ru-RU')
}

const kpiCards = computed(() => {
  const k = summary.value?.kpi
  if (!k) return []
  return [
    {
      label: '总销售额',
      value: formatMoney(k.gmv),
      sub: `客单价 ${formatMoney(k.avg_order_value)}`,
      icon: Wallet,
      color: '#7C3AED',
      bg: '#F3EEFF',
    },
    {
      label: '订单量',
      value: formatInt(k.orders),
      sub: `${formatInt(k.units)} 件商品`,
      icon: ShoppingCart,
      color: '#2563EB',
      bg: '#EAF1FF',
    },
    {
      label: '退货率',
      value: k.return_rate + '%',
      sub: `${formatInt(k.returns)} 笔退货`,
      icon: RefreshLeft,
      color: '#EF4444',
      bg: '#FEECEC',
    },
    {
      label: '广告花费',
      value: formatMoney(k.ad_spend),
      sub: `费比 DRR ${k.drr}%`,
      icon: Promotion,
      color: '#F59E0B',
      bg: '#FEF5E6',
    },
  ]
})

const trendOption = computed(() => {
  const t = summary.value?.trend || []
  const dates = t.map((p) => p.date.slice(5))
  const gmv = t.map((p) => +(p.wb_gmv + p.ozon_gmv).toFixed(2))
  const orders = t.map((p) => p.wb_orders + p.ozon_orders)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['销售额', '订单量'], top: 0 },
    grid: { left: 10, right: 10, bottom: 30, top: 40, containLabel: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 6 }],
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: [
      { type: 'value', name: '销售额₽', axisLabel: { formatter: (v: number) => (v >= 1000 ? v / 1000 + 'k' : v) } },
      { type: 'value', name: '订单', splitLine: { show: false } },
    ],
    series: [
      {
        name: '销售额',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: gmv,
        itemStyle: { color: WB_COLOR },
        areaStyle: { opacity: 0.12, color: WB_COLOR },
      },
      {
        name: '订单量',
        type: 'bar',
        yAxisIndex: 1,
        data: orders,
        barMaxWidth: 18,
        itemStyle: { color: ACCENT, opacity: 0.55 },
      },
    ],
  }
})

const platformPieOption = computed(() => {
  const plats = summary.value?.platforms || []
  const data = plats.map((p) => ({
    name: p.platform_label,
    value: +p.gmv.toFixed(2),
    itemStyle: { color: p.platform === 'ozon' ? OZON_COLOR : WB_COLOR },
  }))
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}<br/>₽ ${Math.round(p.value).toLocaleString('ru-RU')} (${p.percent}%)`,
    },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        label: { formatter: '{d}%' },
        data,
      },
    ],
  }
})

const adOption = computed(() => {
  const t = summary.value?.trend || []
  const dates = t.map((p) => p.date.slice(5))
  const wb = t.map((p) => +p.wb_ad_spend.toFixed(2))
  const ozon = t.map((p) => +p.ozon_ad_spend.toFixed(2))
  const drr = t.map((p) => {
    const gmv = p.wb_gmv + p.ozon_gmv
    const spend = p.wb_ad_spend + p.ozon_ad_spend
    return gmv > 0 ? +((spend / gmv) * 100).toFixed(2) : 0
  })
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['WB广告费', 'Ozon广告费', 'DRR'], top: 0 },
    grid: { left: 10, right: 10, bottom: 20, top: 40, containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: [
      { type: 'value', name: '花费₽' },
      { type: 'value', name: 'DRR%', splitLine: { show: false } },
    ],
    series: [
      { name: 'WB广告费', type: 'bar', stack: 'ad', data: wb, itemStyle: { color: WB_COLOR } },
      { name: 'Ozon广告费', type: 'bar', stack: 'ad', data: ozon, itemStyle: { color: OZON_COLOR } },
      {
        name: 'DRR',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        data: drr,
        itemStyle: { color: DANGER },
      },
    ],
  }
})

const returnsOption = computed(() => {
  const t = summary.value?.trend || []
  const dates = t.map((p) => p.date.slice(5))
  const wb = t.map((p) => p.wb_returns)
  const ozon = t.map((p) => p.ozon_returns)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Wildberries', 'Ozon'], top: 0 },
    grid: { left: 10, right: 10, bottom: 20, top: 40, containLabel: true },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '退货量' },
    series: [
      { name: 'Wildberries', type: 'line', smooth: true, showSymbol: false, data: wb, itemStyle: { color: WB_COLOR } },
      { name: 'Ozon', type: 'line', smooth: true, showSymbol: false, data: ozon, itemStyle: { color: OZON_COLOR } },
    ],
  }
})

async function reload() {
  loading.value = true
  try {
    summary.value = await dashboardApi.summary({
      days: days.value,
      platform: platform.value || undefined,
      shop_id: shopId.value,
    })
  } catch (e) {
    ElMessage.error('加载仪表盘数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadShops()
  reload()
})
</script>

<style scoped lang="scss">
.dashboard {
  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;

    .toolbar-title {
      display: flex;
      align-items: baseline;
      gap: 12px;

      .title {
        font-size: 20px;
        font-weight: 600;
        color: #1f2329;
      }
      .subtitle {
        font-size: 13px;
        color: #8a9099;
      }
    }
    .toolbar-filters {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;

      .shop-select {
        width: 180px;
      }
    }
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

  .kpi-row {
    margin-bottom: 4px;
  }

  .stat-card {
    margin-bottom: 16px;
    border-radius: 8px;

    .stat-content {
      display: flex;
      align-items: center;
    }
    .stat-icon {
      width: 52px;
      height: 52px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 14px;
      flex-shrink: 0;
    }
    .stat-info {
      min-width: 0;
    }
    .stat-value {
      font-size: 22px;
      font-weight: 700;
      color: #1f2329;
      line-height: 1.2;
    }
    .stat-label {
      font-size: 13px;
      color: #646a73;
      margin-top: 2px;
    }
    .stat-sub {
      font-size: 12px;
      color: #a0a4ab;
      margin-top: 2px;
    }
  }

  .chart-row {
    margin-top: 4px;

    .el-card {
      margin-bottom: 16px;
      border-radius: 8px;
    }
  }

  .card-header {
    font-weight: 600;
    color: #1f2329;
  }

  .chart {
    height: 340px;
  }

  .danger-text {
    color: #ef4444;
    font-weight: 600;
  }

  .top-list {
    height: 340px;
    overflow-y: auto;

    .top-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 4px;
      border-bottom: 1px solid #f0f1f3;

      &:last-child {
        border-bottom: none;
      }
    }
    .rank {
      width: 24px;
      height: 24px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      color: #8a9099;
      background: #f2f3f5;
      flex-shrink: 0;
    }
    .rank-1 { background: #fef0e6; color: #f59e0b; }
    .rank-2 { background: #eef1f6; color: #7f8794; }
    .rank-3 { background: #fbeee6; color: #cd7f32; }

    .top-main {
      flex: 1;
      min-width: 0;
    }
    .top-name {
      font-size: 13px;
      color: #1f2329;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .top-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 4px;

      .top-units {
        font-size: 12px;
        color: #a0a4ab;
      }
    }
    .top-gmv {
      font-size: 14px;
      font-weight: 600;
      color: #1f2329;
      flex-shrink: 0;
    }
  }
}
</style>
