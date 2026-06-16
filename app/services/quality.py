from collections import defaultdict

from app.services.ingestion import ParsedCell


class IncrementalQualityGate:
    """Memory-bounded equivalent of :func:`validate_population_cells`.

    The list-based validator builds two ~5.6M-element sets to diff observed vs
    expected dimensions — fine for tests, fatal for national ingestion on a small
    box. This gate accumulates only per-(municipality, year, sex) running sums and a
    handful of scalars while cells are streamed past it, so peak memory stays flat
    regardless of dataset size. It produces the same report shape.

    Completeness is checked by counting: the parser only emits in-range ages and
    in-target municipalities, and the database's uniqueness constraint forbids
    duplicate dimensions, so ``observed`` is a unique subset of ``expected`` and the
    difference reduces to ``expected_count - observed_count``.
    """

    def __init__(self, municipalities: set[str], years: set[int], max_age: int = 100) -> None:
        self.target_municipalities = set(municipalities)
        self.years = set(years)
        self.max_age = max_age
        self._observed_municipalities: set[str] = set()
        self._observed_count = 0
        self._age_out_of_range = 0
        self._has_negative = False
        self._sums: dict[tuple[str, int, str], int] = defaultdict(int)
        self._controls: dict[tuple[str, int, str], dict] = {}

    def observe_cell(self, cell: ParsedCell) -> None:
        self._observed_municipalities.add(cell.municipality_code)
        self._observed_count += 1
        if cell.population < 0:
            self._has_negative = True
        if cell.age < 0 or cell.age > self.max_age:
            self._age_out_of_range += 1
        self._sums[(cell.municipality_code, cell.year, cell.sex)] += cell.population

    def observe_row(self, row_cells, control_key, control_value) -> None:
        self._controls[control_key] = control_value
        for cell in row_cells:
            self.observe_cell(cell)

    def register_controls(self, controls: dict[tuple[str, int, str], dict]) -> None:
        """Seed reconciliation controls up front.

        Live ingestion discovers controls row-by-row via :meth:`observe_row`, but the
        prebuilt-release path carries them in a separate, small ``controls.csv.gz`` while
        the cells stream past one at a time through :meth:`observe_cell`. Registering the
        controls here lets that path reconcile without ever materializing the cells.
        """
        self._controls.update(controls)

    @property
    def cell_count(self) -> int:
        return self._observed_count

    def report(self) -> dict:
        municipalities = self.target_municipalities or self._observed_municipalities
        expected_count = len(municipalities) * len(self.years) * 2 * (self.max_age + 1)
        missing = max(0, expected_count - self._observed_count)
        extra = self._age_out_of_range
        reconciliation_errors = []
        for (municipality, year, _area), control in self._controls.items():
            male = self._sums.get((municipality, year, "M"), 0)
            female = self._sums.get((municipality, year, "F"), 0)
            if male != control["M"] or female != control["F"] or male + female != control["total"]:
                reconciliation_errors.append(
                    {
                        "municipality": municipality,
                        "year": year,
                        "expected": control,
                        "actual": {"M": male, "F": female},
                    }
                )
        failures: list[str] = []
        if missing:
            failures.append(f"{missing} required dimensions are missing")
        if extra:
            failures.append(f"{extra} unexpected dimensions were found")
        if self._has_negative:
            failures.append("Negative population values were found")
        if reconciliation_errors:
            failures.append(f"{len(reconciliation_errors)} source totals failed reconciliation")
        return {
            "status": "passed" if not failures else "failed",
            "checks": {
                "complete_dimensions": not missing,
                "no_unexpected_dimensions": not extra,
                "nonnegative_population": not self._has_negative,
                "source_total_reconciliation": not reconciliation_errors,
            },
            "metrics": {
                "cell_count": self._observed_count,
                "missing_dimension_count": missing,
                "unexpected_dimension_count": extra,
                "reconciliation_error_count": len(reconciliation_errors),
            },
            "failures": failures,
        }


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
