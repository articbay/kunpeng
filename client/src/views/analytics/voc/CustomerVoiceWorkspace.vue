<template>
  <div>
    <AnalyticsPageHeader
      title="客户评价"
      description="按平台查看客户评价、评分、回复和翻译结果"
    >
      <el-radio-group v-model="activePlatform">
        <el-radio-button value="wildberries">Wildberries</el-radio-button>
        <el-radio-button value="ozon">Ozon</el-radio-button>
      </el-radio-group>
    </AnalyticsPageHeader>
    <FeedbackList v-if="activePlatform === 'wildberries'" />
    <OzonCustomerVoiceList v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AnalyticsPageHeader from '@/components/analytics/AnalyticsPageHeader.vue'
import FeedbackList from './FeedbackList.vue'
import OzonCustomerVoiceList from './OzonCustomerVoiceList.vue'

const route = useRoute()
const router = useRouter()
const activePlatform = computed<'wildberries' | 'ozon'>({
  get: () => (route.query.platform === 'ozon' ? 'ozon' : 'wildberries'),
  set: (platform) => router.replace({ query: { ...route.query, platform } })
})
</script>
