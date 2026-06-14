from app.services.ingestion import ParsedCell
from app.services.quality import validate_population_cells


def make_cells():
    cells = []
    for municipality in ("05001", "11001"):
        for sex in ("M", "F"):
            for age in range(101):
                cells.append(
                    ParsedCell(
                        department_code=municipality[:2],
                        department_name="Department",
                        municipality_code=municipality,
                        municipality_name="City",
                        year=2026,
                        area="Total",
                        sex=sex,
                        age=age,
                        population=1,
                    )
                )
    controls = {
        (municipality, 2026, "Total"): {"total": 202, "M": 101, "F": 101}
        for municipality in ("05001", "11001")
    }
    return cells, controls


def test_quality_gate_passes_complete_reconciled_source():
    cells, controls = make_cells()
    report = validate_population_cells(cells, controls, {"05001", "11001"}, {2026})
    assert report["status"] == "passed"
    assert all(report["checks"].values())


def test_quality_gate_rejects_missing_cell():
    cells, controls = make_cells()
    cells.pop()
    report = validate_population_cells(cells, controls, {"05001", "11001"}, {2026})
    assert report["status"] == "failed"
    assert report["metrics"]["missing_dimension_count"] == 1
