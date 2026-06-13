"""
Script de seed data.
Puebla la base de datos con datos sintéticos realistas.
Ejecutar con: python -m scripts.seed_data
"""
import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session, init_db
from app.models.city import City
from app.models.neighborhood import Neighborhood
from app.models.person import Person
from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.services.data_generator import generator
from app.utils.divipola import (
    CITIES,
    BOGOTA_LOCALIDADES,
    MEDELLIN_COMUNAS,
)
from app.api.deps import hash_api_key
import uuid


async def seed_cities():
    """Puebla la tabla de ciudades."""
    async with async_session() as session:
        # Verificar si ya existen ciudades
        result = await session.execute(select(City))
        existing = result.scalars().all()

        if existing:
            print(f"Ya existen {len(existing)} ciudades. Saltando seed de ciudades.")
            return

        for city_data in CITIES:
            city = City(
                divipola=city_data["divipola"],
                name=city_data["name"],
                department=city_data["department"],
                population_total=city_data["population_total"],
                population_genz=city_data["population_genz"],
            )
            session.add(city)

        await session.commit()
        print(f"✓ {len(CITIES)} ciudades creadas.")


async def seed_neighborhoods():
    """Puebla la tabla de barrios/comunas/localidades."""
    async with async_session() as session:
        # Verificar si ya existen barrios
        result = await session.execute(select(Neighborhood))
        existing = result.scalars().all()

        if existing:
            print(f"Ya existen {len(existing)} barrios. Saltando seed de barrios.")
            return

        # Localidades de Bogotá
        for loc in BOGOTA_LOCALIDADES:
            neighborhood = Neighborhood(
                code=loc["code"],
                name=loc["name"],
                city_divipola=loc["city_divipola"],
                neighborhood_type="localidad",
            )
            session.add(neighborhood)

        # Comunas de Medellín
        for com in MEDELLIN_COMUNAS:
            neighborhood = Neighborhood(
                code=com["code"],
                name=com["name"],
                city_divipola=com["city_divipola"],
                neighborhood_type="comuna",
            )
            session.add(neighborhood)

        await session.commit()
        total = len(BOGOTA_LOCALIDADES) + len(MEDELLIN_COMUNAS)
        print(f"✓ {total} barrios/comunas creadas ({len(BOGOTA_LOCALIDADES)} localidades Bogotá + {len(MEDELLIN_COMUNAS)} comunas Medellín).")


async def seed_persons(n: int = 1000):
    """Puebla la tabla de personas sintéticas."""
    async with async_session() as session:
        # Verificar si ya existen personas
        result = await session.execute(select(Person))
        existing = result.scalars().all()

        if existing:
            print(f"Ya existen {len(existing)} personas. Saltando seed de personas.")
            return

        # Generar dataset sintético
        print(f"Generando {n} personas sintéticas...")
        persons_data = generator.generate_dataset(n)

        for p_data in persons_data:
            person = Person(
                id=p_data["id"],
                edad=p_data["edad"],
                sexo=p_data["sexo"],
                ciudad_divipola=p_data["ciudad_divipola"],
                neighborhood_code=p_data["neighborhood_code"],
                estrato=p_data["estrato"],
                nivel_educativo=p_data["nivel_educativo"],
                ocupacion=p_data["ocupacion"],
                acceso_internet=p_data["acceso_internet"],
                interes_musical=p_data["interes_musical"],
                interes_tecnologico=p_data["interes_tecnologico"],
                uso_bicicleta=p_data["uso_bicicleta"],
            )
            session.add(person)

        await session.commit()
        print(f"✓ {n} personas sintéticas creadas.")


async def seed_api_keys():
    """Crea API keys de ejemplo para cada tier."""
    async with async_session() as session:
        # Verificar si ya existen API keys
        result = await session.execute(select(APIKey))
        existing = result.scalars().all()

        if existing:
            print(f"Ya existen {len(existing)} API keys. Saltando seed de API keys.")
            return

        # API keys de ejemplo (para desarrollo/testing)
        # IMPORTANTE: En producción, estas keys deben generarse de forma segura
        test_keys = [
            {
                "key": "genz_free_test_key_12345",
                "name": "Free Tier - Test",
                "tier": "free",
                "queries_per_minute": 100,
                "queries_per_day": 1000,
                "max_sample_size": 100,
                "can_download": "N",
            },
            {
                "key": "genz_pro_test_key_67890",
                "name": "Pro Tier - Test",
                "tier": "pro",
                "queries_per_minute": 1000,
                "queries_per_day": 10000,
                "max_sample_size": 500,
                "can_download": "S",
            },
            {
                "key": "genz_enterprise_test_key_abcde",
                "name": "Enterprise Tier - Test",
                "tier": "enterprise",
                "queries_per_minute": 10000,
                "queries_per_day": 100000,
                "max_sample_size": 1000,
                "can_download": "S",
            },
        ]

        for key_data in test_keys:
            key_hash = hash_api_key(key_data["key"])
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
        print(f"✓ {len(test_keys)} API keys de prueba creadas.")
        print("\n" + "=" * 60)
        print("API KEYS DE PRUEBA (solo para desarrollo):")
        print("=" * 60)
        for key_data in test_keys:
            print(f"  Tier: {key_data['tier'].upper()}")
            print(f"  Key:  {key_data['key']}")
            print(f"  Name: {key_data['name']}")
            print("-" * 60)
        print("\nUsa estas keys en el header X-API-Key para autenticarte.")
        print("IMPORTANTE: Cambia estas keys en producción.\n")


async def main():
    """Ejecuta todos los seeds."""
    print("=" * 60)
    print("GenZ Colombia API - Seed Data")
    print("=" * 60)
    print()

    # Inicializar BD (crear tablas)
    print("Inicializando base de datos...")
    await init_db()
    print("✓ Base de datos inicializada.")
    print()

    # Ejecutar seeds en orden
    await seed_cities()
    await seed_neighborhoods()
    await seed_persons(n=1000)
    await seed_api_keys()

    print()
    print("=" * 60)
    print("Seed data completado exitosamente.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
