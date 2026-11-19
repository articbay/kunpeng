"""新增WB财务结算明细DWD表

Revision ID: c9f0a7791118
Revises: 279c3844ce06
Create Date: 2026-07-29 17:26:33.512347

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c9f0a7791118"
down_revision = "279c3844ce06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dwd_wb_sales_report_detail",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
            comment="主键ID",
        ),
        sa.Column(
            "source_ods_id",
            sa.BigInteger(),
            nullable=False,
            comment="来源 ods_wb_sales_reports.id",
        ),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="店铺ID"),
        sa.Column(
            "date_from",
            sa.Date(),
            nullable=False,
            comment="财务报告周开始日期",
        ),
        sa.Column(
            "rrd_id",
            sa.BigInteger(),
            nullable=False,
            comment="财务结算明细唯一编号",
        ),
        sa.Column("gi_id", sa.BigInteger(), nullable=True, comment="供货编号"),
        sa.Column(
            "subject_name",
            sa.String(length=255),
            nullable=True,
            comment="商品品类",
        ),
        sa.Column("nm_id", sa.BigInteger(), nullable=True, comment="WB商品编号"),
        sa.Column(
            "brand_name",
            sa.String(length=255),
            nullable=True,
            comment="品牌",
        ),
        sa.Column(
            "vendor_code",
            sa.String(length=255),
            nullable=True,
            comment="卖家商品编号",
        ),
        sa.Column("title", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "tech_size",
            sa.String(length=100),
            nullable=True,
            comment="尺码",
        ),
        sa.Column(
            "sku",
            sa.String(length=255),
            nullable=True,
            comment="条形码",
        ),
        sa.Column(
            "doc_type_name",
            sa.String(length=255),
            nullable=True,
            comment="文档类型",
        ),
        sa.Column(
            "seller_oper_name",
            sa.String(length=255),
            nullable=True,
            comment="付款依据",
        ),
        sa.Column(
            "order_dt",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="买家下单日期",
        ),
        sa.Column(
            "sale_dt",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="销售日期",
        ),
        sa.Column("quantity", sa.Integer(), nullable=True, comment="数量"),
        sa.Column(
            "retail_price",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="零售价",
        ),
        sa.Column(
            "retail_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="WB销售商品金额",
        ),
        sa.Column(
            "sale_percent",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="协商商品折扣比例",
        ),
        sa.Column(
            "seller_promo",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="促销码比例",
        ),
        sa.Column(
            "product_discount_for_report",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="最终折扣比例",
        ),
        sa.Column(
            "retail_price_with_disc",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="包含最终折扣的零售价格",
        ),
        sa.Column(
            "sup_rating_up",
            sa.Integer(),
            nullable=True,
            comment="卖家评级佣金减免比例",
        ),
        sa.Column(
            "is_kgvp_v2",
            sa.Integer(),
            nullable=True,
            comment="促销活动佣金减免标识",
        ),
        sa.Column(
            "spp",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="常客折扣比例",
        ),
        sa.Column(
            "commission_percent",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="WB佣金比例",
        ),
        sa.Column(
            "kvw_base",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="WB基础佣金比例（不含增值税）",
        ),
        sa.Column(
            "kvw",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="WB最终佣金比例（不含增值税）",
        ),
        sa.Column(
            "ppvz_sales_commission",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="未扣代理服务费和增值税的销售佣金",
        ),
        sa.Column(
            "ppvz_reward",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="取件和退货服务费用赔偿",
        ),
        sa.Column(
            "acquiring_fee",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="收单或支付结算服务费",
        ),
        sa.Column(
            "acquiring_percent",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="收单或支付结算服务费率",
        ),
        sa.Column(
            "payment_processing",
            sa.String(length=100),
            nullable=True,
            comment="收单或支付结算付款类型",
        ),
        sa.Column(
            "vw",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="WB佣金（不含增值税）",
        ),
        sa.Column(
            "vw_nds",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="WB佣金增值税",
        ),
        sa.Column(
            "for_pay",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="支付给卖家的已售商品金额",
        ),
        sa.Column(
            "delivery_amount",
            sa.Integer(),
            nullable=True,
            comment="交付数量",
        ),
        sa.Column(
            "return_amount",
            sa.Integer(),
            nullable=True,
            comment="退货数量",
        ),
        sa.Column(
            "delivery_service",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="向买家交付货物的服务费",
        ),
        sa.Column(
            "dlv_prc",
            sa.Integer(),
            nullable=True,
            comment="仓库供应固定系数",
        ),
        sa.Column(
            "fix_tariff_date_from",
            sa.String(length=50),
            nullable=True,
            comment="固定费率开始日期",
        ),
        sa.Column(
            "fix_tariff_date_to",
            sa.String(length=50),
            nullable=True,
            comment="固定费率结束日期",
        ),
        sa.Column(
            "srv_dbs",
            sa.Boolean(),
            nullable=True,
            comment="付费配送服务标识",
        ),
        sa.Column(
            "penalty",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="罚款总额",
        ),
        sa.Column(
            "additional_payment",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="WB佣金调整",
        ),
        sa.Column(
            "bonus_type_name",
            sa.String(length=255),
            nullable=True,
            comment="物流、罚款及WB佣金调整类型",
        ),
        sa.Column("shk_id", sa.BigInteger(), nullable=True, comment="FBS标签"),
        sa.Column(
            "acquiring_bank",
            sa.String(length=255),
            nullable=True,
            comment="收单银行名称",
        ),
        sa.Column(
            "ppvz_office_id",
            sa.BigInteger(),
            nullable=True,
            comment="办公室编号",
        ),
        sa.Column(
            "ppvz_office_name",
            sa.Text(),
            nullable=True,
            comment="送货点名称",
        ),
        sa.Column(
            "ppvz_supplier_inn",
            sa.String(length=50),
            nullable=True,
            comment="合作站点税号",
        ),
        sa.Column(
            "ppvz_supplier_name",
            sa.String(length=255),
            nullable=True,
            comment="合作伙伴",
        ),
        sa.Column(
            "office_name",
            sa.String(length=255),
            nullable=True,
            comment="仓库",
        ),
        sa.Column(
            "country",
            sa.String(length=50),
            nullable=True,
            comment="国家",
        ),
        sa.Column(
            "gi_box_type_name",
            sa.String(length=100),
            nullable=True,
            comment="箱型",
        ),
        sa.Column(
            "declaration_number",
            sa.String(length=255),
            nullable=True,
            comment="报关单号",
        ),
        sa.Column(
            "order_id",
            sa.BigInteger(),
            nullable=True,
            comment="配货任务编号",
        ),
        sa.Column(
            "kiz",
            sa.String(length=255),
            nullable=True,
            comment="标记编码，来源 row_data.kiz",
        ),
        sa.Column(
            "sticker_id",
            sa.String(length=255),
            nullable=True,
            comment="仓库标签",
        ),
        sa.Column(
            "srid",
            sa.String(length=255),
            nullable=True,
            comment="SRID",
        ),
        sa.Column(
            "rebill_logistic_cost",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="运输或仓储费用补偿",
        ),
        sa.Column(
            "rebill_logistic_org",
            sa.String(length=100),
            nullable=True,
            comment="承运人",
        ),
        sa.Column(
            "paid_storage",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="仓储费",
        ),
        sa.Column(
            "deduction",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="扣款",
        ),
        sa.Column(
            "paid_acceptance",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="入库验收操作费",
        ),
        sa.Column(
            "is_b2b",
            sa.Boolean(),
            nullable=True,
            comment="向法人实体销售标识",
        ),
        sa.Column(
            "trbx_id",
            sa.String(length=100),
            nullable=True,
            comment="商品处理箱号",
        ),
        sa.Column(
            "installment_cofinancing_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="联合融资计划折扣",
        ),
        sa.Column(
            "wibes_discount_percent",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="Wibes折扣比例",
        ),
        sa.Column(
            "cashback_discount",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="忠诚度计划折扣补偿",
        ),
        sa.Column(
            "cashback_commission_change",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="忠诚度计划参与费用",
        ),
        sa.Column(
            "cashback_amount",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="已扣除的忠诚度积分金额",
        ),
        sa.Column(
            "order_uid",
            sa.String(length=255),
            nullable=True,
            comment="订单购物车ID",
        ),
        sa.Column(
            "payment_schedule",
            sa.String(length=50),
            nullable=True,
            comment="一次性结算周期变更",
        ),
        sa.Column(
            "delivery_method",
            sa.String(length=255),
            nullable=True,
            comment="商品配送方式",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="更新时间",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "rrd_id",
            name="uq_dwd_wb_sales_report_shop_rrd",
        ),
        sa.UniqueConstraint(
            "source_ods_id",
            name="uq_dwd_wb_sales_report_source_ods",
        ),
        comment="Wildberries 财务结算明细 DWD 表",
    )
    op.create_index(
        "idx_dwd_wb_sales_report_date_from",
        "dwd_wb_sales_report_detail",
        ["date_from"],
        unique=False,
    )
    op.create_index(
        "idx_dwd_wb_sales_report_nm_id",
        "dwd_wb_sales_report_detail",
        ["nm_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dwd_wb_sales_report_nm_id",
        table_name="dwd_wb_sales_report_detail",
    )
    op.drop_index(
        "idx_dwd_wb_sales_report_date_from",
        table_name="dwd_wb_sales_report_detail",
    )
    op.drop_table("dwd_wb_sales_report_detail")
