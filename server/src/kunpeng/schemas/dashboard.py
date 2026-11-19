"""
仪表盘（Dashboard）响应模型

面向前端的只读分析结构，聚合自 ODS 层多张表。
所有金额单位统一为卢布(₽)，不做汇率换算（WB / Ozon 均为俄罗斯平台）。
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    """统计时间范围"""

    date_from: str = Field(..., description="开始日期 YYYY-MM-DD")
    date_to: str = Field(..., description="结束日期 YYYY-MM-DD（含当天）")
    days: int = Field(..., description="统计天数")


class KpiBlock(BaseModel):
    """全局核心指标卡片"""

    gmv: float = Field(0, description="销售额(₽)")
    orders: int = Field(0, description="订单量")
    units: int = Field(0, description="销售件数")
    returns: int = Field(0, description="退货量")
    return_rate: float = Field(0, description="退货率(%)")
    ad_spend: float = Field(0, description="广告花费(₽)")
    drr: float = Field(0, description="广告费用占比 DRR(%)，= 广告花费 / 销售额")
    avg_order_value: float = Field(0, description="客单价(₽)")
    shop_count: int = Field(0, description="店铺数")


class TrendPoint(BaseModel):
    """按日趋势的一个数据点（分平台）"""

    date: str = Field(..., description="日期 YYYY-MM-DD")
    wb_gmv: float = 0
    ozon_gmv: float = 0
    wb_orders: int = 0
    ozon_orders: int = 0
    wb_ad_spend: float = 0
    ozon_ad_spend: float = 0
    wb_returns: int = 0
    ozon_returns: int = 0


class PlatformStat(BaseModel):
    """平台维度汇总"""

    platform: str
    platform_label: str
    gmv: float = 0
    orders: int = 0
    units: int = 0
    returns: int = 0
    return_rate: float = 0
    ad_spend: float = 0
    drr: float = 0
    shop_count: int = 0


class ShopStat(BaseModel):
    """店铺维度汇总"""

    shop_id: int
    shop_name: str
    platform: str
    platform_label: str
    gmv: float = 0
    orders: int = 0
    units: int = 0
    returns: int = 0
    return_rate: float = 0
    ad_spend: float = 0
    drr: float = 0


class TopProduct(BaseModel):
    """热销商品排行项"""

    platform: str
    platform_label: str
    ext_id: str = Field(..., description="平台商品ID（WB=nmId, Ozon=SKU）")
    name: str = Field("", description="商品名称/品类")
    gmv: float = 0
    units: int = 0


class DashboardSummary(BaseModel):
    """仪表盘总览响应"""

    range: DateRange
    kpi: KpiBlock
    trend: List[TrendPoint] = Field(default_factory=list)
    platforms: List[PlatformStat] = Field(default_factory=list)
    shops: List[ShopStat] = Field(default_factory=list)
    top_products: List[TopProduct] = Field(default_factory=list)
    generated_at: Optional[str] = Field(None, description="数据生成时间")
