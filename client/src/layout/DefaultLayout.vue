<template>
  <el-container class="layout-container">
    <el-aside :width="asideWidth">
      <div class="logo">
        <h3 v-if="!collapsed">Kunpeng</h3>
        <h3 v-else>K</h3>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        :collapse-transition="false"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        <el-menu-item v-if="userStore.isSuperuser" index="/users">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        <el-menu-item v-if="userStore.isSuperuser" index="/shops">
          <el-icon><Shop /></el-icon>
          <template #title>店铺管理</template>
        </el-menu-item>
<el-sub-menu index="/analysis">
  <template #title>
    <el-icon><DataAnalysis /></el-icon>
    <span>数据分析</span>
  </template>
  <el-sub-menu index="/analytics/goods">
    <template #title>
      <el-icon><Goods /></el-icon>
      <span>商品经营</span>
    </template>
    <el-menu-item index="/analytics/goods/daily">
      <el-icon><DataLine /></el-icon>
      <template #title>商品日分析</template>
    </el-menu-item>
    <el-menu-item index="/analytics/goods/lifecycle">
      <el-icon><Connection /></el-icon>
      <template #title>订单生命周期</template>
    </el-menu-item>
  </el-sub-menu>
  <el-sub-menu index="/analytics/orders-group">
    <template #title>
      <el-icon><Tickets /></el-icon>
      <span>订单</span>
    </template>
    <el-menu-item index="/analytics/orders">
      <el-icon><Document /></el-icon>
      <template #title>履约订单</template>
    </el-menu-item>
    <el-menu-item index="/analytics/orders/statistics">
      <el-icon><DataLine /></el-icon>
      <template #title>统计订单</template>
    </el-menu-item>
  </el-sub-menu>
  <el-sub-menu index="/analysis/traffic">
    <template #title>
      <el-icon><TrendCharts /></el-icon>
      <span>流量数据</span>
    </template>
    <el-menu-item index="/analysis/traffic/sales-funnel">
      <el-icon><DataLine /></el-icon>
      <template #title>销售漏斗</template>
    </el-menu-item>
  </el-sub-menu>
  <el-sub-menu index="/analytics/voc">
    <template #title>
      <el-icon><ChatDotRound /></el-icon>
      <span>客户声音</span>
    </template>
    <el-menu-item index="/analytics/voc/feedbacks">
      <el-icon><Star /></el-icon>
      <template #title>客户评价</template>
    </el-menu-item>
    <el-menu-item index="/analytics/voc/questions">
      <el-icon><QuestionFilled /></el-icon>
      <template #title>客户提问</template>
    </el-menu-item>
    <el-menu-item index="/analytics/voc/pivot">
      <el-icon><DataAnalysis /></el-icon>
      <template #title>客户声音透视表</template>
    </el-menu-item>
  </el-sub-menu>
  <el-menu-item index="/analytics/returns">
    <el-icon><RefreshLeft /></el-icon>
    <template #title>退货</template>
  </el-menu-item>
  <el-sub-menu index="/analytics/adverts">
    <template #title>
      <el-icon><Promotion /></el-icon>
      <span>广告</span>
    </template>
    <el-menu-item index="/analytics/adverts/adverts-report">
      <el-icon><Document /></el-icon>
      <template #title>WB广告列表周维度</template>
    </el-menu-item>
    <el-menu-item index="/analytics/adverts/ozon-efficiency">
      <el-icon><DataAnalysis /></el-icon>
      <template #title>Ozon广告列表日维度</template>
    </el-menu-item>
  </el-sub-menu>
  <el-sub-menu index="/analysis/finance">
    <template #title>
      <el-icon><Money /></el-icon>
      <span>财务数据</span>
    </template>
    <el-menu-item index="/analysis/financial-reports">
      <el-icon><Document /></el-icon>
      <template #title>财务报表周明细</template>
    </el-menu-item>
    <el-menu-item index="/analysis/finance/financial-report-summaries">
      <el-icon><Document /></el-icon>
      <template #title>财务报表周汇总</template>
    </el-menu-item>
  </el-sub-menu>
</el-sub-menu>

      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-content">
          <div class="header-left">
            <el-icon class="collapse-btn" @click="collapsed = !collapsed">
              <Expand v-if="collapsed" />
              <Fold v-else />
            </el-icon>
            <span class="title">Kunpeng 跨境电商系统</span>
          </div>
          <div class="user-info">
            <el-dropdown @command="handleCommand">
              <span class="el-dropdown-link">
                <el-icon><User /></el-icon>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  ChatDotRound,
  Connection,
  DataAnalysis,
  DataLine,
  Document,
  Expand,
  Fold,
  Goods,
  Money,
  Promotion,
  QuestionFilled,
  RefreshLeft,
  Shop,
  Star,
  Tickets,
  TrendCharts,
  User
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/modules/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 窄屏（<= 768px）自动折叠侧边栏，避免主内容区被挤压导致图表坍缩
const MOBILE_BREAKPOINT = 768
const collapsed = ref(false)
const asideWidth = computed(() => (collapsed.value ? '64px' : '260px'))

function syncWithViewport() {
  collapsed.value = window.innerWidth <= MOBILE_BREAKPOINT
}

onMounted(() => {
  syncWithViewport()
  window.addEventListener('resize', syncWithViewport)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncWithViewport)
})

const activeMenu = computed(() => route.path)

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      userStore.logout()
      router.push('/login')
      ElMessage.success('已退出登录')
    } catch {
      // 用户取消
    }
  }
}
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;

  .el-aside {
    background-color: #304156;
    overflow-x: hidden;
    transition: width 0.2s ease;

    .logo {
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;

      h3 {
        color: #fff;
        margin: 0;
      }
    }

    .el-menu {
      border-right: none;
    }
  }

  .el-header {
    background-color: #fff;
    border-bottom: 1px solid #e6e6e6;
    padding: 0 20px;
    display: flex;
    align-items: center;

    .header-content {
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;

      .header-left {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .collapse-btn {
        font-size: 20px;
        cursor: pointer;
        color: #5a5e66;

        &:hover {
          color: #409eff;
        }
      }

      .title {
        font-size: 18px;
        font-weight: bold;
      }

      .user-info {
        .el-dropdown-link {
          display: flex;
          align-items: center;
          cursor: pointer;
        }
      }
    }
  }

  .el-main {
    background-color: #f0f2f5;
    padding: 20px;
  }
}

@media (max-width: 768px) {
  .layout-container {
    .el-header {
      padding: 0 12px;

      .header-content .title {
        font-size: 15px;
      }
    }

    .el-main {
      padding: 12px;
    }
  }
}
</style>
