"""
Script para generar API keys de forma segura.
Uso: python -m scripts.create_api_keys --name "Mi App" --tier pro
"""
import asyncio
import sys
import os
import secrets
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session
from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.api.deps import hash_api_key
import uuid


def generate_secure_key() -> str:
    """Genera una API key segura usando secrets module."""
    prefix = "genz"
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"


async def create_api_key(name: str, tier: str):
    """Crea una nueva API key con su suscripción."""
    # Definir límites por tier
    tier_limits = {
        "free": {
            "queries_per_minute": 100,
            "queries_per_day": 1000,
            "max_sample_size": 100,
            "can_download": "N",
        },
        "pro": {
            "queries_per_minute": 1000,
            "queries_per_day": 10000,
            "max_sample_size": 500,
            "can_download": "S",
        },
        "enterprise": {
            "queries_per_minute": 10000,
            "queries_per_day": 100000,
            "max_sample_size": 1000,
            "can_download": "S",
        },
    }

    if tier not in tier_limits:
        print(f"Error: Tier inválido '{tier}'. Debe ser: free, pro, enterprise")
        return

    # Generar key
    api_key = generate_secure_key()
    key_hash = hash_api_key(api_key)

    limits = tier_limits[tier]

    async with async_session() as session:
        # Crear API key
        key_obj = APIKey(
            key_hash=key_hash,
            key_prefix=api_key[:8],
            name=name,
            tier=tier,
            is_active=True,
        )
        session.add(key_obj)

        # Crear suscripción
        subscription = Subscription(
            id=str(uuid.uuid4()),
            api_key_hash=key_hash,
            tier=tier,
            queries_per_minute=limits["queries_per_minute"],
            queries_per_day=limits["queries_per_day"],
            max_sample_size=limits["max_sample_size"],
            can_download=limits["can_download"],
        )
        session.add(subscription)

        await session.commit()

    print("=" * 60)
    print("API Key creada exitosamente")
    print("=" * 60)
    print(f"Nombre: {name}")
    print(f"Tier:   {tier.upper()}")
    print(f"Key:    {api_key}")
    print()
    print("Límites:")
    print(f"  Queries/minuto:  {limits['queries_per_minute']}")
    print(f"  Queries/día:     {limits['queries_per_day']}")
    print(f"  Muestra máxima:  {limits['max_sample_size']}")
    print(f"  Descargas:       {'Sí' if limits['can_download'] == 'S' else 'No'}")
    print()
    print("Usa esta key en el header X-API-Key:")
    print(f"  curl -H 'X-API-Key: {api_key}' http://localhost:8000/metadata")
    print("=" * 60)
    print()
    print("IMPORTANTE: Guarda esta key en un lugar seguro. No se mostrará de nuevo.")


def main():
    parser = argparse.ArgumentParser(description="Crear API key para GenZ Colombia API")
    parser.add_argument("--name", required=True, help="Nombre descriptivo de la API key")
    parser.add_argument("--tier", required=True, choices=["free", "pro", "enterprise"], help="Tier de suscripción")

    args = parser.parse_args()
    asyncio.run(create_api_key(args.name, args.tier))


if __name__ == "__main__":
    main()
