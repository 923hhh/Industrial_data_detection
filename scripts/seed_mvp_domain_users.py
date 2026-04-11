#!/usr/bin/env python3
"""向检修域 MVP 表写入演示账号（依赖已执行 Alembic 迁移）。

用法：
    python scripts/seed_mvp_domain_users.py

默认密码均为 ``ChangeMe123!``，生产环境禁用本脚本或修改密码。
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.database import get_session_context
from app.models.mvp_domain import AuthUser, Device, Role, UserRole
from app.modules.mvp_maintenance.security import hash_password


async def main() -> None:
    pwd = hash_password("ChangeMe123!")
    async with get_session_context() as session:
        roles = (await session.execute(select(Role))).scalars().all()
        role_by_code = {r.code: r for r in roles}

        async def ensure_user(username: str, display: str, codes: list[str]) -> AuthUser:
            row = (await session.execute(select(AuthUser).where(AuthUser.username == username))).scalar_one_or_none()
            if row:
                return row
            u = AuthUser(
                username=username,
                password_hash=pwd,
                display_name=display,
                is_active=True,
            )
            session.add(u)
            await session.flush()
            for c in codes:
                rid = role_by_code[c].id
                session.add(UserRole(user_id=u.id, role_id=rid))
            return u

        await ensure_user("mvp_worker", "演示一线", ["worker"])
        expert = await ensure_user("mvp_expert", "演示专家", ["expert"])
        await ensure_user("mvp_safety", "演示安全", ["safety"])
        await ensure_user("mvp_admin", "演示管理员", ["admin"])

        dev = (
            await session.execute(select(Device).where(Device.device_type == "pump_test"))
        ).scalar_one_or_none()
        if dev is None:
            session.add(
                Device(
                    device_type="pump_test",
                    model="P-100",
                    asset_code="AST-MVP-001",
                    location="测试车间",
                    responsibility_expert_user_id=expert.id,
                )
            )
        await session.commit()
        print("MVP 演示用户与设备已就绪：mvp_worker / mvp_expert / mvp_safety / mvp_admin，密码 ChangeMe123!")


if __name__ == "__main__":
    asyncio.run(main())
