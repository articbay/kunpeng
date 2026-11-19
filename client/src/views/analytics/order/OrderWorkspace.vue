<template>
  <div class="order-workspace">
    <AnalyticsPageHeader
      title="履约订单"
      description="按平台查询订单明细，并导出当前筛选或已选记录"
    >
      <el-radio-group v-model="platform">
        <el-radio-button
          v-for="option in platformOptions"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </el-radio-button>
      </el-radio-group>
    </AnalyticsPageHeader>

    <OrderList v-if="platform === 'wildberries'" />
    <OzonOrderList v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AnalyticsPageHeader from '@/components/analytics/AnalyticsPageHeader.vue'
import OrderList from './OrderList.vue'
import OzonOrderList from './OzonOrderList.vue'

type Platform = 'wildberries' | 'ozon'

const route = useRoute()
const router = useRouter()
const platformOptions = [
  { label: 'Wildberries', value: 'wildberries' },
  { label: 'Ozon', value: 'ozon' }
]

const platform = computed<Platform>({
  get: () => (route.query.platform === 'ozon' ? 'ozon' : 'wildberries'),
  set: (value) => {
    router.replace({ query: { ...route.query, platform: value } })
  }
})
</script>
