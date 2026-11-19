"""删除竞品抓取相关数据表(competitor 模块下线)

背景：竞品抓取功能属于二期内容，本期交接前整体下线。对应的后端代码、
前端页面与 scrapers/ 抓取包已删除，这里同步删除数据库中遗留的 4 张表：
  - competitor_scrape_task_items（抓取任务条目，外键指向 tasks/products）
  - competitor_reviews（竞品评论，外键指向 products）
  - competitor_scrape_tasks（抓取任务）
  - competitor_products（竞品商品）

删除顺序：先删带外键的子表，再删父表，避免外键约束报错。
downgrade 精确重建这 4 张表（与 baseline 定义保持一致），保证可回滚。

Revision ID: b0c2eb2aaa42
Revises: 6a02e2a56732
Create Date: 2026-07-14 13:51:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b0c2eb2aaa42"
down_revision = "6a02e2a56732"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 先删子表（含外键），再删父表
    op.drop_table("competitor_scrape_task_items")
    op.drop_table("competitor_reviews")
    op.drop_table("competitor_scrape_tasks")
    op.drop_table("competitor_products")


def downgrade() -> None:
    # 按父表 -> 子表顺序重建（与 baseline 迁移定义一致）
    op.create_table(
        "competitor_products",
        sa.Column(
            "id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column(
            "platform",
            sa.String(length=50),
            nullable=False,
            comment="平台(wildberries, ozon)",
        ),
        sa.Column(
            "product_id", sa.String(length=100), nullable=False, comment="平台商品ID"
        ),
        sa.Column(
            "category_id",
            sa.String(length=100),
            nullable=True,
            comment="抓取时的类目ID",
        ),
        sa.Column("url", sa.String(length=2000), nullable=True, comment="商品页面URL"),
        sa.Column("title", sa.String(length=1000), nullable=True, comment="商品名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="商品详细介绍"),
        sa.Column(
            "main_image_url", sa.String(length=2000), nullable=True, comment="主图URL"
        ),
        sa.Column(
            "image_urls", sa.JSON(), nullable=True, comment="所有图片URL列表(JSON数组)"
        ),
        sa.Column(
            "price",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="当前价格",
        ),
        sa.Column(
            "original_price",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="原价",
        ),
        sa.Column(
            "rating", sa.Numeric(precision=3, scale=2), nullable=True, comment="评分"
        ),
        sa.Column("review_count", sa.Integer(), nullable=True, comment="评论数"),
        sa.Column("brand", sa.String(length=500), nullable=True, comment="品牌"),
        sa.Column("seller", sa.String(length=500), nullable=True, comment="卖家"),
        sa.Column("specs", sa.JSON(), nullable=True, comment="商品规格参数(JSON对象)"),
        sa.Column("raw_data", sa.JSON(), nullable=True, comment="原始抓取数据(JSON)"),
        sa.Column(
            "scraped_at", sa.DateTime(timezone=True), nullable=True, comment="抓取时间"
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "platform", "product_id", name="uq_competitor_product_platform_pid"
        ),
        comment="竞品商品表",
    )
    op.create_index(
        "idx_competitor_platform_scraped",
        "competitor_products",
        ["platform", "scraped_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_products_id"), "competitor_products", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_competitor_products_platform"),
        "competitor_products",
        ["platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_products_product_id"),
        "competitor_products",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_products_scraped_at"),
        "competitor_products",
        ["scraped_at"],
        unique=False,
    )

    op.create_table(
        "competitor_scrape_tasks",
        sa.Column(
            "id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column(
            "platform",
            sa.String(length=50),
            nullable=False,
            comment="平台: wildberries/ozon",
        ),
        sa.Column(
            "task_type",
            sa.String(length=50),
            nullable=False,
            comment="任务类型: search/product",
        ),
        sa.Column(
            "keyword", sa.String(length=500), nullable=True, comment="搜索关键词"
        ),
        sa.Column(
            "target_url",
            sa.String(length=2000),
            nullable=True,
            comment="单商品任务的 URL",
        ),
        sa.Column("params", sa.JSON(), nullable=True, comment="任务参数 (JSON)"),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            comment="状态: pending/running/success/partial_success/failed",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="任务失败原因"),
        sa.Column(
            "requested_count", sa.Integer(), nullable=True, comment="计划抓取数量"
        ),
        sa.Column(
            "searched_count", sa.Integer(), nullable=False, comment="搜索到的商品数"
        ),
        sa.Column("saved_count", sa.Integer(), nullable=False, comment="入库成功数"),
        sa.Column("failed_count", sa.Integer(), nullable=False, comment="入库失败数"),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间"
        ),
        sa.Column(
            "finished_at", sa.DateTime(timezone=True), nullable=True, comment="完成时间"
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="竞品抓取任务表",
    )
    op.create_index(
        "idx_competitor_task_status_created",
        "competitor_scrape_tasks",
        ["status", "create_time"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_scrape_tasks_id"),
        "competitor_scrape_tasks",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_scrape_tasks_keyword"),
        "competitor_scrape_tasks",
        ["keyword"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_scrape_tasks_platform"),
        "competitor_scrape_tasks",
        ["platform"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_scrape_tasks_status"),
        "competitor_scrape_tasks",
        ["status"],
        unique=False,
    )

    op.create_table(
        "competitor_reviews",
        sa.Column(
            "id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column("product_id", sa.Integer(), nullable=False, comment="竞品商品ID"),
        sa.Column(
            "platform_review_id",
            sa.String(length=100),
            nullable=True,
            comment="平台评论ID",
        ),
        sa.Column("rating", sa.Integer(), nullable=True, comment="评分(1-5)"),
        sa.Column("content", sa.Text(), nullable=True, comment="评论内容"),
        sa.Column(
            "images", sa.JSON(), nullable=True, comment="评论图片URL列表(JSON数组)"
        ),
        sa.Column(
            "author_name", sa.String(length=500), nullable=True, comment="作者名称"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=True, comment="评论时间"
        ),
        sa.Column(
            "scraped_at", sa.DateTime(timezone=True), nullable=True, comment="抓取时间"
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["competitor_products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id", "platform_review_id", name="uniq_competitor_review"
        ),
        comment="竞品评论表",
    )
    op.create_index(
        "idx_competitor_review_product_id",
        "competitor_reviews",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_reviews_id"), "competitor_reviews", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_competitor_reviews_platform_review_id"),
        "competitor_reviews",
        ["platform_review_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_reviews_product_id"),
        "competitor_reviews",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "competitor_scrape_task_items",
        sa.Column(
            "id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column("task_id", sa.Integer(), nullable=False, comment="任务ID"),
        sa.Column("platform", sa.String(length=50), nullable=False, comment="平台"),
        sa.Column(
            "platform_product_id",
            sa.String(length=100),
            nullable=True,
            comment="平台商品ID",
        ),
        sa.Column("url", sa.String(length=2000), nullable=True, comment="商品页URL"),
        sa.Column("title", sa.String(length=1000), nullable=True, comment="商品名称"),
        sa.Column("brand", sa.String(length=500), nullable=True, comment="品牌"),
        sa.Column(
            "main_image_url", sa.String(length=2000), nullable=True, comment="主图URL"
        ),
        sa.Column(
            "price",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="价格快照",
        ),
        sa.Column(
            "rating",
            sa.Numeric(precision=3, scale=2),
            nullable=True,
            comment="评分快照",
        ),
        sa.Column("review_count", sa.Integer(), nullable=True, comment="评价数快照"),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            comment="条目状态: pending/success/failed",
        ),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column(
            "competitor_product_id",
            sa.Integer(),
            nullable=True,
            comment="关联的竞品商品ID",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.ForeignKeyConstraint(
            ["competitor_product_id"], ["competitor_products.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["competitor_scrape_tasks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="竞品抓取任务条目表",
    )
    op.create_index(
        "idx_competitor_task_item_task",
        "competitor_scrape_task_items",
        ["task_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_scrape_task_items_competitor_product_id"),
        "competitor_scrape_task_items",
        ["competitor_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_scrape_task_items_id"),
        "competitor_scrape_task_items",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_scrape_task_items_platform_product_id"),
        "competitor_scrape_task_items",
        ["platform_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competitor_scrape_task_items_task_id"),
        "competitor_scrape_task_items",
        ["task_id"],
        unique=False,
    )
