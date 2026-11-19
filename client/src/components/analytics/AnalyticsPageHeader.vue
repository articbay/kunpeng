<template>
  <el-card shadow="never" class="analytics-page-header">
    <div class="header-content">
      <div class="header-copy">
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
      <div v-if="$slots.default" class="header-actions">
        <slot />
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<style scoped>
.analytics-page-header {
  margin-bottom: 16px;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.header-copy h2 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 20px;
}

.header-copy p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 640px) {
  .header-content {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
  }
}
</style>
