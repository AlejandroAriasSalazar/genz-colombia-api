"""
Servicio de generación de datos sintéticos.
Genera personas sintéticas con distribuciones marginales realistas basadas en estadísticas oficiales del DANE.
"""
import numpy as np
import hashlib
import uuid
from typing import Optional

from app.utils.divipola import (
    BOGOTA_DIVIPOLA,
    MEDELLIN_DIVIPOLA,
    BOGOTA_LOCALIDADES,
    MEDELLIN_COMUNAS,
    ESTRATOS_DISTRIBUTION,
    SEX_DISTRIBUTION,
    NIVELES_EDUCATIVOS,
    OCUPACIONES,
    INTERESES_MUSICALES,
    INTERESES_TECNOLOGICOS,
    USO_BICICLETA,
)


class SyntheticDataGenerator:
    """Generador de datos sintéticos con distribuciones realistas."""

    def __init__(self, seed: int = 42):
        """Inicializa el generador con semilla para reproducibilidad."""
        self.rng = np.random.default_rng(seed)

    def generate_person_id(self) -> str:
        """Genera un ID sintético irreversível (hash)."""
        raw = str(uuid.uuid4())
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def generate_age(self) -> int:
        """
        Genera edad con distribución realista para Gen Z (12-28).
        Distribución ligeramente concentrada en 18-24 años.
        """
        # Distribución con pico en 18-24
        ages = np.arange(12, 29)
        weights = np.array([
            0.04, 0.05, 0.06, 0.07,  # 12-15
            0.08, 0.09, 0.10, 0.11,  # 16-19
            0.12, 0.11, 0.10, 0.09,  # 20-23
            0.07, 0.05, 0.04, 0.02,  # 24-27
            0.01,  # 28
        ])
        weights = weights / weights.sum()
        return int(self.rng.choice(ages, p=weights))

    def generate_sex(self) -> str:
        """Genera sexo con distribución 48% M, 52% F (DANE)."""
        return str(self.rng.choice(["M", "F"], p=[SEX_DISTRIBUTION["M"], SEX_DISTRIBUTION["F"]]))

    def generate_city(self) -> str:
        """
        Genera ciudad con distribución proporcional a población Gen Z.
        Bogotá: ~75%, Medellín: ~25%
        """
        return str(self.rng.choice([BOGOTA_DIVIPOLA, MEDELLIN_DIVIPOLA], p=[0.75, 0.25]))

    def generate_neighborhood(self, city_divipola: str) -> str:
        """Genera código de barrio/comuna/localidad según la ciudad."""
        if city_divipola == BOGOTA_DIVIPOLA:
            neighborhoods = BOGOTA_LOCALIDADES
        elif city_divipola == MEDELLIN_DIVIPOLA:
            neighborhoods = MEDELLIN_COMUNAS
        else:
            raise ValueError(f"Ciudad no soportada: {city_divipola}")

        # Distribución uniforme entre barrios/comunas
        return str(self.rng.choice([n["code"] for n in neighborhoods]))

    def generate_estrato(self, city_divipola: str) -> int:
        """
        Genera estrato con distribución por ciudad (basada en DANE/ECV).
        Bogotá: 15% E1, 35% E2, 30% E3, 12% E4, 5% E5, 3% E6
        Medellín: 18% E1, 33% E2, 32% E3, 12% E4, 4% E5, 1% E6
        """
        distribution = ESTRATOS_DISTRIBUTION.get(city_divipola, ESTRATOS_DISTRIBUTION[BOGOTA_DIVIPOLA])
        estratos = list(distribution.keys())
        probs = list(distribution.values())
        return int(self.rng.choice(estratos, p=probs))

    def generate_nivel_educativo(self, edad: int, estrato: int) -> str:
        """
        Genera nivel educativo con distribución condicional a edad y estrato.
        - 12-15: primaria/secundaria
        - 16-17: secundaria/media
        - 18-20: media/técnica/universitaria
        - 21-28: técnica/tecnológica/universitaria/posgrado
        Estratos más altos tienden a más educación.
        """
        if edad <= 15:
            options = ["primaria", "secundaria"]
            probs = [0.3, 0.7]
        elif edad <= 17:
            options = ["secundaria", "media"]
            probs = [0.4, 0.6]
        elif edad <= 20:
            if estrato >= 4:
                options = ["media", "tecnica", "universitaria"]
                probs = [0.3, 0.3, 0.4]
            else:
                options = ["media", "tecnica", "tecnologica"]
                probs = [0.5, 0.3, 0.2]
        else:  # 21-28
            if estrato >= 5:
                options = ["tecnica", "tecnologica", "universitaria", "posgrado"]
                probs = [0.15, 0.20, 0.45, 0.20]
            elif estrato >= 3:
                options = ["tecnica", "tecnologica", "universitaria", "posgrado"]
                probs = [0.25, 0.30, 0.35, 0.10]
            else:
                options = ["primaria", "secundaria", "media", "tecnica", "tecnologica"]
                probs = [0.05, 0.20, 0.35, 0.25, 0.15]

        return str(self.rng.choice(options, p=probs))

    def generate_ocupacion(self, edad: int, nivel_educativo: str) -> str:
        """
        Genera ocupación con distribución condicional a edad y nivel educativo.
        - 12-16: 90% estudiante
        - 17-20: 70% estudiante, 30% empleado/independiente
        - 21-28: distribución más variada
        """
        if edad <= 16:
            options = ["estudiante", "oficios_del_hogar", "otro"]
            probs = [0.90, 0.05, 0.05]
        elif edad <= 20:
            options = ["estudiante", "empleado", "independiente", "desempleado"]
            probs = [0.65, 0.15, 0.10, 0.10]
        else:  # 21-28
            if nivel_educativo in ["universitaria", "posgrado"]:
                options = ["empleado", "independiente", "estudiante", "desempleado"]
                probs = [0.50, 0.25, 0.10, 0.15]
            elif nivel_educativo in ["tecnica", "tecnologica"]:
                options = ["empleado", "independiente", "desempleado", "estudiante"]
                probs = [0.45, 0.25, 0.20, 0.10]
            else:
                options = ["empleado", "independiente", "desempleado", "oficios_del_hogar"]
                probs = [0.35, 0.20, 0.30, 0.15]

        return str(self.rng.choice(options, p=probs))

    def generate_acceso_internet(self, estrato: int) -> bool:
        """
        Genera acceso a internet con probabilidad condicional a estrato.
        Estratos altos: 98%, Estratos bajos: 75%
        (Basado en ENTIC/MinTIC)
        """
        prob = {
            1: 0.75,
            2: 0.85,
            3: 0.92,
            4: 0.96,
            5: 0.98,
            6: 0.99,
        }.get(estrato, 0.90)

        return bool(self.rng.random() < prob)

    def generate_interes_musical(self, edad: int) -> str:
        """
        Genera interés musical con distribución realista para Gen Z.
        Reggaetón, pop y urbano colombiano son dominantes.
        """
        options = INTERESES_MUSICALES
        probs = [
            0.25,  # reggaeton
            0.15,  # pop
            0.08,  # rock
            0.12,  # hip_hop
            0.08,  # electronica
            0.05,  # salsa
            0.07,  # vallenato
            0.10,  # urbano_colombiano
            0.05,  # indie
            0.02,  # metal
            0.01,  # clasica
            0.02,  # otro
        ]
        return str(self.rng.choice(options, p=probs))

    def generate_interes_tecnologico(self, edad: int) -> str:
        """
        Genera interés tecnológico con distribución realista para Gen Z.
        Videojuegos, redes sociales y streaming son dominantes.
        """
        options = INTERESES_TECNOLOGICOS
        probs = [
            0.22,  # videojuegos
            0.20,  # redes_sociales
            0.10,  # programacion
            0.15,  # streaming
            0.08,  # creacion_contenido
            0.05,  # ecommerce
            0.08,  # inteligencia_artificial
            0.04,  # cripto
            0.04,  # fotografia_digital
            0.02,  # musica_digital
            0.02,  # otro
        ]
        return str(self.rng.choice(options, p=probs))

    def generate_uso_bicicleta(self, ciudad_divipola: str, estrato: int) -> str:
        """
        Genera uso de bicicleta con distribución condicional a ciudad y estrato.
        Medellín tiene mayor cultura de bicicleta que Bogotá en estratos bajos.
        Bogotá tiene más uso en estratos altos (ciclovía).
        """
        options = USO_BICICLETA

        if ciudad_divipola == MEDELLIN_DIVIPOLA:
            if estrato <= 2:
                probs = [0.30, 0.25, 0.25, 0.15, 0.05]
            elif estrato <= 4:
                probs = [0.25, 0.25, 0.25, 0.18, 0.07]
            else:
                probs = [0.35, 0.25, 0.20, 0.15, 0.05]
        else:  # Bogotá
            if estrato <= 2:
                probs = [0.35, 0.25, 0.20, 0.15, 0.05]
            elif estrato <= 4:
                probs = [0.20, 0.20, 0.25, 0.25, 0.10]
            else:
                probs = [0.15, 0.15, 0.25, 0.30, 0.15]

        return str(self.rng.choice(options, p=probs))

    def generate_person(self) -> dict:
        """Genera una persona sintética completa con todas las variables."""
        edad = self.generate_age()
        sexo = self.generate_sex()
        ciudad = self.generate_city()
        neighborhood = self.generate_neighborhood(ciudad)
        estrato = self.generate_estrato(ciudad)
        nivel_educativo = self.generate_nivel_educativo(edad, estrato)
        ocupacion = self.generate_ocupacion(edad, nivel_educativo)
        acceso_internet = self.generate_acceso_internet(estrato)
        interes_musical = self.generate_interes_musical(edad)
        interes_tecnologico = self.generate_interes_tecnologico(edad)
        uso_bicicleta = self.generate_uso_bicicleta(ciudad, estrato)

        return {
            "id": self.generate_person_id(),
            "edad": edad,
            "sexo": sexo,
            "ciudad_divipola": ciudad,
            "neighborhood_code": neighborhood,
            "estrato": estrato,
            "nivel_educativo": nivel_educativo,
            "ocupacion": ocupacion,
            "acceso_internet": acceso_internet,
            "interes_musical": interes_musical,
            "interes_tecnologico": interes_tecnologico,
            "uso_bicicleta": uso_bicicleta,
        }

    def generate_dataset(self, n: int = 1000) -> list[dict]:
        """Genera un dataset completo de n personas sintéticas."""
        return [self.generate_person() for _ in range(n)]


# Instancia global del generador
generator = SyntheticDataGenerator(seed=42)
