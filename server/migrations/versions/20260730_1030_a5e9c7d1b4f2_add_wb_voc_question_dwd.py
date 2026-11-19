"""add Wildberries VOC question DWD table

Revision ID: a5e9c7d1b4f2
Revises: c4f8a9d2e6b1
Create Date: 2026-07-30 10:30:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a5e9c7d1b4f2"
down_revision: Union[str, None] = "c4f8a9d2e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "dwd_wb_voc_question_detail"


def upgrade() -> None:
    """Create the DWD table when absent and backfill it from ODS."""
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
            sa.Column(
                "question_id",
                sa.String(length=255),
                nullable=False,
                comment="问题ID",
            ),
            sa.Column(
                "created_date",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="日期",
            ),
            sa.Column(
                "supplier_article",
                sa.String(length=255),
                nullable=True,
                comment="卖家货号",
            ),
            sa.Column("nm_id", sa.BigInteger(), nullable=True, comment="WB货号"),
            sa.Column(
                "brand_name",
                sa.String(length=255),
                nullable=True,
                comment="品牌名称",
            ),
            sa.Column("text", sa.Text(), nullable=True, comment="问题文本"),
            sa.Column("answer", sa.Text(), nullable=True, comment="回复"),
            sa.PrimaryKeyConstraint("shop_id", "question_id"),
            comment="Wildberries客户提问业务明细表",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index(
            "idx_dwd_wb_voc_question_created_date",
            TABLE_NAME,
            ["created_date"],
            unique=False,
        )
        op.create_index(
            "idx_dwd_wb_voc_question_nm_id",
            TABLE_NAME,
            ["nm_id"],
            unique=False,
        )
        op.create_index(
            "idx_dwd_wb_voc_question_supplier_article",
            TABLE_NAME,
            ["supplier_article"],
            unique=False,
        )

    if sa.inspect(bind).has_table("ods_wb_questions"):
        op.execute(
            sa.text(
                """
                INSERT INTO dwd_wb_voc_question_detail (
                    shop_id,
                    question_id,
                    created_date,
                    supplier_article,
                    nm_id,
                    brand_name,
                    text,
                    answer
                )
                SELECT
                    source_shop_id,
                    source_question_id,
                    source_created_date,
                    source_supplier_article,
                    source_nm_id,
                    source_brand_name,
                    source_text,
                    source_answer
                FROM (
                    SELECT
                        shop_id AS source_shop_id,
                        question_id AS source_question_id,
                        created_date AS source_created_date,
                        supplier_article AS source_supplier_article,
                        nm_id AS source_nm_id,
                        brand_name AS source_brand_name,
                        text AS source_text,
                        JSON_UNQUOTE(JSON_EXTRACT(answer, '$.text'))
                            AS source_answer
                    FROM ods_wb_questions
                ) AS source_rows
                ON DUPLICATE KEY UPDATE
                    created_date = source_created_date,
                    supplier_article = source_supplier_article,
                    nm_id = source_nm_id,
                    brand_name = source_brand_name,
                    text = source_text,
                    answer = source_answer
                """
            )
        )


def downgrade() -> None:
    """Drop the Wildberries VOC question DWD table."""
    if sa.inspect(op.get_bind()).has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
