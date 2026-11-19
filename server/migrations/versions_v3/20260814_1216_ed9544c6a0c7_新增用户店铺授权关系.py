"""新增用户店铺授权关系。

Revision ID: ed9544c6a0c7
Revises: c3f1a9e7b2d4
Create Date: 2026-08-14 12:16:53
"""

import sqlalchemy as sa

from alembic import op

revision = "ed9544c6a0c7"
down_revision = "c3f1a9e7b2d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_shop_access",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="被授权用户ID"),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="授权店铺ID"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="更新时间",
        ),
        sa.ForeignKeyConstraint(
            ["shop_id"],
            ["shops.id"],
            name="fk_user_shop_access_shop_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_shop_access_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "shop_id", name="uq_user_shop_access_user_shop"),
        comment="用户店铺只读授权关系",
    )
    op.create_index(
        "idx_user_shop_access_user_shop",
        "user_shop_access",
        ["user_id", "shop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_shop_access_shop_id"),
        "user_shop_access",
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_shop_access_user_id"),
        "user_shop_access",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    raise RuntimeError(
        "为避免删除用户店铺授权数据，本迁移不支持直接降级；请使用发布备份回滚。"
    )
