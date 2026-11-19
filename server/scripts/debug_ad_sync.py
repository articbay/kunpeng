#!/usr/bin/env python
"""调试 Ozon/Wildberries 广告数据同步"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import asyncio
import logging
from sqlalchemy import select

from kunpeng.core.database import AsyncSessionLocal
from kunpeng.models.shop import Shop
from kunpeng.models.user import User
from kunpeng.clients.ozon import OzonClient
from kunpeng.clients.wildberries import WildberriesClient

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("debug_ad_sync")


async def check_existing_data():
    """检查现有数据"""
    print("\n" + "="*60)
    print("检查现有数据")
    print("="*60)

    async with AsyncSessionLocal() as db:
        # 检查用户
        result = await db.execute(select(User))
        users = list(result.scalars().all())
        print(f"\n用户数: {len(users)}")
        for u in users:
            print(f"  - {u.id}: {u.email} ({u.full_name})")

        # 检查店铺
        result = await db.execute(select(Shop))
        shops = list(result.scalars().all())
        print(f"\n店铺数: {len(shops)}")
        for s in shops:
            print(f"  - {s.id}: {s.name} ({s.platform})")
            print(f"    platform_shop_id: {s.platform_shop_id}")
            print(f"    user_id: {s.user_id}")
            print(f"    perf client_id: {'*'*20 if s.performance_client_id else 'None'}")
            print(f"    perf secret: {'*'*20 if s.performance_client_secret else 'None'}")

        return shops


async def test_ozon_performance_api(shop):
    """测试 Ozon Performance API"""
    print("\n" + "="*60)
    print(f"测试 Ozon 广告 API: {shop.name}")
    print("="*60)

    # 获取配置
    from kunpeng.config import settings
    client_id = getattr(shop, "platform_shop_id", "")
    api_key = str(shop.api_key or "")
    perf_client_id = getattr(shop, "performance_client_id", None) or settings.ozon_performance_client_id
    perf_client_secret = getattr(shop, "performance_client_secret", None) or settings.ozon_performance_client_secret

    print(f"\nClient ID: {client_id}")
    print(f"Perf Client ID: {perf_client_id[:50] if perf_client_id else 'None'}...")
    print(f"Perf Secret: {'*'*20 if perf_client_secret else 'None'}")

    if not perf_client_id or not perf_client_secret:
        print("\nERROR: Performance API 凭证未配置")
        return

    # 创建客户端
    client = OzonClient(
        client_id=client_id,
        api_key=api_key,
        performance_client_id=perf_client_id,
        performance_client_secret=perf_client_secret
    )

    try:
        async with client.performance:
            # 1. 测试获取广告活动列表
            print("\n--- 测试: 获取广告活动列表 ---")
            try:
                campaign_resp = await client.performance.get_campaigns()
                print(f"响应类型: {type(campaign_resp)}")
                print(f"完整响应: {campaign_resp}")
                campaigns = campaign_resp.get("list", []) or []
                print(f"\n广告活动数: {len(campaigns)}")
                for i, c in enumerate(campaigns[:5]):
                    print(f"  {i+1}. {c}")
                if len(campaigns) > 5:
                    print(f"  ... 还有 {len(campaigns)-5} 个")

            except Exception as e:
                print(f"ERROR: 获取广告活动失败: {e}")
                import traceback
                traceback.print_exc()
                return

            # 2. 如果有活动，测试获取按天统计
            if campaigns:
                print("\n--- 测试: 获取按天统计 ---")
                from datetime import datetime, timedelta
                today = datetime.now()
                date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
                date_to = today.strftime("%Y-%m-%d")

                try:
                    stats_resp = await client.performance.get_statistics_daily(
                        date_from=date_from,
                        date_to=date_to
                    )
                    print(f"统计响应: {stats_resp}")
                    stat_rows = stats_resp.get("rows", []) or []
                    print(f"\n统计数据行数: {len(stat_rows)}")
                    for i, row in enumerate(stat_rows[:5]):
                        print(f"  {i+1}. {row}")

                except Exception as e:
                    print(f"ERROR: 获取按天统计失败: {e}")
                    import traceback
                    traceback.print_exc()

    except Exception as e:
        print(f"ERROR: Ozon Performance API 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_wildberries_ad_api(shop):
    """测试 Wildberries 广告 API"""
    print("\n" + "="*60)
    print(f"测试 Wildberries 广告 API: {shop.name}")
    print("="*60)

    api_key = str(shop.api_key or "")
    print(f"\nAPI Key: {api_key[:50]}...")

    # 创建客户端
    client = WildberriesClient(
        statistics_api_key=api_key,
        analytics_api_key=api_key,
        advert_api_key=api_key,
        feedbacks_api_key=api_key,
        marketplace_api_key=api_key,
        finance_api_key=api_key
    )

    try:
        async with client:
            # 1. 测试获取广告活动列表
            if hasattr(client, 'advert') and client.advert:
                print("\n--- 测试: 获取广告活动列表 ---")
                try:
                    adverts_resp = await client.advert.get_adverts_list()
                    print(f"响应: {adverts_resp}")
                    adverts = adverts_resp.get("adverts", []) or []
                    print(f"\n广告活动数: {len(adverts)}")
                    for i, a in enumerate(adverts[:5]):
                        print(f"  {i+1}. {a}")
                    if len(adverts) > 5:
                        print(f"  ... 还有 {len(adverts)-5} 个")

                    # 2. 获取广告统计
                    if adverts:
                        print("\n--- 测试: 获取广告统计 ---")
                        from datetime import datetime, timedelta
                        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                        advert_ids = [a.get("id") for a in adverts if a.get("id")]
                        if advert_ids:
                            stats_resp = await client.advert.get_advert_stats(
                                advert_ids=advert_ids[:1],
                                begin_date=yesterday,
                                end_date=yesterday
                            )
                            print(f"统计响应: {stats_resp}")

                except Exception as e:
                    print(f"ERROR: 测试广告 API 失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("没有配置 advert 客户端")

    except Exception as e:
        print(f"ERROR: Wildberries API 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def run_sync_ozon_ad(shop):
    """运行 Ozon 广告数据同步（使用真实服务）"""
    print("\n" + "="*60)
    print(f"运行 Ozon 广告同步: {shop.name}")
    print("="*60)

    from kunpeng.services.ozon_sync_service import OzonSyncService

    async with AsyncSessionLocal() as db:
        service = OzonSyncService(db, shop)

        print("\n正在同步广告活动和日统计...")
        result = await service.sync_adverts(date_from="2026-07-01", date_to="2026-07-21")
        print(f"\n同步结果: {result}")

        print("\n正在同步广告 SKU 明细...")
        result2 = await service.sync_advert_products(date_from="2026-07-01", date_to="2026-07-21")
        print(f"\n同步结果: {result2}")


async def run_sync_wb_ad(shop):
    """运行 Wildberries 广告数据同步"""
    print("\n" + "="*60)
    print(f"运行 Wildberries 广告同步: {shop.name}")
    print("="*60)

    from kunpeng.services.wb_sync_service import WBSyncService

    async with AsyncSessionLocal() as db:
        service = WBSyncService(db, shop)

        print("\n正在同步广告数据...")
        result = await service.sync_adverts(date_from="2026-07-20", date_to="2026-07-21")
        print(f"\n同步结果: {result}")


async def auto_test_mode():
    """自动测试模式"""
    print("="*60)
    print("鲲鹏广告数据同步调试工具 - 自动模式")
    print("="*60)

    # 检查现有数据
    shops = await check_existing_data()

    if not shops:
        print("\n没有发现店铺！")
        return

    # 找到第一个 Ozon 店铺和 WB 店铺
    ozon_shops = [s for s in shops if s.platform.lower() == "ozon"]
    wb_shops = [s for s in shops if s.platform.lower() == "wildberries"]

    # 测试第一个 Ozon 店铺（如果有）
    if ozon_shops:
        shop = ozon_shops[0]
        print(f"\n\n{'='*60}")
        print(f"自动测试 Ozon 店铺: {shop.name}")
        print('='*60)
        await test_ozon_performance_api(shop)

    # 测试第一个 WB 店铺（如果有）
    if wb_shops:
        shop = wb_shops[0]
        print(f"\n\n{'='*60}")
        print(f"自动测试 Wildberries 店铺: {shop.name}")
        print('='*60)
        await test_wildberries_ad_api(shop)


async def main():
    """主函数"""
    import sys

    # 检查是否有命令行参数指定自动模式
    if len(sys.argv) > 1 and sys.argv[1] in ["--auto", "-a"]:
        await auto_test_mode()
        return

    print("="*60)
    print("鲲鹏广告数据同步调试工具")
    print("="*60)

    # 检查现有数据
    shops = await check_existing_data()

    if not shops:
        print("\n没有发现店铺，先添加店铺？")
        return

    # 交互式选择
    print("\n" + "="*60)
    print("请选择:")
    print("1. 仅查看现有数据（不调用 API）")
    print("2. 测试 Ozon 广告 API（查看 API 响应，不写入数据库）")
    print("3. 测试 Wildberries 广告 API（查看 API 响应，不写入数据库）")
    print("4. 运行真实 Ozon 广告数据同步（会写入数据库）")
    print("5. 运行真实 Wildberries 广告数据同步（会写入数据库）")
    print("6. 自动测试所有店铺（API 响应，不写入数据库）")
    print("0. 退出")

    try:
        choice = int(input("\n请输入选项 (0-6): ").strip())
    except ValueError:
        choice = 0

    if choice == 1:
        print("\n已选择仅查看现有数据")
        return

    if choice == 6:
        await auto_test_mode()
        return

    # 选择店铺
    print("\n请选择店铺:")
    for i, shop in enumerate(shops):
        print(f"{i+1}. {shop.name} ({shop.platform})")

    try:
        shop_choice = int(input(f"\n请选择店铺 (1-{len(shops)}): ").strip()) - 1
        if shop_choice < 0 or shop_choice >= len(shops):
            print("无效的选择")
            return
        selected_shop = shops[shop_choice]
    except ValueError:
        print("无效的输入")
        return

    if choice == 2:
        if selected_shop.platform.lower() != "ozon":
            print(f"该店铺是 {selected_shop.platform}，不是 Ozon")
            return
        await test_ozon_performance_api(selected_shop)

    elif choice == 3:
        if selected_shop.platform.lower() != "wildberries":
            print(f"该店铺是 {selected_shop.platform}，不是 Wildberries")
            return
        await test_wildberries_ad_api(selected_shop)

    elif choice == 4:
        if selected_shop.platform.lower() != "ozon":
            print(f"该店铺是 {selected_shop.platform}，不是 Ozon")
            return
        await run_sync_ozon_ad(selected_shop)

    elif choice == 5:
        if selected_shop.platform.lower() != "wildberries":
            print(f"该店铺是 {selected_shop.platform}，不是 Wildberries")
            return
        await run_sync_wb_ad(selected_shop)


if __name__ == "__main__":
    asyncio.run(main())
