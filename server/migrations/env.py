import os
import re
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from alembic import context

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

from kunpeng.config import settings

# add your model's MetaData object here
# for 'autogenerate' support
from kunpeng.models.base import Base
from kunpeng.models.dwd import (
    DWDOzonAdvertEfficiencyDetail,
    DWDOzonCustomerVoiceDetail,
    DWDOzonOrderDetail,
    DWDOzonProductNameTranslation,
    DWDOzonReturnDetail,
    DWDOzonSalesFunnelDetail,
    DWDWBAdvertActivityDetail,
    DWDWBAdvertBidConfig,
    DWDWBAdvertStatsDailyIncr,
    DWDWBAdvertStatsHourlyIncr,
    DWDWBOrderDetail,
    DWDWBOrderStatisticsDetail,
    DWDWBReturnDetail,
    DWDWBSalesFunnelDetail,
    DWDWBSalesReportDetail,
    DWDWBSalesReportSummary,
    DWDWBVOCFeedbackDetail,
    DWDWBVOCQuestionDetail,
)

# The historical production bridge hashes a frozen model registry. Do not add
# this newer DWM table to that registry during ordinary upgrades; its explicit
# migration is sufficient. Schema-diff commands still need the model metadata.
if any(command in {"revision", "check"} for command in sys.argv[1:]):
    from kunpeng.models.dwm import (  # noqa: F401
        DWMOzonGoodsTradeReturnDay,
        DWMOzonOrderLifecycleDetail,
    )

from kunpeng.models.ods import (
    ODSWBAdvert,
    ODSWBAdvertStat,
    ODSWBAdvertStatHourly,
    ODSWBChatEvent,
    ODSWBFbsSupply,
    ODSWBFeedback,
    ODSWBFeedbackPin,
    ODSWBGoodsReturn,
    ODSWBMarketplaceOrder,
    ODSWBMarketplaceOrderStatusHistory,
    ODSWBNewOrder,
    ODSWBOrderMetadata,
    ODSWBProductSearchText,
    ODSWBQuestion,
    ODSWBRegionSale,
    ODSWBReshipmentOrder,
    ODSWBReturnClaim,
    ODSWBSalesFunnel,
    ODSWBSalesReport,
    ODSWBSalesReportList,
    ODSWBSearchClusterStatHourly,
    ODSWBSearchTraffic,
    ODSWBSellerBalance,
    ODSWBSupplierOrder,
    ODSWBSupplierSale,
)

# 导入Ozon模型
from kunpeng.models.ods.ozon import (
    ODSOzonAccrualFee,
    ODSOzonAnalyticsDataDaily,
    ODSOzonAnalyticsTotalsWindow,
    ODSOzonFBSPosting,
    ODSOzonFBSPostingCancellation,
    ODSOzonFBSPostingDelivery,
    ODSOzonFBSPostingExternal,
    ODSOzonFBSPostingOptional,
    ODSOzonFBSPostingProduct,
    ODSOzonFinanceAccrual,
    ODSOzonFinanceAccrualType,
    ODSOzonFinanceRealizationHeader,
    ODSOzonFinanceRealizationRow,
    ODSOzonPostingReportRow,
    ODSOzonPostingReportTask,
    ODSOzonReturn,
    ODSOzonReturnProduct,
    ODSOzonReturnStorage,
    ODSOzonReview,
    ODSOzonUnfulfilledPosting,
)
from kunpeng.models.ods.wildberries.adv_enhanced import (
    ODSWBAdvertFullStat,
    ODSWBAdvertV2,
    ODSWBBidRecommendation,
    ODSWBNormQueryBid,
    ODSWBNormQueryList,
    ODSWBNormQueryMinus,
    ODSWBNormQueryStat,
    ODSWBPromotionCount,
)

target_metadata = Base.metadata

_LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1"}
_DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def _sync_database_url(database_url: str) -> str:
    """Convert the application's async URL to an Alembic-compatible sync URL."""
    url = make_url(database_url)
    if url.drivername == "mysql+asyncmy":
        url = url.set(drivername="mysql+pymysql")
    elif url.drivername == "sqlite+aiosqlite":
        url = url.set(drivername="sqlite")
    return url.render_as_string(hide_password=False)


def _migration_database_url() -> str:
    """Return the configured URL, optionally targeting a safe local test database."""
    database_url = settings.database_url
    database_name = os.getenv("ALEMBIC_DATABASE_NAME")
    if not database_name:
        return database_url
    if not _DATABASE_NAME_PATTERN.fullmatch(database_name):
        raise ValueError("ALEMBIC_DATABASE_NAME contains invalid characters")

    url = make_url(database_url)
    if url.host not in _LOCAL_DATABASE_HOSTS:
        raise RuntimeError(
            "ALEMBIC_DATABASE_NAME may only override a localhost database"
        )
    return url.set(database=database_name).render_as_string(hide_password=False)


migration_database_url = _migration_database_url()


def include_object(object_, name, type_, reflected, compare_to):
    """Keep database-only legacy tables out of destructive autogenerate output."""
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


# ConfigParser treats ``%`` in URL-escaped credentials as interpolation syntax.
# Escaping it here does not change the URL received by SQLAlchemy.
config.set_main_option(
    "sqlalchemy.url",
    _sync_database_url(migration_database_url).replace("%", "%%"),
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy import create_engine

    connectable = create_engine(_sync_database_url(migration_database_url))

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
