"""
Ozon Pydantic Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


# ==================== 基础响应模型 ====================

class OzonBaseResponse(BaseModel):
    """基础响应模型"""
    model_config = ConfigDict(from_attributes=True)


# ==================== 订单相关 ====================

class OzonPostingBase(OzonBaseResponse):
    """订单数据基础"""
    posting_number: Optional[str] = None
    order_id: Optional[int] = None
    status: Optional[str] = None
    substatus: Optional[str] = None
    in_process_at: Optional[datetime] = None
    shipment_date: Optional[datetime] = None
    delivering_date: Optional[datetime] = None


class OzonPostingCreate(OzonPostingBase):
    """创建订单数据"""
    shop_id: int


class OzonPostingResponse(OzonPostingBase):
    """订单数据响应"""
    id: int
    shop_id: int
    create_time: datetime
    update_time: Optional[datetime] = None


# ==================== 商品相关 ====================

class OzonProductBase(OzonBaseResponse):
    """商品数据基础"""
    product_id: Optional[int] = None
    offer_id: Optional[str] = None
    name: Optional[str] = None
    price: Optional[Decimal] = None
    old_price: Optional[Decimal] = None
    premium_price: Optional[Decimal] = None
    stock: Optional[int] = None
    visibility: Optional[str] = None


class OzonProductCreate(OzonProductBase):
    """创建商品数据"""
    shop_id: int


class OzonProductResponse(OzonProductBase):
    """商品数据响应"""
    id: int
    shop_id: int
    create_time: datetime
    update_time: Optional[datetime] = None


# ==================== 退货相关 ====================

class OzonReturnBase(OzonBaseResponse):
    """退货数据基础"""
    return_id: Optional[int] = None
    posting_number: Optional[str] = None
    product_id: Optional[int] = None
    offer_id: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    return_reason: Optional[str] = None
    order_date: Optional[datetime] = None
    return_date: Optional[datetime] = None
    price: Optional[Decimal] = None


class OzonReturnCreate(OzonReturnBase):
    """创建退货数据"""
    shop_id: int


class OzonReturnResponse(OzonReturnBase):
    """退货数据响应"""
    id: int
    shop_id: int
    create_time: datetime
    update_time: Optional[datetime] = None


# ==================== 财务相关 ====================

class OzonFinanceTransactionBase(OzonBaseResponse):
    """财务交易基础"""
    transaction_id: Optional[str] = None
    operation_type: Optional[str] = None
    operation_type_name: Optional[str] = None
    posting_number: Optional[str] = None
    operation_date: Optional[datetime] = None
    order_date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    price: Optional[Decimal] = None
    product_id: Optional[int] = None
    offer_id: Optional[str] = None
    product_name: Optional[str] = None
    sku: Optional[int] = None
    quantity: Optional[int] = None
    warehouse_id: Optional[int] = None
    warehouse: Optional[str] = None


class OzonFinanceTransactionCreate(OzonFinanceTransactionBase):
    """创建财务交易"""
    shop_id: int


class OzonFinanceTransactionResponse(OzonFinanceTransactionBase):
    """财务交易响应"""
    id: int
    shop_id: int
    create_time: datetime
    update_time: Optional[datetime] = None


# ==================== 同步相关 ====================

class OzonSyncRequest(BaseModel):
    """同步请求"""
    shop_id: int
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None    # YYYY-MM-DD
    sync_types: Optional[List[str]] = None  # 要同步的数据类型: postings, products, returns, finance


class OzonSyncResponse(BaseModel):
    """同步响应"""
    status: str
    message: str
    synced_count: Optional[Dict[str, int]] = None
