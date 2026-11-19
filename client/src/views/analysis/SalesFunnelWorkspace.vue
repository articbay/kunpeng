<template>
  <div class="sales-funnel-workspace">
    <AnalyticsPageHeader
      title="销售漏斗"
      description="按平台、店铺和商品查看访问、加购、下单与成交转化表现"
    >
      <el-radio-group v-model="activePlatform">
        <el-radio-button value="wildberries">Wildberries</el-radio-button>
        <el-radio-button value="ozon">Ozon</el-radio-button>
      </el-radio-group>
    </AnalyticsPageHeader>

    <SalesFunnelList v-if="activePlatform === 'wildberries'" />
    <OzonSalesFunnelList v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AnalyticsPageHeader from '@/components/analytics/AnalyticsPageHeader.vue'
import OzonSalesFunnelList from '@/views/analytics/traffic/OzonSalesFunnelList.vue'
import SalesFunnelList from './SalesFunnelList.vue'

type SalesFunnelPlatform = 'wildberries' | 'ozon'

const route = useRoute()
const router = useRouter()

const activePlatform = computed<SalesFunnelPlatform>({
  get() {
    return route.query.platform === 'ozon' ? 'ozon' : 'wildberries'
  },
  set(platform) {
    router.replace({
      query: {
        ...route.query,
        platform
      }
    })
  }
})
</script>
