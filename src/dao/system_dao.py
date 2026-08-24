from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.system import SystemConfig


class SystemDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_json(self, key: str, default: Any = None) -> Any:
        item = await self.session.scalar(select(SystemConfig).where(SystemConfig.key == key, SystemConfig.is_deleted.is_(False)))
        if not item or not item.value:
            return default
        try:
            return json.loads(item.value)
        except json.JSONDecodeError:
            return item.value

    async def set_json(self, key: str, value: Any, description: str = "") -> SystemConfig:
        payload = json.dumps(value, ensure_ascii=False)
        item = await self.session.scalar(select(SystemConfig).where(SystemConfig.key == key))
        if item:
            item.value = payload
            if description:
                item.description = description
            item.value_type = "json"
        else:
            item = SystemConfig(key=key, value=payload, description=description, value_type="json")
            self.session.add(item)
        await self.session.flush()
        return item
