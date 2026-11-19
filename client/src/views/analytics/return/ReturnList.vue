<template>
  <div class="return-analysis-page">
    <AnalyticsPageHeader
      title="退货分析"
      description="按平台查看退货明细、退货状态及相关商品信息"
    >
      <el-radio-group v-model="activePlatform">
        <el-radio-button value="wildberries">Wildberries</el-radio-button>
        <el-radio-button value="ozon">Ozon</el-radio-button>
      </el-radio-group>
    </AnalyticsPageHeader>

    <WBReturnList v-if="activePlatform === 'wildberries'" />
    <OzonReturnList v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AnalyticsPageHeader from '@/components/analytics/AnalyticsPageHeader.vue'
import OzonReturnList from './OzonReturnList.vue'
import WBReturnList from './WBReturnList.vue'

type ReturnPlatform = 'wildberries' | 'ozon'

const route = useRoute()
const router = useRouter()

const activePlatform = computed<ReturnPlatform>({
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
