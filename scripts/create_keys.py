"""
Script para crear API keys de prueba.
Ejecutar dentro del contenedor: python -m scripts.create_keys
"""
import asyncio
import bcrypt
import sys
import uuid

from sqlalchemy import select
from app.database import async_session
from app.models.api_key import APIKey
from app.models.subscription import Subscription


def _truncate_key(key: str) -> bytes:
    return key.encode('utf-8')[:72]


async def main():
    test_keys = [
        {"key": "genz_free_test_key_12345", "name": "Free Tier - Test", "tier": "free",
         "queries_per_minute": 100, "queries_per_day": 1000, "max_sample_size": 100, "can_download": "N"},
        {"key": "genz_pro_test_key_67890", "name": "Pro Tier - Test", "tier": "pro",
         "queries_per_minute": 1000, "queries_per_day": 10000, "max_sample_size": 500, "can_download": "S"},
        {"key": "genz_enterprise_test_key_abcde", "name": "Enterprise Tier - Test", "tier": "enterprise",
         "queries_per_minute": 10000, "queries_per_day": 100000, "max_sample_size": 1000, "can_download": "S"},
    ]

    async with async_session() as session:
        # Check if keys already exist
        result = await session.execute(select(APIKey).where(APIKey.name.like('%Test%')))
        existing = result.scalars().all()
        if existing:
            print(f"Found {len(existing)} existing test keys - skipping")
            return

        for key_data in test_keys:
            key_hash = bcrypt.hashpw(_truncate_key(key_data["key"]), bcrypt.gensalt()).decode('utf-8')
            
            api_key = APIKey(
                key_hash=key_hash,
                key_prefix=key_data["key"][:8],
                name=key_data["name"],
                tier=key_data["tier"],
                is_active=True,
            )
            session.add(api_key)
            
            subscription = Subscription(
                id=str(uuid.uuid4()),
                api_key_hash=key_hash,
                tier=key_data["tier"],
                queries_per_minute=key_data["queries_per_minute"],
                queries_per_day=key_data["queries_per_day"],
                max_sample_size=key_data["max_sample_size"],
                can_download=key_data["can_download"],
            )
            session.add(subscription)
        
        await session.commit()
    
    print(f"Created {len(test_keys)} API keys successfully")

asyncio.run(main())
