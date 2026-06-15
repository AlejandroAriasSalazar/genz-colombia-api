import html
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ProblemError
from app.models import PopulationCell
from app.services.market import _weighted_median_age
from app.services.query import release_metadata, resolve_release


def build_report(
    db: Session,
    settings: Settings,
    municipality_code: str,
    year: int | None = None,
    age_min: int = 12,
    age_max: int = 28,
    top: int = 10,
) -> dict:
    """Consolidated market-intelligence report for one municipality (one call = one report)."""
    release = resolve_release(db)
    year = year or settings.default_reference_year
    base = PopulationCell.dataset_version_id == release.id

    territory = db.execute(
        select(
            PopulationCell.municipality_name,
            PopulationCell.department_code,
            PopulationCell.department_name,
        )
        .where(base, PopulationCell.year == year, PopulationCell.municipality_code == municipality_code)
        .limit(1)
    ).first()
    if territory is None:
        raise ProblemError(
            404, "Territory not found", f"No data for municipality {municipality_code} in {year}."
        )

    cells: dict[tuple[int, str], int] = {}
    by_age: dict[int, int] = {}
    by_sex = {"M": 0, "F": 0}
    target = 0
    rows = db.execute(
        select(PopulationCell.age, PopulationCell.sex, func.sum(PopulationCell.population).label("p")).where(
            base,
            PopulationCell.year == year,
            PopulationCell.municipality_code == municipality_code,
            PopulationCell.age >= age_min,
            PopulationCell.age <= age_max,
        ).group_by(PopulationCell.age, PopulationCell.sex)
    ).all()
    for row in rows:
        population = int(row.p)
        cells[(row.age, row.sex)] = population
        by_age[row.age] = by_age.get(row.age, 0) + population
        by_sex[row.sex] = by_sex.get(row.sex, 0) + population
        target += population

    territory_population = int(
        db.scalar(
            select(func.sum(PopulationCell.population)).where(
                base, PopulationCell.year == year, PopulationCell.municipality_code == municipality_code
            )
        )
        or 0
    )

    pyramid = []
    low = age_min
    while low <= age_max:
        high = min(low + 2, age_max)
        pyramid.append(
            {
                "range": f"{low}-{high}",
                "M": sum(p for (a, s), p in cells.items() if s == "M" and low <= a <= high),
                "F": sum(p for (a, s), p in cells.items() if s == "F" and low <= a <= high),
            }
        )
        low = high + 1

    rank_rows = db.execute(
        select(
            PopulationCell.municipality_code.label("code"),
            PopulationCell.municipality_name.label("name"),
            func.sum(PopulationCell.population).label("target"),
        ).where(
            base,
            PopulationCell.year == year,
            PopulationCell.age >= age_min,
            PopulationCell.age <= age_max,
        ).group_by(PopulationCell.municipality_code, PopulationCell.municipality_name)
    ).all()
    ranked = sorted(((r.code, r.name, int(r.target)) for r in rank_rows), key=lambda x: x[2], reverse=True)
    national_rank = next((i + 1 for i, r in enumerate(ranked) if r[0] == municipality_code), None)
    ranking = [
        {"code": code, "name": name, "target_size": size, "is_current": code == municipality_code}
        for code, name, size in ranked[:top]
    ]

    return {
        "dataset": release_metadata(release),
        "territory": {
            "municipality_code": municipality_code,
            "municipality_name": territory.municipality_name,
            "department_code": territory.department_code,
            "department_name": territory.department_name,
        },
        "reference_year": year,
        "age_range": [age_min, age_max],
        "headline": {
            "territory_population": territory_population,
            "target_size": target,
            "target_share_percent": round(target * 100 / territory_population, 2)
            if territory_population
            else 0.0,
            "female_percent": round(by_sex["F"] * 100 / target, 2) if target else 0.0,
            "median_age": _weighted_median_age(by_age),
            "national_rank": national_rank,
        },
        "by_sex": by_sex,
        "pyramid": pyramid,
        "ranking": ranking,
    }


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{--bg:#0f1115;--card:#171a21;--line:#262b35;--text:#e8eaed;--muted:#9aa3b2;--accent:#378ADD;--teal:#1D9E75}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.5}
.wrap{max-width:960px;margin:0 auto;padding:32px 20px}
.head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:24px}
.title{font-size:26px;font-weight:600;margin:0}.sub{color:var(--muted);font-size:14px;margin-top:4px}
.badge{font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:8px;padding:6px 10px;white-space:nowrap}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:28px}
.metric{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.metric .lab{font-size:13px;color:var(--muted)}.metric .val{font-size:26px;font-weight:600;margin-top:4px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:20px}
.panel h2{font-size:16px;font-weight:600;margin:0 0 12px}
.chartbox{position:relative;width:100%;height:320px}
.foot{color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:14px;margin-top:8px}
.foot code{color:var(--text)}
</style></head><body>
<div class="wrap" id="app"></div>
<script>
const R = __DATA__;
const f = n => (n==null?'—':Number(n).toLocaleString('es-CO'));
const h = R.headline, t = R.territory;
document.title = "Gen Z · "+t.municipality_name;
const cards = [
  ["Mercado Gen Z ("+R.age_range[0]+"-"+R.age_range[1]+")", f(h.target_size)],
  ["Población total", f(h.territory_population)],
  ["% del municipio", h.target_share_percent+"%"],
  ["% mujeres", h.female_percent+"%"],
  ["Edad mediana", h.median_age==null?'—':h.median_age+" años"],
  ["Ranking nacional", h.national_rank==null?'—':"#"+h.national_rank],
];
document.getElementById('app').innerHTML = `
  <div class="head">
    <div><h1 class="title">Gen Z · ${t.municipality_name}</h1>
    <div class="sub">${t.department_name} · año ${R.reference_year} · inteligencia de mercado</div></div>
    <span class="badge">Fuente: DANE · método citable</span>
  </div>
  <div class="cards">${cards.map(c=>`<div class="metric"><div class="lab">${c[0]}</div><div class="val">${c[1]}</div></div>`).join('')}</div>
  <div class="panel"><h2>Mercado por edad y sexo</h2><div class="chartbox"><canvas id="pyr"></canvas></div></div>
  <div class="panel"><h2>Posición nacional · top municipios por mercado Gen Z</h2><div class="chartbox" style="height:${Math.max(260,R.ranking.length*34+60)}px"><canvas id="rank"></canvas></div></div>
  <div class="foot">Personas sintéticas derivadas de agregados oficiales DANE — nunca individuos reales.
  Dataset <code>${R.dataset.version}</code> · checksum <code>${(R.dataset.source_checksum_sha256||'').slice(0,12)}</code>.
  Variables de consumo y poder adquisitivo: roadmap (Tier 2/3).</div>`;
Chart.defaults.color = '#9aa3b2'; Chart.defaults.borderColor = 'rgba(255,255,255,.08)';
new Chart(document.getElementById('pyr'),{type:'bar',
  data:{labels:R.pyramid.map(b=>b.range),datasets:[
    {label:'Hombres',data:R.pyramid.map(b=>-b.M),backgroundColor:'#378ADD'},
    {label:'Mujeres',data:R.pyramid.map(b=>b.F),backgroundColor:'#1D9E75'}]},
  options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
    scales:{x:{stacked:true,ticks:{callback:v=>f(Math.abs(v))}},y:{stacked:true}},
    plugins:{tooltip:{callbacks:{label:c=>c.dataset.label+': '+f(Math.abs(c.raw))}}}}});
new Chart(document.getElementById('rank'),{type:'bar',
  data:{labels:R.ranking.map(r=>r.name),datasets:[{data:R.ranking.map(r=>r.target_size),
    backgroundColor:R.ranking.map(r=>r.is_current?'#1D9E75':'#2f6aa8')}]},
  options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
    plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>f(c.raw)}}},
    scales:{x:{ticks:{callback:v=>f(v)}},y:{ticks:{autoSkip:false}}}}});
</script></body></html>"""


def render_report_html(report: dict) -> str:
    title = html.escape(f"Gen Z · {report['territory']['municipality_name']}")
    # Escape "<" so no data value (e.g. a name containing "</script>") can break out
    # of the inline <script> block.
    data = json.dumps(report, default=str).replace("<", "\\u003c")
    return REPORT_TEMPLATE.replace("__TITLE__", title).replace("__DATA__", data)
