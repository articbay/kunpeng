<template>
  <div class="pivot-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-title">
          <div>
            <h2>客户声音透视表</h2>
            <p>从现有评价、提问和退货明细生成可拖动字段的 Excel 透视表。</p>
          </div>
          <el-tag type="success" effect="plain">只读导出</el-tag>
        </div>
      </template>

      <el-alert
        title="导出过程只读取现有数据，不会修改数据库；打开 Excel 后如未自动刷新，可点击“数据 → 刷新”。"
        type="info"
        :closable="false"
        show-icon
      />

      <el-form label-position="top" class="filter-form">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="8">
            <el-form-item label="业务日期">
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="店铺 ID">
              <el-input-number v-model="filters.shop_id" :min="1" :controls="false" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="WB货号">
              <el-input-number v-model="filters.nm_id" :min="1" :controls="false" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="卖家货号">
              <el-input v-model.trim="filters.supplier_article" clearable />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="4">
            <el-form-item label="品牌">
              <el-input v-model.trim="filters.brand_name" clearable />
            </el-form-item>
          </el-col>
        </el-row>

        <el-alert
          v-if="filters.supplier_article"
          title="退货明细没有卖家货号字段，因此使用该筛选时，导出结果只包含评价和提问。"
          type="warning"
          :closable="false"
          show-icon
          class="filter-warning"
        />

        <div class="actions">
          <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
          <el-button type="success" :icon="Download" :loading="exporting" @click="exportPivot">
            导出原生数据透视表
          </el-button>
        </div>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header><span class="section-title">工作簿内容</span></template>
      <el-row :gutter="16">
        <el-col v-for="item in pivotSections" :key="item.title" :xs="24" :md="12" :xl="8">
          <div class="pivot-item">
            <el-icon><DataAnalysis /></el-icon>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.description }}</p>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Download, RefreshLeft } from '@element-plus/icons-vue'
import { vocPivotApi, type WBVOCPivotFilters } from '@/api/modules/vocPivot'
import { downloadExcel } from '@/utils/download'

const exporting = ref(false)
const dateRange = ref<string[]>([])
const filters = reactive<WBVOCPivotFilters>({})

const pivotSections = [
  { title: '客户声音-data', description: '评价、提问和退货三张 DWD 的统一明细。' },
  { title: '货号－星级数量', description: 'WB货号为行，评价星级为列。' },
  { title: '货号－原因', description: 'WB货号为行，退货原因分类为列。' },
  { title: '货号－状态', description: 'WB货号为行，退货状态为列。' },
  { title: '下单日期－状态', description: '下单日期为行，退货状态为列。' }
]

function activeFilters(): WBVOCPivotFilters {
  return {
    shop_id: filters.shop_id ?? undefined,
    date_from: dateRange.value[0] || undefined,
    date_to: dateRange.value[1] || undefined,
    nm_id: filters.nm_id ?? undefined,
    supplier_article: filters.supplier_article || undefined,
    brand_name: filters.brand_name || undefined
  }
}

function resetFilters() {
  dateRange.value = []
  Object.keys(filters).forEach((key) => delete filters[key as keyof WBVOCPivotFilters])
}

async function exportPivot() {
  exporting.value = true
  try {
    const blob = await vocPivotApi.export({ filters: activeFilters() })
    downloadExcel(blob, 'WB客户声音分析')
    ElMessage.success('原生数据透视表已生成')
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped lang="scss">
.pivot-page {
  display: flex;
  flex-direction: column;
  gap: 16px;

  .card-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    h2 { margin: 0 0 6px; color: #1f2329; font-size: 20px; }
    p { margin: 0; color: #7a828e; }
  }

  .filter-form {
    margin-top: 20px;
    :deep(.el-date-editor), :deep(.el-input-number) { width: 100%; }
  }

  .filter-warning { margin-bottom: 16px; }
  .actions { display: flex; justify-content: flex-end; gap: 12px; }
  .section-title { color: #1f2329; font-weight: 600; }

  .pivot-item {
    min-height: 82px;
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    padding: 16px;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    background: #f8fafc;
    .el-icon { flex: 0 0 auto; margin-top: 2px; color: #409eff; font-size: 22px; }
    p { margin: 8px 0 0; color: #7a828e; line-height: 1.5; }
  }
}
</style>
