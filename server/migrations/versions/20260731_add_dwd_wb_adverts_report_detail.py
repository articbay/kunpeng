"""add_dwd_wb_adverts_report_detail: 新增Wildberries广告周度报表明细表

Revision ID: 20260731_add_dwd_wb_report
Revises: 2d67ff2f44ca
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '20260731_add_dwd_wb_report'
down_revision = '2d67ff2f44ca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # DWD层 - Wildberries广告周度报表明细表
    op.create_table(
        'dwd_wb_adverts_report_detail',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('shop_id', sa.BigInteger(), nullable=False, comment='店铺ID'),
        sa.Column('week', sa.String(length=20), nullable=False, comment='周度标识 (如 week202530)'),
        sa.Column('advert_id', sa.BigInteger(), nullable=False, comment='广告活动ID'),
        sa.Column('advert_name', sa.String(length=500), nullable=True, comment='广告活动名称'),
        sa.Column('advert_status', sa.Integer(), nullable=True, comment='活动状态 (0-暂停, 1-进行中)'),
        sa.Column('advert_status_label', sa.String(length=50), nullable=True, comment='活动状态标签'),
        sa.Column('paid_views', sa.Integer(), nullable=False, default=0, comment='付费曝光量'),
        sa.Column('paid_clicks', sa.Integer(), nullable=False, default=0, comment='付费点击量'),
        sa.Column('atbs', sa.Integer(), nullable=False, default=0, comment='加购次数'),
        sa.Column('orders', sa.Integer(), nullable=False, default=0, comment='订单次数'),
        sa.Column('ctr', sa.Numeric(precision=8, scale=4), nullable=True, comment='点击率 (%)'),
        sa.Column('cpc', sa.Numeric(precision=12, scale=4), nullable=True, comment='单次点击成本 (₽)'),
        sa.Column('cr', sa.Numeric(precision=8, scale=4), nullable=True, comment='转化率 (%)'),
        sa.Column('sum_cost', sa.Numeric(precision=18, scale=2), nullable=True, comment='总花费 (₽)'),
        sa.Column('sum_price', sa.Numeric(precision=18, scale=2), nullable=True, comment='总销售金额 (₽)'),
        sa.Column('create_time', sa.DateTime(timezone=True), server_default=sa.text('(now())'), nullable=False, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shop_id', 'week', 'advert_id', name='uq_dwd_adreport_shop_week_advert'),
        comment='Wildberries 广告周度报表明细表',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='Wildberries 广告周度报表明细表',
        mysql_default_charset='utf8mb4',
        mysql_engine='InnoDB'
    )
    op.create_index('idx_dwd_adreport_shop_id', 'dwd_wb_adverts_report_detail', ['shop_id'], unique=False)
    op.create_index('idx_dwd_adreport_week', 'dwd_wb_adverts_report_detail', ['week'], unique=False)
    op.create_index('idx_dwd_adreport_advert_id', 'dwd_wb_adverts_report_detail', ['advert_id'], unique=False)
    op.create_index('idx_dwd_adreport_advert_status', 'dwd_wb_adverts_report_detail', ['advert_status'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_dwd_adreport_advert_status', table_name='dwd_wb_adverts_report_detail')
    op.drop_index('idx_dwd_adreport_advert_id', table_name='dwd_wb_adverts_report_detail')
    op.drop_index('idx_dwd_adreport_week', table_name='dwd_wb_adverts_report_detail')
    op.drop_index('idx_dwd_adreport_shop_id', table_name='dwd_wb_adverts_report_detail')
    op.drop_table('dwd_wb_adverts_report_detail')
