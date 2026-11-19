"""add WB DWD Chinese translation fields

Revision ID: 9b2f4d6e8a10
Revises: f6a8c2d4e7b9
Create Date: 2026-08-03 16:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9b2f4d6e8a10"
down_revision: Union[str, None] = "f6a8c2d4e7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_COLUMNS = {
    "dwd_wb_voc_feedback_detail": (
        sa.Column("text_cn", sa.Text(), nullable=True, comment="评价文本（中文）"),
        sa.Column("pros_cn", sa.Text(), nullable=True, comment="优点（中文）"),
        sa.Column("cons_cn", sa.Text(), nullable=True, comment="缺点（中文）"),
        sa.Column("color_cn", sa.String(100), nullable=True, comment="颜色（中文）"),
        sa.Column("size_cn", sa.String(100), nullable=True, comment="尺码（中文）"),
        sa.Column("answer_cn", sa.Text(), nullable=True, comment="回复正文（中文）"),
    ),
    "dwd_wb_voc_question_detail": (
        sa.Column("text_cn", sa.Text(), nullable=True, comment="问题文本（中文）"),
        sa.Column("answer_cn", sa.Text(), nullable=True, comment="回复（中文）"),
    ),
    "dwd_wb_return_detail": (
        sa.Column(
            "subject_name_cn", sa.String(255), nullable=True, comment="商品品类（中文）"
        ),
        sa.Column("status_cn", sa.String(255), nullable=True, comment="状态（中文）"),
        sa.Column(
            "return_type_cn", sa.String(255), nullable=True, comment="退货类型（中文）"
        ),
        sa.Column(
            "reason_cn", sa.String(500), nullable=True, comment="退货原因（中文）"
        ),
        sa.Column(
            "dst_office_address_cn",
            sa.String(500),
            nullable=True,
            comment="地址（中文）",
        ),
    ),
    "dwd_wb_order_detail": (
        sa.Column("title_cn", sa.Text(), nullable=True, comment="商品名称（中文）"),
        sa.Column(
            "tech_size_cn", sa.String(100), nullable=True, comment="尺寸（中文）"
        ),
        sa.Column("color_cn", sa.String(100), nullable=True, comment="颜色（中文）"),
        sa.Column(
            "warehouse_name_cn",
            sa.String(255),
            nullable=True,
            comment="卖家仓库（中文）",
        ),
        sa.Column(
            "wb_status_cn", sa.String(100), nullable=True, comment="工作状态（中文）"
        ),
        sa.Column("address_cn", sa.Text(), nullable=True, comment="地址（中文）"),
        sa.Column(
            "delivery_type_cn",
            sa.String(50),
            nullable=True,
            comment="配送类型（中文）",
        ),
        sa.Column(
            "supplier_status_cn",
            sa.String(100),
            nullable=True,
            comment="卖家处理状态（中文）",
        ),
    ),
    "dwd_wb_order_statistics_detail": (
        sa.Column(
            "warehouse_name_cn",
            sa.String(255),
            nullable=True,
            comment="仓库名称（中文）",
        ),
        sa.Column(
            "country_name_cn", sa.String(255), nullable=True, comment="国家（中文）"
        ),
        sa.Column(
            "oblast_okrug_name_cn",
            sa.String(255),
            nullable=True,
            comment="联邦管区（中文）",
        ),
        sa.Column(
            "region_name_cn", sa.String(255), nullable=True, comment="地区（中文）"
        ),
        sa.Column(
            "category_cn", sa.String(255), nullable=True, comment="商品分类（中文）"
        ),
        sa.Column(
            "subject_name_cn",
            sa.String(255),
            nullable=True,
            comment="商品品类（中文）",
        ),
        sa.Column(
            "tech_size_cn", sa.String(100), nullable=True, comment="尺码（中文）"
        ),
    ),
}


def upgrade() -> None:
    for table_name, columns in TABLE_COLUMNS.items():
        for column in columns:
            op.add_column(table_name, column)


def downgrade() -> None:
    for table_name, columns in reversed(TABLE_COLUMNS.items()):
        for column in reversed(columns):
            op.drop_column(table_name, column.name)
