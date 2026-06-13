"""
Códigos DIVIPOLA oficiales para Bogotá y Medellín.
Fuentes:
- DANE: https://www.dane.gov.co/index.php/estadisticas-por-tema/datos-y-datos-abiertos
- Clasificación de Localidades de Bogotá (20 localidades)
- Clasificación de Comunas de Medellín (16 comunas)
"""

# Bogotá D.C. - Código DIVIPOLA: 11001
BOGOTA_DIVIPOLA = "11001"
BOGOTA_NAME = "Bogotá D.C."

# Medellín - Código DIVIPOLA: 05001
MEDELLIN_DIVIPOLA = "05001"
MEDELLIN_NAME = "Medellín"

# Localidades de Bogotá con códigos DIVIPOLA oficiales
BOGOTA_LOCALIDADES = [
    {"code": "11001", "name": "Usaquén", "city_divipola": "11001"},
    {"code": "11002", "name": "Chapinero", "city_divipola": "11001"},
    {"code": "11003", "name": "Santa Fe", "city_divipola": "11001"},
    {"code": "11004", "name": "San Cristóbal", "city_divipola": "11001"},
    {"code": "11005", "name": "Usme", "city_divipola": "11001"},
    {"code": "11006", "name": "Tunjuelito", "city_divipola": "11001"},
    {"code": "11007", "name": "Bosa", "city_divipola": "11001"},
    {"code": "11008", "name": "Kennedy", "city_divipola": "11001"},
    {"code": "11009", "name": "Fontibón", "city_divipola": "11001"},
    {"code": "11010", "name": "Engativá", "city_divipola": "11001"},
    {"code": "11011", "name": "Suba", "city_divipola": "11001"},
    {"code": "11012", "name": "Barrios Unidos", "city_divipola": "11001"},
    {"code": "11013", "name": "Teusaquillo", "city_divipola": "11001"},
    {"code": "11014", "name": "Los Mártires", "city_divipola": "11001"},
    {"code": "11015", "name": "Antonio Nariño", "city_divipola": "11001"},
    {"code": "11016", "name": "Puente Aranda", "city_divipola": "11001"},
    {"code": "11017", "name": "La Candelaria", "city_divipola": "11001"},
    {"code": "11018", "name": "Rafael Uribe Uribe", "city_divipola": "11001"},
    {"code": "11019", "name": "Ciudad Bolívar", "city_divipola": "11001"},
    {"code": "11020", "name": "Sumapaz", "city_divipola": "11001"},
]

# Comunas de Medellín con códigos oficiales
# Nota: Las comunas de Medellín no tienen códigos DIVIPOLA independientes,
# se usan códigos internos del municipio (05001) + sufijo de comuna
MEDELLIN_COMUNAS = [
    {"code": "05001-01", "name": "Popular", "city_divipola": "05001"},
    {"code": "05001-02", "name": "Santa Cruz", "city_divipola": "05001"},
    {"code": "05001-03", "name": "Manrique", "city_divipola": "05001"},
    {"code": "05001-04", "name": "Aranjuez", "city_divipola": "05001"},
    {"code": "05001-05", "name": "Castilla", "city_divipola": "05001"},
    {"code": "05001-06", "name": "Doce de Octubre", "city_divipola": "05001"},
    {"code": "05001-07", "name": "Robledo", "city_divipola": "05001"},
    {"code": "05001-08", "name": "Villa Hermosa", "city_divipola": "05001"},
    {"code": "05001-09", "name": "Buenos Aires", "city_divipola": "05001"},
    {"code": "05001-10", "name": "La América", "city_divipola": "05001"},
    {"code": "05001-11", "name": "La Candelaria", "city_divipola": "05001"},
    {"code": "05001-12", "name": "Laureles-Estadio", "city_divipola": "05001"},
    {"code": "05001-13", "name": "San Javier", "city_divipola": "05001"},
    {"code": "05001-14", "name": "El Poblado", "city_divipola": "05001"},
    {"code": "05001-15", "name": "Guayabal", "city_divipola": "05001"},
    {"code": "05001-16", "name": "Belén", "city_divipola": "05001"},
]

# Ciudades del proyecto
CITIES = [
    {
        "divipola": BOGOTA_DIVIPOLA,
        "name": BOGOTA_NAME,
        "department": "Cundinamarca",
        "population_total": 7412566,  # Proyección DANE 2023
        "population_genz": 2150000,  # Estimación Gen Z (12-28 años)
    },
    {
        "divipola": MEDELLIN_DIVIPOLA,
        "name": MEDELLIN_NAME,
        "department": "Antioquia",
        "population_total": 2569817,  # Proyección DANE 2023
        "population_genz": 720000,  # Estimación Gen Z (12-28 años)
    },
]


def get_city_by_divipola(divipola: str) -> dict | None:
    """Obtiene información de ciudad por código DIVIPOLA."""
    for city in CITIES:
        if city["divipola"] == divipola:
            return city
    return None


def get_neighborhoods_by_city(city_divipola: str) -> list[dict]:
    """Obtiene barrios/comunas/localidades por ciudad."""
    if city_divipola == BOGOTA_DIVIPOLA:
        return BOGOTA_LOCALIDADES
    elif city_divipola == MEDELLIN_DIVIPOLA:
        return MEDELLIN_COMUNAS
    return []


# Distribuciones de estratos por ciudad (basadas en datos DANE/GEIH)
# Fuente: Encuesta de Calidad de Vida DANE 2022
ESTRATOS_DISTRIBUTION = {
    "11001": {  # Bogotá
        1: 0.15,
        2: 0.35,
        3: 0.30,
        4: 0.12,
        5: 0.05,
        6: 0.03,
    },
    "05001": {  # Medellín
        1: 0.18,
        2: 0.33,
        3: 0.32,
        4: 0.12,
        5: 0.04,
        6: 0.01,
    },
}

# Distribución de sexos (basada en proyecciones DANE)
SEX_DISTRIBUTION = {"M": 0.48, "F": 0.52}

# Niveles educativos
NIVELES_EDUCATIVOS = [
    "ninguno",
    "primaria",
    "secundaria",
    "media",
    "tecnica",
    "tecnologica",
    "universitaria",
    "posgrado",
]

# Ocupaciones (clasificación simplificada CUOC)
OCUPACIONES = [
    "estudiante",
    "empleado",
    "independiente",
    "desempleado",
    "oficios_del_hogar",
    "otro",
]

# Intereses musicales
INTERESES_MUSICALES = [
    "reggaeton",
    "pop",
    "rock",
    "hip_hop",
    "electronica",
    "salsa",
    "vallenato",
    "urbano_colombiano",
    "indie",
    "metal",
    "clasica",
    "otro",
]

# Intereses tecnológicos
INTERESES_TECNOLOGICOS = [
    "videojuegos",
    "redes_sociales",
    "programacion",
    "streaming",
    "creacion_contenido",
    "ecommerce",
    "inteligencia_artificial",
    "cripto",
    "fotografia_digital",
    "musica_digital",
    "otro",
]

# Uso de bicicleta (frecuencia)
USO_BICICLETA = [
    "nunca",
    "rara_vez",
    "a_veces",
    "frecuentemente",
    "diariamente",
]
