"""新增Ozon客户声音DWD表

Revision ID: 425a70c7b20a
Revises: a4c8e2f6b9d1
Create Date: 2026-08-25 22:54:54
"""

import sqlalchemy as sa
from alembic import op

revision = "425a70c7b20a"
down_revision = "a4c8e2f6b9d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dwd_ozon_customer_voice_detail",
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("review_id", sa.String(length=64), nullable=False, comment="评价ID"),
        sa.Column(
            "month", sa.String(length=7), nullable=True, comment="月份（YYYY-MM）"
        ),
        sa.Column("offer_id", sa.String(length=255), nullable=True, comment="货号"),
        sa.Column("sku", sa.BigInteger(), nullable=True, comment="Ozon SKU"),
        sa.Column("product_name", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "product_name_cn", sa.Text(), nullable=True, comment="商品名称（中文）"
        ),
        sa.Column(
            "posting_number", sa.String(length=100), nullable=True, comment="订单号"
        ),
        sa.Column(
            "order_status", sa.String(length=50), nullable=True, comment="收货状态"
        ),
        sa.Column(
            "order_status_cn",
            sa.String(length=255),
            nullable=True,
            comment="收货状态（中文）",
        ),
        sa.Column("review_text", sa.Text(), nullable=True, comment="评价文本"),
        sa.Column(
            "review_text_cn", sa.Text(), nullable=True, comment="评价文本（中文）"
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="发布日期",
        ),
        sa.Column(
            "review_status", sa.String(length=50), nullable=True, comment="评价状态"
        ),
        sa.Column(
            "review_status_cn",
            sa.String(length=255),
            nullable=True,
            comment="评价状态（中文）",
        ),
        sa.Column("rating", sa.Integer(), nullable=True, comment="评分（1-5）"),
        sa.Column("photos_amount", sa.Integer(), nullable=True, comment="照片数量"),
        sa.Column("videos_amount", sa.Integer(), nullable=True, comment="视频数量"),
        sa.Column("comments_amount", sa.Integer(), nullable=True, comment="评论回应数"),
        sa.PrimaryKeyConstraint("shop_id", "review_id"),
        comment="Ozon客户声音评价业务明细表",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "idx_dwd_ozon_customer_voice_offer",
        "dwd_ozon_customer_voice_detail",
        ["offer_id"],
    )
    op.create_index(
        "idx_dwd_ozon_customer_voice_published",
        "dwd_ozon_customer_voice_detail",
        ["published_at"],
    )
    op.create_index(
        "idx_dwd_ozon_customer_voice_sku", "dwd_ozon_customer_voice_detail", ["sku"]
    )
    op.create_index(
        "idx_dwd_ozon_customer_voice_status",
        "dwd_ozon_customer_voice_detail",
        ["review_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dwd_ozon_customer_voice_status",
        table_name="dwd_ozon_customer_voice_detail",
    )
    op.drop_index(
        "idx_dwd_ozon_customer_voice_sku", table_name="dwd_ozon_customer_voice_detail"
    )
    op.drop_index(
        "idx_dwd_ozon_customer_voice_published",
        table_name="dwd_ozon_customer_voice_detail",
    )
    op.drop_index(
        "idx_dwd_ozon_customer_voice_offer", table_name="dwd_ozon_customer_voice_detail"
    )
    op.drop_table("dwd_ozon_customer_voice_detail")
