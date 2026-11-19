#!/usr/bin/env python
"""检查广告相关表的结构和数据"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import asyncio
from sqlalchemy import select, text

from kunpeng.core.database import AsyncSessionLocal


async def check_table_structure():
    """检查表结构"""
    print("\n" + "="*60)
    print("检查广告相关表结构")
    print("="*60)

    async with AsyncSessionLocal() as db:
        # 查询所有表
        tables_to_check = [
            ("Ozon 广告活动表", "ods_ozon_adv_campaigns"),
            ("Ozon 广告日统计表", "ods_ozon_adv_stats_daily"),
            ("Ozon 广告 SKU 日统计表", "ods_ozon_adv_stats_product_daily"),
            ("Ozon 广告 SKU 小时统计表", "ods_ozon_adv_stats_product_hourly"),
            ("Wildberries 广告活动表", "ods_wb_adverts"),
            ("Wildberries 广告商品表", "ods_wb_advert_product"),
            ("Wildberries 广告预算表", "ods_wb_advert_budget"),
            ("Wildberries 广告统计表", "ods_wb_advert_stats"),
            ("Wildberries 广告小时统计表", "ods_wb_advert_stats_hourly"),
            ("Wildberries 搜索关键词统计表", "ods_wb_search_cluster_stat"),
            ("Wildberries 搜索关键词小时统计表", "ods_wb_search_cluster_stat_hourly"),
        ]

        for name, table_name in tables_to_check:
            print(f"\n{name} ({table_name})")
            print("-"*60)

            # 检查表是否存在
            result = await db.execute(text(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{table_name}'
            """))
            exists = result.scalar() == 1
            if not exists:
                print(f"  ❌ 表不存在")
                continue

            # 检查行数
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"  ✅ 行数: {count}")

            if count > 0:
                # 如果有数据，查看几条
                result = await db.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
                rows = result.all()
                columns = list(result.keys())

                print(f"\n  列: {', '.join(columns)}")

                print(f"\n  前{len(rows)}行数据预览:")
                for i, row in enumerate(rows):
                    print(f"\n  行{i+1}:")
                    for col, val in zip(columns, row):
                        # 裁剪长值
                        str_val = str(val) if val is not None else "NULL"
                        if len(str_val) > 100:
                            str_val = str_val[:100] + "..."
                        print(f"    {col}: {str_val}")


async def check_alembic_version():
    """检查 alembic 版本"""
    print("\n" + "="*60)
    print("检查数据库迁移版本")
    print("="*60)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"\n当前数据库版本: {version}")
        except Exception as e:
            print(f"\n无法读取 alembic_version: {e}")


async def main():
    """主函数"""
    print("="*60)
    print("鲲鹏广告数据检查工具")
    print("="*60)

    await check_alembic_version()
    await check_table_structure()

    print("\n" + "="*60)
    print("检查完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
