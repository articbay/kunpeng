import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/modules/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layout/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'shops',
        name: 'ShopManager',
        component: () => import('@/views/shop/ShopManager.vue'),
        meta: { adminOnly: true }
      },
      {
        path: 'analysis/financial-reports',
        name: 'FinancialReportList',
        component: () => import('@/views/analysis/FinancialReportList.vue')
      },
      {
        path: 'analysis/finance/financial-report-summaries',
        name: 'FinancialReportSummaryList',
        component: () => import('@/views/analysis/FinancialReportSummaryList.vue')
      },
      {
        path: 'analysis/traffic/sales-funnel',
        name: 'SalesFunnelList',
        component: () => import('@/views/analysis/SalesFunnelWorkspace.vue')
      },
      {
        path: 'analysis/traffic/ozon-sales-funnel',
        name: 'OzonSalesFunnelList',
        redirect: (to) => ({
          path: '/analysis/traffic/sales-funnel',
          query: { ...to.query, platform: 'ozon' }
        })
      },
      {
        path: 'analytics',
        name: 'Analytics',
        redirect: '/analytics/orders',
        children: [
          {
            path: 'goods/daily',
            name: 'GoodsDailyAnalysis',
            component: () => import('@/views/analytics/goods/GoodsDailyAnalysis.vue')
          },
          {
            path: 'goods/ozon-daily',
            redirect: (to) => ({
              path: '/analytics/goods/daily',
              query: { ...to.query, platform: 'ozon' }
            })
          },
          {
            path: 'goods/lifecycle',
            name: 'OrderLifecycle',
            component: () => import('@/views/analytics/goods/OrderLifecycle.vue')
          },
          {
            path: 'goods/ozon-lifecycle',
            redirect: (to) => ({
              path: '/analytics/goods/lifecycle',
              query: { ...to.query, platform: 'ozon' }
            })
          },
          {
            path: 'orders',
            name: 'OrderWorkspace',
            component: () => import('@/views/analytics/order/OrderWorkspace.vue')
          },
          {
            path: 'orders/statistics',
            name: 'WBOrderStatisticsList',
            component: () => import('@/views/analytics/order/OrderStatisticsList.vue')
          },
          {
            path: 'returns',
            name: 'WBReturnList',
            component: () => import('@/views/analytics/return/ReturnList.vue')
          },
          {
            path: 'voc/feedbacks',
            name: 'CustomerVoiceWorkspace',
            component: () => import('@/views/analytics/voc/CustomerVoiceWorkspace.vue')
          },
          {
            path: 'voc/questions',
            name: 'WBVOCQuestionList',
            component: () => import('@/views/analytics/voc/QuestionList.vue')
          },
          {
            path: 'voc/pivot',
            name: 'WBVOCPivotExport',
            component: () => import('@/views/analytics/voc/PivotExport.vue')
          },
          {
            path: 'adverts',
            name: 'WBAdverts',
            redirect: '/analytics/adverts/adverts-report',
            children: [
              {
                path: 'adverts-report',
                name: 'AdvertsReport',
                component: () => import('@/views/data-analysis/AdvertsReport.vue')
              },
              {
                path: 'ozon-efficiency',
                name: 'OzonAdvertEfficiency',
                component: () => import('@/views/analytics/adverts/OzonAdvertEfficiencyList.vue')
              }
            ]
          }
        ]
      },
      {
        path: 'users',
        name: 'UserManager',
        component: () => import('@/views/user/UserManager.vue'),
        meta: { adminOnly: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, _from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth !== false && !userStore.isLoggedIn) {
    next('/login')
    return
  }

  if (userStore.isLoggedIn && !userStore.userInfo) {
    try {
      await userStore.fetchUserInfo()
    } catch {
      next('/login')
      return
    }
  }

  if (to.meta.adminOnly && !userStore.isSuperuser) {
    next('/dashboard')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
