# API v1版本模块
from fastapi import APIRouter

from kunpeng.api.v1 import (
    auth,
    dashboard,
    ozon_advert_efficiency,
    ozon_customer_voice,
    ozon_goods_daily_analysis,
    ozon_order,
    ozon_order_lifecycle,
    ozon_return,
    ozon_sales_funnel,
    shop,
    shop_access,
    wb_order,
    wb_order_lifecycle,
    wb_order_statistics,
    wb_goods_daily_analysis,
    wb_return,
    wb_voc_feedback,
    wb_voc_pivot,
    wb_voc_question,
    wildberries,
)
from kunpeng.api.v1.platforms import sync

api_router = APIRouter()

# 注册路由
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(shop.router, prefix="/shops", tags=["shop"])
api_router.include_router(
    shop_access.router, prefix="/shop-access", tags=["shop-access"]
)
api_router.include_router(
    ozon_order.router,
    prefix="/ozon",
    tags=["ozon-orders"],
)
api_router.include_router(
    ozon_return.router,
    prefix="/ozon",
    tags=["ozon-returns"],
)
api_router.include_router(
    ozon_advert_efficiency.router,
    prefix="/ozon",
    tags=["ozon-advert-efficiency"],
)
api_router.include_router(
    ozon_customer_voice.router,
    prefix="/ozon",
    tags=["ozon-customer-voice"],
)
api_router.include_router(
    ozon_goods_daily_analysis.router,
    prefix="/ozon",
    tags=["ozon-goods-daily-analysis"],
)
api_router.include_router(
    ozon_order_lifecycle.router,
    prefix="/ozon",
    tags=["ozon-order-lifecycle"],
)
api_router.include_router(
    ozon_sales_funnel.router,
    prefix="/ozon",
    tags=["ozon-sales-funnel"],
)
api_router.include_router(
    wildberries.router, prefix="/wildberries", tags=["wildberries"]
)
api_router.include_router(
    wb_goods_daily_analysis.router,
    prefix="/wildberries",
    tags=["wildberries-goods-daily-analysis"],
)
api_router.include_router(
    wb_order.router,
    prefix="/wildberries",
    tags=["wildberries-orders"],
)
api_router.include_router(
    wb_order_lifecycle.router,
    prefix="/wildberries",
    tags=["wildberries-order-lifecycle"],
)
api_router.include_router(
    wb_order_statistics.router,
    prefix="/wildberries",
    tags=["wildberries-order-statistics"],
)
api_router.include_router(
    wb_return.router,
    prefix="/wildberries",
    tags=["wildberries-returns"],
)
api_router.include_router(
    wb_voc_feedback.router,
    prefix="/wildberries/voc",
    tags=["wildberries-voc"],
)
api_router.include_router(
    wb_voc_question.router,
    prefix="/wildberries/voc",
    tags=["wildberries-voc"],
)
api_router.include_router(
    wb_voc_pivot.router,
    prefix="/wildberries/voc",
    tags=["wildberries-voc"],
)
api_router.include_router(sync.router, prefix="", tags=["platforms"])
