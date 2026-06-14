from pathlib import Path

from openpyxl import Workbook

from app.core.config import get_settings
from app.services.ingestion import DANEPopulationConnector


def build_fixture(path: Path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "PobMunicipalxÁreaSexoEdad"
    for row in range(1, 9):
        sheet.cell(row=row, column=1, value="metadata" if row == 3 else None)
    headers = ["DP", "DPNOM", "MPIO", "DPMP", "AÑO", "ÁREA GEOGRÁFICA", "Total", "Hombres", "Mujeres"]
    headers += [f"Hombres {age} año" if age == 1 else f"Hombres {age} años" for age in range(100)]
    headers += ["Hombres 100 años y más"]
    headers += [f"Mujeres {age} año" if age == 1 else f"Mujeres {age} años" for age in range(100)]
    headers += ["Mujeres 100 años y más"]
    sheet.append(headers)
    for code, city, department, department_name in (
        ("05001", "Medellín", "05", "Antioquia"),
        ("11001", "Bogotá, D.C.", "11", "Bogotá, D.C."),
    ):
        values = [department, department_name, code, city, 2026, "Total", 202, 101, 101]
        values += [1] * 202
        sheet.append(values)
    workbook.save(path)


def test_dane_connector_parses_verified_shape(tmp_path):
    source = tmp_path / "fixture.xlsx"
    build_fixture(source)
    connector = DANEPopulationConnector(get_settings())
    cells, controls = connector.parse(source, {"05001", "11001"}, {2026})
    assert len(cells) == 404
    assert controls[("05001", 2026, "Total")] == {"total": 202, "M": 101, "F": 101}
    assert {cell.age for cell in cells} == set(range(101))
