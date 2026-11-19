from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class SyncSettings(BaseSettings):
    """数据同步窗口配置

    统一收敛"每小时任务"的取数窗口（靠幂等去重，避免每小时重复扫描超大区间），
    并为财务类数据提供"回补窗口"（防止平台 T+1 延迟结算导致漏数）。
    可通过 .env 以 `sync_` 前缀覆盖，例如 `SYNC_OZON_POSTINGS_LOOKBACK_DAYS=5`。
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_prefix="sync_", case_sensitive=False, extra="ignore"
    )

    # ── 每小时任务的取数窗口（收敛后）──
    # Wildberries：销售 / 订单（小时级），回看小时数
    wb_orders_lookback_hours: int = 24
    # Wildberries：Marketplace 订单，回看天数
    wb_marketplace_lookback_days: int = 2
    # Wildberries：销售漏斗，按单日粒度回补最近已结束的平台日
    wb_funnel_lookback_days: int = 7
    # Wildberries：区域销售报告，最近已结束的完整平台日数量
    wb_region_sales_lookback_days: int = 2
    # Wildberries：商品搜索词报告，最近已结束的完整平台日数量
    wb_product_search_texts_lookback_days: int = 2
    # Wildberries：商品搜索流量报告，最近已结束的完整平台日数量
    wb_search_traffic_lookback_days: int = 7
    # Wildberries：订单元数据，从 N 天前零点回看到本次运行时刻
    wb_order_metadata_lookback_days: int = 1
    # Wildberries：买家退货申请，按更新时间回看小时数
    wb_return_claims_lookback_hours: int = 1
    # Wildberries：买家聊天事件，从 N 天前零点回看到本次运行时刻
    wb_chat_events_lookback_days: int = 1
    # Wildberries：重新发货订单状态变化，从 N 天前零点回看到本次运行时刻
    wb_reshipment_lookback_days: int = 1
    # Wildberries：评价置顶记录，从 N 天前零点回看到本次运行时刻
    wb_feedback_pins_lookback_days: int = 1
    # Ozon：FBS 订单，回看天数（原默认 30 天，过大）
    ozon_postings_lookback_days: int = 3
    # Ozon：FBO 订单，回看天数
    ozon_fbo_lookback_days: int = 3
    # Ozon：退货，回看天数
    ozon_returns_lookback_days: int = 2
    # Ozon：待处理（未发货）新订单，回看天数
    ozon_unfulfilled_lookback_days: int = 1
    # Ozon：经营分析，按 SKU x 日粒度回补最近已结束的平台日
    ozon_analytics_lookback_days: int = 7

    # ── 财务类回补窗口（防延迟结算）──
    # 财务日更任务每次回补的天数（T-1 往前多拉几天，幂等覆盖）
    finance_backfill_days: int = 7
    # WB 按日财务明细任务的回补天数
    wb_finance_daily_backfill_days: int = 7


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, case_sensitive=False, extra="ignore"
    )

    # 应用配置
    app_name: str = "Kunpeng跨境电商系统"
    debug: bool = True
    environment: str = "development"  # development / production
    # 非生产环境启动 API 时是否按 SQLAlchemy 模型自动补建缺失表。
    # 手工精简本地库、但仍希望保留模型代码时应设为 False。
    auto_create_tables: bool = True

    # 平台业务时区：WB / Ozon 的统计数据均按莫斯科时间(UTC+3，无夏令时)归集。
    # 应用内所有"当前时间/今天/昨天/当前小时"等业务日期计算统一以此时区为准，
    # 与服务器/宿主机 OS 时区解耦，保证开发机、CI、生产环境行为一致。
    platform_timezone: str = "Europe/Moscow"

    # 定时任务总开关：默认仅生产环境注册调度任务；
    # 置为 True 后，非生产环境也会注册（便于本地真实验证调度链路）
    jobs_enabled: bool = False

    # 调度器运行开关：多进程部署(uvicorn --workers N)时，若每个 worker 都启动
    # APScheduler 会导致同一任务被并发触发 N 次（内存 jobstore 各自独立），
    # 从而把外部平台接口打到限流(429)。生产改为“API 多 worker + 独立单进程调度器”：
    #   - API 容器：RUN_SCHEDULER=false（仅提供 HTTP，不注册/启动调度）
    #   - 调度容器：RUN_SCHEDULER=true（单进程，唯一的调度来源）
    # 默认 True 以兼容本地一体化运行。
    run_scheduler: bool = True

    # 以逗号分隔的定时任务 ID 黑名单。任务函数和手动同步接口仍然保留，
    # 仅在调度注册阶段跳过这些任务；修改后需要重启调度进程。
    disabled_scheduled_jobs: str = ""

    @property
    def disabled_scheduled_job_ids(self) -> set[str]:
        """返回清理过的定时任务 ID 黑名单。"""
        return {
            job_id.strip()
            for job_id in self.disabled_scheduled_jobs.split(",")
            if job_id.strip()
        }

    # 数据库配置 (默认使用 MySQL，通过 .env 覆盖)
    database_url: str

    # JWT配置
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 30  # 30天

    # Wildberries API配置
    wb_api_key: Optional[str] = None

    # 百度通用文本翻译 API（俄语内容翻译为中文）
    baidu_translate_app_id: Optional[str] = None
    baidu_translate_secret_key: Optional[str] = None
    baidu_translate_qps: int = 10

    # Ozon Performance（广告）API 配置
    # 与 Seller API 独立鉴权，凭证形如 <id>@advertising.performance.ozon.ru
    ozon_performance_client_id: Optional[str] = None
    ozon_performance_client_secret: Optional[str] = None

    # CORS配置
    backend_cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # 数据同步窗口配置
    sync: SyncSettings = SyncSettings()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
