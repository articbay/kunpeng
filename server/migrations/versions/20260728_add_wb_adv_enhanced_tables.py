"""add_wb_adv_enhanced_tables: 标记WB广告增强数据表已创建

Revision ID: 20260728_add_wb_adv
Revises: 91d7e6c4a2f8
Create Date: 2026-07-28

这是一个占位迁移。这8张表已经在数据库中存在了：
1. ods_wb_norm_query_bids - 标准查询竞价表
2. ods_wb_norm_query_minus - 排除关键词表
3. ods_wb_norm_query_list - 标准查询列表
4. ods_wb_norm_query_stats - 标准查询统计表
5. ods_wb_promotion_counts - 促销计数表
6. ods_wb_bid_recommendations - 竞价推荐表
7. ods_wb_advert_full_stats - 广告完整统计表
8. ods_wb_adverts_v2 - 广告列表V2表

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260728_add_wb_adv'
down_revision = '91d7e6c4a2f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 表已经在数据库中存在，不做任何操作
    pass


def downgrade() -> None:
    # 不执行删除表操作，保留数据
    pass
