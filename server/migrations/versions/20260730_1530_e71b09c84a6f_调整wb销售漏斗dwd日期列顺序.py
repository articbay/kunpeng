"""调整WB销售漏斗DWD日期列顺序

Revision ID: e71b09c84a6f
Revises: f4a7c2e91b3d
Create Date: 2026-07-30 15:30:00
"""

from alembic import op

revision = "e71b09c84a6f"
down_revision = "f4a7c2e91b3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """在 MySQL 中把日期范围移动到 shop_id 后面。"""
    if op.get_bind().dialect.name != "mysql":
        return

    op.execute(
        """
        ALTER TABLE dwd_wb_sales_funnel_detail
        MODIFY COLUMN date_from DATE NOT NULL COMMENT '统计开始日期'
        AFTER shop_id
        """
    )
    op.execute(
        """
        ALTER TABLE dwd_wb_sales_funnel_detail
        MODIFY COLUMN date_to DATE NOT NULL COMMENT '统计结束日期（技术字段）'
        AFTER date_from
        """
    )


def downgrade() -> None:
    """恢复首次建表迁移中的日期列顺序。"""
    if op.get_bind().dialect.name != "mysql":
        return

    op.execute(
        """
        ALTER TABLE dwd_wb_sales_funnel_detail
        MODIFY COLUMN date_from DATE NOT NULL COMMENT '统计开始日期'
        AFTER feedback_rating
        """
    )
    op.execute(
        """
        ALTER TABLE dwd_wb_sales_funnel_detail
        MODIFY COLUMN date_to DATE NOT NULL COMMENT '统计结束日期（技术字段）'
        AFTER date_from
        """
    )
