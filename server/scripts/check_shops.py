#!/usr/bin/env python
"""
查看现有用户和店铺
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.core.database import AsyncSessionLocal
from kunpeng.models.shop import Shop
from kunpeng.models.user import User


async def check_data():
    """查询现有数据"""
    print("=" * 60)
    print("鲲鹏项目 - 查看现有用户和店铺")
    print("=" * 60)
    print()

    async with AsyncSessionLocal() as db:
        # 查询用户
        print("--- 用户列表 ---")
        result = await db.execute(select(User))
        users = list(result.scalars().all())

        if not users:
            print("  (暂无用户)")
        else:
            for user in users:
                print(f"  ID: {user.id}, 邮箱: {user.email}, 姓名: {user.full_name}")

        print()
        print("--- 店铺列表 ---")
        result = await db.execute(select(Shop))
        shops = list(result.scalars().all())

        if not shops:
            print("  (暂无店铺)")
        else:
            for shop in shops:
                print(f"  ID: {shop.id}")
                print(f"    名称: {shop.name}")
                print(f"    平台: {shop.platform}")
                print(f"    平台店铺ID: {shop.platform_shop_id}")
                print(f"    用户ID: {shop.user_id}")
                print(f"    广告凭证已配置: {'是' if (shop.performance_client_id or shop.performance_client_secret) else '否'}")
                print()

        print("=" * 60)

        return users, shops

asyncio.run(check_data())
