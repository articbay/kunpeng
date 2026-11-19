<template>
  <el-select
    v-model="selectedShopId"
    :loading="loading"
    :no-data-text="emptyText"
    placeholder="全部店铺"
    filterable
    clearable
    class="platform-shop-select"
  >
    <el-option
      v-for="shop in shops"
      :key="shop.id"
      :label="shopOptionLabel(shop)"
      :value="shop.id"
    >
      <span>{{ shop.name }}</span>
      <span class="shop-id">ID：{{ shop.id }}</span>
    </el-option>
  </el-select>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { shopApi, type Shop } from '@/api/modules/shop'

type ShopPlatform = 'wildberries' | 'ozon'

const props = defineProps<{
  modelValue?: number
  platform: ShopPlatform
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | undefined]
  'shops-loaded': [shops: Shop[]]
}>()

const loading = ref(false)
const loadFailed = ref(false)
const shops = ref<Shop[]>([])

const selectedShopId = computed({
  get: () => props.modelValue,
  set: (value: number | undefined) => emit('update:modelValue', value)
})

const platformName = computed(() =>
  props.platform === 'wildberries' ? 'Wildberries' : 'Ozon'
)

const emptyText = computed(() =>
  loadFailed.value ? '店铺加载失败' : `暂无${platformName.value}店铺`
)

function shopOptionLabel(shop: Shop) {
  return `${shop.name}（ID：${shop.id}）`
}

async function fetchShops() {
  loading.value = true
  loadFailed.value = false
  try {
    const result = await shopApi.list()
    shops.value = result.filter(
      (shop) => shop.platform.toLowerCase() === props.platform
    )
    emit('shops-loaded', shops.value)
    if (
      props.modelValue !== undefined &&
      !shops.value.some((shop) => shop.id === props.modelValue)
    ) {
      emit('update:modelValue', undefined)
    }
  } catch {
    shops.value = []
    loadFailed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchShops)
</script>

<style scoped>
.platform-shop-select {
  width: 100%;
}

.shop-id {
  float: right;
  margin-left: 16px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
