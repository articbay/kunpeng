"""add name_zh to ods_ozon_finance_accrual_types + seed 115 中文名称

给应计类型字典表补中文名称列，并按 type_id 灌入 115 条中文翻译。
翻译基于官方英文/俄文名，专业术语需人工复核。

Revision ID: add_name_zh_20260706
Revises: add_seller_price_20260706
Create Date: 2026-07-06 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "add_name_zh_20260706"
down_revision = "add_seller_price_20260706"
branch_labels = None
depends_on = None

TABLE = "ods_ozon_finance_accrual_types"

# 中文映射复用 crud 层常量，避免两处维护
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "..", "src"))
from kunpeng.crud.ods.ozon.accrual_type_names import ACCRUAL_TYPE_NAME_ZH as NAME_ZH


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("name_zh", mysql.VARCHAR(length=255), nullable=True, comment="中文名称"),
    )
    conn = op.get_bind()
    stmt = sa.text(f"UPDATE {TABLE} SET name_zh = :zh WHERE type_id = :tid")
    for tid, zh in NAME_ZH.items():
        conn.execute(stmt, {"zh": zh, "tid": tid})


def downgrade() -> None:
    op.drop_column(TABLE, "name_zh")
