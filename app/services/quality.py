from collections import defaultdict

from app.services.ingestion import ParsedCell


def validate_population_cells(
    cells: list[ParsedCell],
    controls: dict[tuple[str, int, str], dict],
    municipalities: set[str],
    years: set[int],
    max_age: int = 100,
) -> dict:
    failures: list[str] = []
    # When ingestion targets all of Colombia (no explicit municipality set), validate
    # completeness against the municipalities actually present in the source file.
    if not municipalities:
        municipalities = {cell.municipality_code for cell in cells}
    observed_dimensions = {(cell.municipality_code, cell.year, cell.sex, cell.age) for cell in cells}
    expected_dimensions = {
        (municipality, year, sex, age)
        for municipality in municipalities
        for year in years
        for sex in ("M", "F")
        for age in range(max_age + 1)
    }
    missing = expected_dimensions - observed_dimensions
    extra = observed_dimensions - expected_dimensions
    if missing:
        failures.append(f"{len(missing)} required dimensions are missing")
    if extra:
        failures.append(f"{len(extra)} unexpected dimensions were found")
    if any(cell.population < 0 for cell in cells):
        failures.append("Negative population values were found")

    sums: dict[tuple[str, int, str], int] = defaultdict(int)
    for cell in cells:
        sums[(cell.municipality_code, cell.year, cell.sex)] += cell.population
    reconciliation_errors = []
    for (municipality, year, _area), control in controls.items():
        male = sums[(municipality, year, "M")]
        female = sums[(municipality, year, "F")]
        if male != control["M"] or female != control["F"] or male + female != control["total"]:
            reconciliation_errors.append(
                {
                    "municipality": municipality,
                    "year": year,
                    "expected": control,
                    "actual": {"M": male, "F": female},
                }
            )
    if reconciliation_errors:
        failures.append(f"{len(reconciliation_errors)} source totals failed reconciliation")

    report = {
        "status": "passed" if not failures else "failed",
        "checks": {
            "complete_dimensions": not missing,
            "no_unexpected_dimensions": not extra,
            "nonnegative_population": not any(cell.population < 0 for cell in cells),
            "source_total_reconciliation": not reconciliation_errors,
        },
        "metrics": {
            "cell_count": len(cells),
            "missing_dimension_count": len(missing),
            "unexpected_dimension_count": len(extra),
            "reconciliation_error_count": len(reconciliation_errors),
        },
        "failures": failures,
    }
    return report
