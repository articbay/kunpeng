"""add Wildberries VOC feedback DWD table

Revision ID: c4f8a9d2e6b1
Revises: 91d7e6c4a2f8
Create Date: 2026-07-29 15:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "c4f8a9d2e6b1"
down_revision: Union[str, None] = "91d7e6c4a2f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "dwd_wb_voc_feedback_detail"


def upgrade() -> None:
    """Create the DWD table when absent and backfill it from ODS."""
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
            sa.Column(
                "feedback_id",
                sa.String(length=255),
                nullable=False,
                comment="评价ID",
            ),
            sa.Column(
                "created_date",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="评价创建时间",
            ),
            sa.Column(
                "supplier_article",
                sa.String(length=255),
                nullable=True,
                comment="卖家货号",
            ),
            sa.Column("nm_id", sa.BigInteger(), nullable=True, comment="WB货号"),
            sa.Column(
                "product_valuation",
                mysql.TINYINT(unsigned=True),
                nullable=True,
                comment="星级数量",
            ),
            sa.Column(
                "brand_name",
                sa.String(length=255),
                nullable=True,
                comment="品牌名称",
            ),
            sa.Column("text", sa.Text(), nullable=True, comment="评价文本"),
            sa.Column("pros", sa.Text(), nullable=True, comment="优点"),
            sa.Column("cons", sa.Text(), nullable=True, comment="缺点"),
            sa.Column(
                "user_name",
                sa.String(length=255),
                nullable=True,
                comment="用户姓名",
            ),
            sa.Column(
                "color",
                sa.String(length=100),
                nullable=True,
                comment="颜色",
            ),
            sa.Column(
                "size",
                sa.String(length=100),
                nullable=True,
                comment="尺码",
            ),
            sa.Column("answer", sa.Text(), nullable=True, comment="回复正文"),
            sa.Column(
                "parent_feedback_id",
                sa.String(length=255),
                nullable=True,
                comment="初始评价ID",
            ),
            sa.Column(
                "child_feedback_id",
                sa.String(length=255),
                nullable=True,
                comment="追加评价ID",
            ),
            sa.PrimaryKeyConstraint("shop_id", "feedback_id"),
            comment="Wildberries客户评价业务明细表",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index(
            "idx_dwd_wb_voc_feedback_created_date",
            TABLE_NAME,
            ["created_date"],
            unique=False,
        )
        op.create_index(
            "idx_dwd_wb_voc_feedback_nm_id",
            TABLE_NAME,
            ["nm_id"],
            unique=False,
        )
        op.create_index(
            "idx_dwd_wb_voc_feedback_supplier_article",
            TABLE_NAME,
            ["supplier_article"],
            unique=False,
        )

    if sa.inspect(bind).has_table("ods_wb_feedbacks"):
        op.execute(
            sa.text(
                """
                INSERT INTO dwd_wb_voc_feedback_detail (
                    shop_id,
                    feedback_id,
                    created_date,
                    supplier_article,
                    nm_id,
                    product_valuation,
                    brand_name,
                    text,
                    pros,
                    cons,
                    user_name,
                    color,
                    size,
                    answer,
                    parent_feedback_id,
                    child_feedback_id
                )
                SELECT
                    source_shop_id,
                    source_feedback_id,
                    source_created_date,
                    source_supplier_article,
                    source_nm_id,
                    source_product_valuation,
                    source_brand_name,
                    source_text,
                    source_pros,
                    source_cons,
                    source_user_name,
                    source_color,
                    source_size,
                    source_answer,
                    source_parent_feedback_id,
                    source_child_feedback_id
                FROM (
                    SELECT
                        shop_id AS source_shop_id,
                        feedback_id AS source_feedback_id,
                        created_date AS source_created_date,
                        supplier_article AS source_supplier_article,
                        nm_id AS source_nm_id,
                        product_valuation AS source_product_valuation,
                        brand_name AS source_brand_name,
                        text AS source_text,
                        pros AS source_pros,
                        cons AS source_cons,
                        user_name AS source_user_name,
                        color AS source_color,
                        size AS source_size,
                        JSON_UNQUOTE(JSON_EXTRACT(answer, '$.text'))
                            AS source_answer,
                        parent_feedback_id AS source_parent_feedback_id,
                        child_feedback_id AS source_child_feedback_id
                    FROM ods_wb_feedbacks
                ) AS source_rows
                ON DUPLICATE KEY UPDATE
                    created_date = source_created_date,
                    supplier_article = source_supplier_article,
                    nm_id = source_nm_id,
                    product_valuation = source_product_valuation,
                    brand_name = source_brand_name,
                    text = source_text,
                    pros = source_pros,
                    cons = source_cons,
                    user_name = source_user_name,
                    color = source_color,
                    size = source_size,
                    answer = source_answer,
                    parent_feedback_id = source_parent_feedback_id,
                    child_feedback_id = source_child_feedback_id
                """
            )
        )


def downgrade() -> None:
    """Drop the Wildberries VOC feedback DWD table."""
    if sa.inspect(op.get_bind()).has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
