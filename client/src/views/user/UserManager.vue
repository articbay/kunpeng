<template>
  <div class="user-manager">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增用户
          </el-button>
        </div>
      </template>

      <el-table :data="userList" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="full_name" label="姓名" />
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :active-value="true"
              :inactive-value="false"
              active-text="启用"
              inactive-text="停用"
              inline-prompt
              @change="handleToggleStatus.bind(null, row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="is_superuser" label="管理员" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_superuser ? 'danger' : 'info'">{{ row.is_superuser ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="350">
          <template #default="{ row }">
            <el-button v-if="!row.is_superuser" size="small" type="primary" @click="handleShopAccess(row)">店铺授权</el-button>
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="warning" @click="handleChangePassword(row)">修改密码</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="form.full_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="管理员" prop="is_superuser">
          <el-switch
            v-model="form.is_superuser"
            :active-value="true"
            :inactive-value="false"
            active-text="是"
            inactive-text="否"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="accessDialogVisible" :title="`店铺授权：${accessUser?.email || ''}`" width="520px">
      <el-alert
        title="被授权用户只能查看和导出店铺数据，不能修改店铺凭证或删除店铺。"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      />
      <div v-loading="accessLoading">
        <el-checkbox-group v-model="selectedShopIds" class="shop-access-list">
          <el-checkbox v-for="shop in accessOptions" :key="shop.shop_id" :label="shop.shop_id">
            {{ shop.shop_name }}（{{ shop.platform }}）
          </el-checkbox>
        </el-checkbox-group>
        <el-empty v-if="!accessLoading && accessOptions.length === 0" description="当前管理员还没有可授权的店铺" />
      </div>
      <template #footer>
        <el-button @click="accessDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="accessSaving" @click="handleSaveShopAccess">保存授权</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px">
      <el-form :model="pwdForm" :rules="pwdRules" ref="pwdFormRef" label-width="100px">
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitPassword" :loading="pwdSubmitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { userApi, type User, type UserCreateForm } from '@/api/modules/user'
import { shopAccessApi, type ShopAccessOption } from '@/api/modules/shopAccess'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const userList = ref<User[]>([])
const formRef = ref<any>(null)
const accessDialogVisible = ref(false)
const accessLoading = ref(false)
const accessSaving = ref(false)
const accessUser = ref<User | null>(null)
const accessOptions = ref<ShopAccessOption[]>([])
const selectedShopIds = ref<number[]>([])

const form = ref<UserCreateForm & { is_superuser: boolean }>({
  email: '',
  password: '',
  full_name: '',
  is_superuser: false
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ]
}

const pwdDialogVisible = ref(false)
const pwdSubmitLoading = ref(false)
const pwdFormRef = ref<any>(null)
const pwdEditId = ref<number | null>(null)
const pwdForm = ref({ new_password: '' })
const pwdRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ]
}

const fetchUsers = async () => {
  loading.value = true
  try {
    userList.value = await userApi.list()
  } catch (error) {
    // request interceptor 已处理错误提示
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  editId.value = null
  form.value = {
    email: '',
    password: '',
    full_name: '',
    is_superuser: false
  }
  dialogVisible.value = true
}

const handleEdit = (row: User) => {
  isEdit.value = true
  editId.value = row.id
  form.value = {
    email: row.email,
    password: '',
    full_name: row.full_name || '',
    is_superuser: row.is_superuser
  }
  dialogVisible.value = true
}

const handleDelete = async (row: User) => {
  try {
    await ElMessageBox.confirm(`确定要删除用户 "${row.email}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await userApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch {
    // 用户取消
  }
}

const handleToggleStatus = async (row: User, val: boolean) => {
  try {
    await userApi.toggleStatus(row.id, val)
    ElMessage.success(val ? '已启用' : '已停用')
    fetchUsers()
  } catch {
    // 失败时回滚状态
    row.is_active = !val
  }
}

const handleChangePassword = (row: User) => {
  pwdEditId.value = row.id
  pwdForm.value.new_password = ''
  pwdDialogVisible.value = true
}

const handleShopAccess = async (row: User) => {
  accessUser.value = row
  accessDialogVisible.value = true
  accessLoading.value = true
  try {
    const response = await shopAccessApi.get(row.id)
    accessOptions.value = response.shops
    selectedShopIds.value = response.shops
      .filter((shop) => shop.granted)
      .map((shop) => shop.shop_id)
  } finally {
    accessLoading.value = false
  }
}

const handleSaveShopAccess = async () => {
  if (!accessUser.value) return
  accessSaving.value = true
  try {
    await shopAccessApi.update(accessUser.value.id, selectedShopIds.value)
    ElMessage.success('店铺授权已更新')
    accessDialogVisible.value = false
  } finally {
    accessSaving.value = false
  }
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      await userApi.update(editId.value, {
        email: form.value.email,
        full_name: form.value.full_name || undefined,
        is_superuser: form.value.is_superuser
      })
      ElMessage.success('更新成功')
    } else {
      await userApi.create({
        email: form.value.email,
        password: form.value.password,
        full_name: form.value.full_name || undefined
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } finally {
    submitLoading.value = false
  }
}

const handleSubmitPassword = async () => {
  const valid = await pwdFormRef.value?.validate().catch(() => false)
  if (!valid) return

  pwdSubmitLoading.value = true
  try {
    if (pwdEditId.value) {
      await userApi.changePassword(pwdEditId.value, { new_password: pwdForm.value.new_password })
      ElMessage.success('密码修改成功')
    }
    pwdDialogVisible.value = false
  } finally {
    pwdSubmitLoading.value = false
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN')
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped lang="scss">
.user-manager {
  .shop-access-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
