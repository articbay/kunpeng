<template>
  <div class="shop-manager">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>店铺管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增店铺
          </el-button>
        </div>
      </template>

      <el-table :data="shopList" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="店铺名称" />
        <el-table-column prop="platform" label="平台" width="120">
          <template #default="{ row }">
            <el-tag :type="row.platform === 'wildberries' ? 'primary' : 'success'">
              {{ row.platform }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="platform_shop_id" label="平台店铺ID" />
        <el-table-column label="广告凭证" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.platform === 'ozon'" :type="row.performance_client_id ? 'success' : 'info'" size="small">
              {{ row.performance_client_id ? '已配置' : '未配置' }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑店铺' : '新增店铺'" width="560px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="140px">
        <el-form-item label="店铺名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入店铺名称" />
        </el-form-item>
        <el-form-item label="平台" prop="platform">
          <el-select v-model="form.platform" placeholder="请选择平台" style="width: 100%" @change="handlePlatformChange">
            <el-option label="Wildberries" value="wildberries" />
            <el-option label="Ozon" value="ozon" />
          </el-select>
        </el-form-item>

        <!-- 平台店铺ID：Ozon 即 Seller Client-Id -->
        <el-form-item :label="platformShopIdLabel" prop="platform_shop_id">
          <el-input v-model="form.platform_shop_id" :placeholder="platformShopIdPlaceholder" />
        </el-form-item>

        <!-- API 密钥：Ozon 即 Seller Api-Key -->
        <el-form-item :label="apiKeyLabel" prop="api_key">
          <el-input
            v-model="form.api_key"
            type="textarea"
            :rows="2"
            :placeholder="apiKeyPlaceholder"
          />
        </el-form-item>

        <!-- Ozon 广告 Performance API 凭证（仅 Ozon 平台显示） -->
        <template v-if="isOzon">
          <el-divider content-position="left">Ozon 广告 API（Performance）</el-divider>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 16px"
            title="广告数据走独立的 Performance API，凭证与 Seller API 不同"
            description="如需同步推广/广告统计数据，请填写广告 Client-Id 与 Client-Secret；留空则不同步广告数据。"
          />
          <el-form-item label="广告 Client-Id" prop="performance_client_id">
            <el-input
              v-model="form.performance_client_id"
              placeholder="形如 xxxxxxxx-xxxxxxxxxxxxx@advertising.performance.ozon.ru"
            />
          </el-form-item>
          <el-form-item label="广告 Client-Secret" prop="performance_client_secret">
            <el-input
              v-model="form.performance_client_secret"
              type="textarea"
              :rows="2"
              :placeholder="isEdit ? '留空表示不修改，如需更新请重新输入' : '请输入广告 API Client-Secret'"
            />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { shopApi, type Shop, type ShopCreateForm } from '@/api/modules/shop'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const shopList = ref<Shop[]>([])
const formRef = ref<any>(null)

const createEmptyForm = (): ShopCreateForm => ({
  name: '',
  platform: 'wildberries',
  platform_shop_id: '',
  api_key: '',
  performance_client_id: '',
  performance_client_secret: ''
})

const form = ref<ShopCreateForm>(createEmptyForm())

const isOzon = computed(() => form.value.platform === 'ozon')

// 平台差异化的字段标签与提示
const platformShopIdLabel = computed(() =>
  isOzon.value ? 'Client-Id（店铺ID）' : '平台店铺ID'
)
const platformShopIdPlaceholder = computed(() =>
  isOzon.value ? '请输入 Ozon Seller API 的 Client-Id' : '请输入平台店铺ID'
)
const apiKeyLabel = computed(() => (isOzon.value ? 'Api-Key' : 'API密钥'))
const apiKeyPlaceholder = computed(() => {
  if (isEdit.value) return '留空表示不修改，如需更新请重新输入'
  return isOzon.value ? '请输入 Ozon Seller API 的 Api-Key' : '请输入API密钥'
})

const rules = {
  name: [{ required: true, message: '请输入店铺名称', trigger: 'blur' }],
  platform: [{ required: true, message: '请选择平台', trigger: 'change' }]
}

const fetchShops = async () => {
  loading.value = true
  try {
    shopList.value = await shopApi.list()
  } catch (error) {
    // request interceptor 已处理错误提示
  } finally {
    loading.value = false
  }
}

const handlePlatformChange = () => {
  // 切换到非 Ozon 平台时清空广告凭证，避免误提交
  if (!isOzon.value) {
    form.value.performance_client_id = ''
    form.value.performance_client_secret = ''
  }
}

const handleAdd = () => {
  isEdit.value = false
  editId.value = null
  form.value = createEmptyForm()
  dialogVisible.value = true
}

const handleEdit = (row: Shop) => {
  isEdit.value = true
  editId.value = row.id
  // 敏感字段（api_key / performance_client_secret）不回显真实值，
  // 留空表示保持原值不变，仅当用户重新输入时才更新
  form.value = {
    name: row.name,
    platform: row.platform,
    platform_shop_id: row.platform_shop_id || '',
    api_key: '',
    performance_client_id: row.performance_client_id || '',
    performance_client_secret: ''
  }
  dialogVisible.value = true
}

const handleDelete = async (row: Shop) => {
  try {
    await ElMessageBox.confirm(`确定要删除店铺 "${row.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await shopApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchShops()
  } catch {
    // 用户取消
  }
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    const data: ShopCreateForm = {
      name: form.value.name,
      platform: form.value.platform,
      platform_shop_id: form.value.platform_shop_id || undefined,
      api_key: form.value.api_key || undefined
    }
    // 仅 Ozon 平台提交广告凭证
    if (isOzon.value) {
      data.performance_client_id = form.value.performance_client_id || undefined
      data.performance_client_secret = form.value.performance_client_secret || undefined
    }
    if (isEdit.value && editId.value) {
      await shopApi.update(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await shopApi.create(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchShops()
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  fetchShops()
})
</script>

<style scoped lang="scss">
.shop-manager {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
