"""feat: 新增WB广告完整数据表(10张表)

Revision ID: add_wb_advert_full_20260723
Revises: b0c2eb2aaa42
Create Date: 2026-07-23

新增10张表：
1. dim_wb_advert_main - 广告活动主表(整合API2+API3)
2. dim_wb_normquery_main - 搜索词主表(整合API4+API5)
3. dim_wb_normquery_bid_recommend - 搜索词推荐出价表(API6)
4. dim_wb_advert_minus_words - 广告否定词表(API7)
5. dwd_wb_normquery_daily_stats - 搜索词日统计表(API8)
6. dws_wb_advert_daily_stats - 广告日汇总表(v1, API9)
7. dwd_wb_advert_fullstats_daily - 广告全量日明细表(v3, API10)
8. ods_wb_payment_history - 充值历史表(API11)
9. ods_wb_expense_history - 扣费历史表(API12)

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "add_wb_advert_full_20260723"
down_revision = "b0c2eb2aaa42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 广告活动主表
    op.create_table(
        "dim_wb_advert_main",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("advert_name", sa.String(length=500), nullable=True, comment="活动名称"),
        sa.Column("brand", sa.String(length=500), nullable=True, comment="品牌名"),
        sa.Column("advert_type", sa.Integer(), nullable=True, comment="活动类型（1=搜索，2=媒体）"),
        sa.Column("status", sa.Integer(), nullable=True, comment="活动状态码"),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=True, comment="活动创建时间"),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True, comment="活动结束时间"),
        sa.Column("total_budget", sa.Numeric(precision=18, scale=2), nullable=True, comment="活动总预算"),
        sa.Column("daily_limit", sa.Numeric(precision=18, scale=2), nullable=True, comment="日限额"),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=True, comment="活动最后更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "advert_id", name="uq_dim_advert_main_shop_advert"),
        comment="Wildberries 广告活动主维表",
    )
    op.create_index("idx_dim_advert_main_shop_id", "dim_wb_advert_main", ["shop_id"], unique=False)
    op.create_index("idx_dim_advert_main_advert_id", "dim_wb_advert_main", ["advert_id"], unique=False)
    op.create_index("idx_dim_advert_main_status", "dim_wb_advert_main", ["status"], unique=False)

    # 2. 搜索词主表
    op.create_table(
        "dim_wb_normquery_main",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="商品ID"),
        sa.Column("norm_query", sa.String(length=500), nullable=False, comment="搜索词"),
        sa.Column("status", sa.Integer(), nullable=True, comment="搜索词状态"),
        sa.Column("bid", sa.Numeric(precision=18, scale=2), nullable=True, comment="当前实际出价（卢布）"),
        sa.Column("bid_kopecks", sa.BigInteger(), nullable=True, comment="当前实际出价（戈比）"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="币种"),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=True, comment="同步时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "advert_id", "nm_id", "norm_query", name="uq_dim_normquery_main_shop_advert_nm_query"),
        comment="Wildberries 搜索词主维表",
    )
    op.create_index("idx_dim_normquery_main_shop_id", "dim_wb_normquery_main", ["shop_id"], unique=False)
    op.create_index("idx_dim_normquery_main_advert_id", "dim_wb_normquery_main", ["advert_id"], unique=False)
    op.create_index("idx_dim_normquery_main_nm_id", "dim_wb_normquery_main", ["nm_id"], unique=False)

    # 3. 搜索词推荐出价表
    op.create_table(
        "dim_wb_normquery_bid_recommend",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="商品ID"),
        sa.Column("norm_query", sa.String(length=500), nullable=False, comment="搜索词"),
        sa.Column("competitive_bid_kopecks", sa.BigInteger(), nullable=True, comment="行业竞争基准出价（戈比）"),
        sa.Column("leaders_bid_kopecks", sa.BigInteger(), nullable=True, comment="头部领先者出价（戈比）"),
        sa.Column("top2_bid_kopecks", sa.BigInteger(), nullable=True, comment="TOP2 位次出价（戈比）"),
        sa.Column("reach_max_bid_kopecks", sa.BigInteger(), nullable=True, comment="最大触达推荐出价（戈比）"),
        sa.Column("reach_medium_bid_kopecks", sa.BigInteger(), nullable=True, comment="中等触达推荐出价（戈比）"),
        sa.Column("reach_min_bid_kopecks", sa.BigInteger(), nullable=True, comment="最小触达推荐出价（戈比）"),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=True, comment="同步时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "advert_id", "nm_id", "norm_query", name="uq_dim_bid_recommend_shop_advert_nm_query"),
        comment="Wildberries 搜索词推荐出价表",
    )
    op.create_index("idx_dim_bid_recommend_shop_id", "dim_wb_normquery_bid_recommend", ["shop_id"], unique=False)
    op.create_index("idx_dim_bid_recommend_advert_id", "dim_wb_normquery_bid_recommend", ["advert_id"], unique=False)
    op.create_index("idx_dim_bid_recommend_nm_id", "dim_wb_normquery_bid_recommend", ["nm_id"], unique=False)

    # 4. 广告否定词表
    op.create_table(
        "dim_wb_advert_minus_words",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="商品ID"),
        sa.Column("minus_word", sa.String(length=500), nullable=False, comment="否定词"),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=True, comment="同步时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "advert_id", "nm_id", "minus_word", name="uq_dim_minus_words_shop_advert_nm_word"),
        comment="Wildberries 广告否定词维表",
    )
    op.create_index("idx_dim_minus_words_shop_id", "dim_wb_advert_minus_words", ["shop_id"], unique=False)
    op.create_index("idx_dim_minus_words_advert_id", "dim_wb_advert_minus_words", ["advert_id"], unique=False)
    op.create_index("idx_dim_minus_words_nm_id", "dim_wb_advert_minus_words", ["nm_id"], unique=False)

    # 5. 搜索词日统计表
    op.create_table(
        "dwd_wb_normquery_daily_stats",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="商品ID"),
        sa.Column("stat_date", sa.Date(), nullable=False, comment="统计日期"),
        sa.Column("norm_query", sa.String(length=500), nullable=False, comment="搜索词"),
        sa.Column("views", sa.Integer(), nullable=True, comment="曝光次数"),
        sa.Column("clicks", sa.Integer(), nullable=True, comment="点击次数"),
        sa.Column("atbs", sa.Integer(), nullable=True, comment="加购次数"),
        sa.Column("orders", sa.Integer(), nullable=True, comment="订单次数"),
        sa.Column("ctr", sa.Numeric(precision=8, scale=4), nullable=True, comment="点击率（%）"),
        sa.Column("cpc", sa.Numeric(precision=12, scale=4), nullable=True, comment="单次点击成本（戈比）"),
        sa.Column("cpm", sa.Numeric(precision=12, scale=4), nullable=True, comment="千次展示成本（戈比）"),
        sa.Column("avg_pos", sa.Numeric(precision=8, scale=2), nullable=True, comment="平均广告排名"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="币种"),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=True, comment="入库时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "advert_id", "nm_id", "stat_date", "norm_query", name="uq_dwd_normquery_stats_shop_advert_nm_date_query"),
        comment="Wildberries 搜索词日统计明细表",
    )
    op.create_index("idx_dwd_normquery_stats_shop_id", "dwd_wb_normquery_daily_stats", ["shop_id"], unique=False)
    op.create_index("idx_dwd_normquery_stats_advert_id", "dwd_wb_normquery_daily_stats", ["advert_id"], unique=False)
    op.create_index("idx_dwd_normquery_stats_nm_id", "dwd_wb_normquery_daily_stats", ["nm_id"], unique=False)
    op.create_index("idx_dwd_normquery_stats_stat_date", "dwd_wb_normquery_daily_stats", ["stat_date"], unique=False)

    # 6. 广告日汇总表(v1)
    op.create_table(
        "dws_wb_advert_daily_stats",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="商品ID"),
        sa.Column("stat_date", sa.Date(), nullable=False, comment="统计日期"),
        sa.Column("app_type", sa.String(length=50), nullable=False, comment="终端类型"),
        sa.Column("advert_type", sa.Integer(), nullable=True, comment="广告类型"),
        sa.Column("place", sa.String(length=100), nullable=True, comment="广告位"),
        sa.Column("views", sa.Integer(), nullable=True, comment="曝光次数"),
        sa.Column("clicks", sa.Integer(), nullable=True, comment="点击次数"),
        sa.Column("atbs", sa.Integer(), nullable=True, comment="加购次数"),
        sa.Column("orders", sa.Integer(), nullable=True, comment="订单次数"),
        sa.Column("ctr", sa.Numeric(precision=8, scale=4), nullable=True, comment="点击率（%）"),
        sa.Column("cr", sa.Numeric(precision=8, scale=4), nullable=True, comment="转化率（%）"),
        sa.Column("cpc", sa.Numeric(precision=12, scale=4), nullable=True, comment="单次点击成本"),
        sa.Column("sum_cost", sa.Numeric(precision=18, scale=2), nullable=True, comment="广告总花费"),
        sa.Column("sum_price", sa.Numeric(precision=18, scale=2), nullable=True, comment="订单总金额"),
        sa.Column("status", sa.Integer(), nullable=True, comment="活动当日状态"),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=True, comment="入库时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "advert_id", "nm_id", "stat_date", "app_type", name="uq_dws_advert_daily_shop_advert_nm_date_app"),
        comment="Wildberries 广告日汇总表（v1）",
    )
    op.create_index("idx_dws_advert_daily_shop_id", "dws_wb_advert_daily_stats", ["shop_id"], unique=False)
    op.create_index("idx_dws_advert_daily_advert_id", "dws_wb_advert_daily_stats", ["advert_id"], unique=False)
    op.create_index("idx_dws_advert_daily_nm_id", "dws_wb_advert_daily_stats", ["nm_id"], unique=False)
    op.create_index("idx_dws_advert_daily_stat_date", "dws_wb_advert_daily_stats", ["stat_date"], unique=False)

    # 7. 广告全量日明细表(v3)
    op.create_table(
        "dwd_wb_advert_fullstats_daily",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("stat_date", sa.Date(), nullable=False, comment="统计日期"),
        sa.Column("app_type", sa.String(length=50), nullable=False, comment="终端类型"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="商品ID"),
        sa.Column("nm_name", sa.String(length=500), nullable=True, comment="商品名称"),
        sa.Column("views", sa.Integer(), nullable=True, comment="曝光次数"),
        sa.Column("clicks", sa.Integer(), nullable=True, comment="点击次数"),
        sa.Column("atbs", sa.Integer(), nullable=True, comment="加购次数"),
        sa.Column("orders", sa.Integer(), nullable=True, comment="订单次数"),
        sa.Column("canceled", sa.Integer(), nullable=True, comment="取消订单次数"),
        sa.Column("shks", sa.Integer(), nullable=True, comment="已发货订单数"),
        sa.Column("sum_cost", sa.Numeric(precision=18, scale=2), nullable=True, comment="广告花费"),
        sa.Column("sum_price", sa.Numeric(precision=18, scale=2), nullable=True, comment="订单销售额"),
        sa.Column("cpc", sa.Numeric(precision=12, scale=4), nullable=True, comment="单次点击成本"),
        sa.Column("ctr", sa.Numeric(precision=8, scale=4), nullable=True, comment="点击率"),
        sa.Column("cr", sa.Numeric(precision=8, scale=4), nullable=True, comment="转化率"),
        sa.Column("avg_position", sa.Numeric(precision=8, scale=2), nullable=True, comment="助推器平均排名"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="币种"),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=True, comment="入库时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "advert_id", "stat_date", "app_type", "nm_id", name="uq_dwd_fullstats_daily_shop_advert_date_app_nm"),
        comment="Wildberries 广告全量日明细表（v3）",
    )
    op.create_index("idx_dwd_fullstats_daily_shop_id", "dwd_wb_advert_fullstats_daily", ["shop_id"], unique=False)
    op.create_index("idx_dwd_fullstats_daily_advert_id", "dwd_wb_advert_fullstats_daily", ["advert_id"], unique=False)
    op.create_index("idx_dwd_fullstats_daily_stat_date", "dwd_wb_advert_fullstats_daily", ["stat_date"], unique=False)
    op.create_index("idx_dwd_fullstats_daily_nm_id", "dwd_wb_advert_fullstats_daily", ["nm_id"], unique=False)

    # 8. 充值历史表
    op.create_table(
        "ods_wb_payment_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("upd_num", sa.BigInteger(), nullable=False, comment="流水号"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("upd_time", sa.DateTime(timezone=True), nullable=True, comment="充值时间"),
        sa.Column("upd_sum", sa.Numeric(precision=18, scale=2), nullable=True, comment="充值金额"),
        sa.Column("camp_name", sa.String(length=500), nullable=True, comment="活动名称"),
        sa.Column("advert_type", sa.Integer(), nullable=True, comment="活动类型"),
        sa.Column("payment_type", sa.String(length=50), nullable=True, comment="支付类型（余额/对公）"),
        sa.Column("advert_status", sa.Integer(), nullable=True, comment="充值时活动状态"),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=True, comment="入库时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "upd_num", "advert_id", name="uq_ods_payment_history_shop_upd_advert"),
        comment="Wildberries 充值历史表",
    )
    op.create_index("idx_ods_payment_history_shop_id", "ods_wb_payment_history", ["shop_id"], unique=False)
    op.create_index("idx_ods_payment_history_advert_id", "ods_wb_payment_history", ["advert_id"], unique=False)
    op.create_index("idx_ods_payment_history_upd_time", "ods_wb_payment_history", ["upd_time"], unique=False)

    # 9. 扣费历史表
    op.create_table(
        "ods_wb_expense_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=True, comment="原始JSON数据"),
        sa.Column("expense_id", sa.BigInteger(), nullable=True, comment="扣费流水ID"),
        sa.Column("expense_date", sa.DateTime(timezone=True), nullable=True, comment="扣费时间"),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True, comment="扣费金额"),
        sa.Column("expense_type", sa.Integer(), nullable=True, comment="扣费类型码"),
        sa.Column("status_id", sa.Integer(), nullable=True, comment="扣费状态码"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="币种"),
        sa.Column("card_status", sa.String(length=50), nullable=True, comment="支付卡状态"),
        sa.Column("create_time", sa.DateTime(timezone=True), nullable=True, comment="入库时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="Wildberries 扣费历史表",
    )
    op.create_index("idx_ods_expense_history_shop_id", "ods_wb_expense_history", ["shop_id"], unique=False)
    op.create_index("idx_ods_expense_history_expense_date", "ods_wb_expense_history", ["expense_date"], unique=False)


def downgrade() -> None:
    # 按反向顺序删除
    op.drop_index("idx_ods_expense_history_expense_date", table_name="ods_wb_expense_history")
    op.drop_index("idx_ods_expense_history_shop_id", table_name="ods_wb_expense_history")
    op.drop_table("ods_wb_expense_history")

    op.drop_index("idx_ods_payment_history_upd_time", table_name="ods_wb_payment_history")
    op.drop_index("idx_ods_payment_history_advert_id", table_name="ods_wb_payment_history")
    op.drop_index("idx_ods_payment_history_shop_id", table_name="ods_wb_payment_history")
    op.drop_table("ods_wb_payment_history")

    op.drop_index("idx_dwd_fullstats_daily_nm_id", table_name="dwd_wb_advert_fullstats_daily")
    op.drop_index("idx_dwd_fullstats_daily_stat_date", table_name="dwd_wb_advert_fullstats_daily")
    op.drop_index("idx_dwd_fullstats_daily_advert_id", table_name="dwd_wb_advert_fullstats_daily")
    op.drop_index("idx_dwd_fullstats_daily_shop_id", table_name="dwd_wb_advert_fullstats_daily")
    op.drop_table("dwd_wb_advert_fullstats_daily")

    op.drop_index("idx_dws_advert_daily_stat_date", table_name="dws_wb_advert_daily_stats")
    op.drop_index("idx_dws_advert_daily_nm_id", table_name="dws_wb_advert_daily_stats")
    op.drop_index("idx_dws_advert_daily_advert_id", table_name="dws_wb_advert_daily_stats")
    op.drop_index("idx_dws_advert_daily_shop_id", table_name="dws_wb_advert_daily_stats")
    op.drop_table("dws_wb_advert_daily_stats")

    op.drop_index("idx_dwd_normquery_stats_stat_date", table_name="dwd_wb_normquery_daily_stats")
    op.drop_index("idx_dwd_normquery_stats_nm_id", table_name="dwd_wb_normquery_daily_stats")
    op.drop_index("idx_dwd_normquery_stats_advert_id", table_name="dwd_wb_normquery_daily_stats")
    op.drop_index("idx_dwd_normquery_stats_shop_id", table_name="dwd_wb_normquery_daily_stats")
    op.drop_table("dwd_wb_normquery_daily_stats")

    op.drop_index("idx_dim_minus_words_nm_id", table_name="dim_wb_advert_minus_words")
    op.drop_index("idx_dim_minus_words_advert_id", table_name="dim_wb_advert_minus_words")
    op.drop_index("idx_dim_minus_words_shop_id", table_name="dim_wb_advert_minus_words")
    op.drop_table("dim_wb_advert_minus_words")

    op.drop_index("idx_dim_bid_recommend_nm_id", table_name="dim_wb_normquery_bid_recommend")
    op.drop_index("idx_dim_bid_recommend_advert_id", table_name="dim_wb_normquery_bid_recommend")
    op.drop_index("idx_dim_bid_recommend_shop_id", table_name="dim_wb_normquery_bid_recommend")
    op.drop_table("dim_wb_normquery_bid_recommend")

    op.drop_index("idx_dim_normquery_main_nm_id", table_name="dim_wb_normquery_main")
    op.drop_index("idx_dim_normquery_main_advert_id", table_name="dim_wb_normquery_main")
    op.drop_index("idx_dim_normquery_main_shop_id", table_name="dim_wb_normquery_main")
    op.drop_table("dim_wb_normquery_main")

    op.drop_index("idx_dim_advert_main_status", table_name="dim_wb_advert_main")
    op.drop_index("idx_dim_advert_main_advert_id", table_name="dim_wb_advert_main")
    op.drop_index("idx_dim_advert_main_shop_id", table_name="dim_wb_advert_main")
    op.drop_table("dim_wb_advert_main")
