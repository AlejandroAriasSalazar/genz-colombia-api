"""Iterative Proportional Fitting (IPF).

Capa 1 del pipeline de enriquecimiento (ver Propuesta, sección 4.2): ajusta una
tabla de contingencia "semilla" (que aporta la estructura de asociación) a un
conjunto de marginales objetivo locales (Censo 2018 / MinTIC) hasta que TODOS los
márgenes coinciden simultáneamente.

Garantía dura de IPF: la distribución sintética de cada variable anclada reproduce
los marginales oficiales. Lo que NO garantiza: correlaciones de variables sin un
marginal local (eso lo cubre la cópula en `copula.py`).

Implementación pura en numpy (sin scipy) para no añadir dependencias pesadas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class IPFResult:
    """Tabla conjunta ajustada y diagnósticos de convergencia."""

    fitted: np.ndarray
    iterations: int
    converged: bool
    max_margin_error: float
    tae: float          # Total Absolute Error contra los marginales objetivo
    srmse: float        # Standardised Root Mean Squared Error


def _normalise_targets(targets: list[np.ndarray], total: float) -> list[np.ndarray]:
    """Reescala cada marginal objetivo para que sumen el mismo total (consistencia
    necesaria para que IPF converja)."""
    normalised = []
    for margin in targets:
        margin = np.asarray(margin, dtype=float)
        s = margin.sum()
        if s <= 0:
            raise ValueError("Cada marginal objetivo debe sumar un valor positivo")
        normalised.append(margin * (total / s))
    return normalised


def fit_ipf(
    seed: np.ndarray,
    targets: list[np.ndarray],
    *,
    max_iter: int = 200,
    tol: float = 1e-8,
) -> IPFResult:
    """Ajusta `seed` (n-dimensional) a los marginales `targets` (uno por eje).

    Args:
        seed: tabla de contingencia inicial con la estructura de asociación.
        targets: lista de vectores marginales objetivo, en el orden de los ejes
            de `seed`. `targets[k]` debe tener longitud `seed.shape[k]`.
        max_iter: tope de iteraciones.
        tol: tolerancia sobre el máximo error absoluto de marginal.

    Returns:
        IPFResult con la tabla ajustada y métricas de ajuste por zona.
    """
    fitted = np.asarray(seed, dtype=float).copy()
    if fitted.ndim != len(targets):
        raise ValueError("Se requiere un marginal objetivo por cada eje de la semilla")
    # Evita ceros estructurales que congelarían celdas con masa objetivo.
    fitted = np.where(fitted <= 0, 1e-9, fitted)

    total = float(np.asarray(targets[0], dtype=float).sum())
    targets = _normalise_targets(targets, total)

    def _other_axes(axis: int) -> tuple[int, ...]:
        return tuple(i for i in range(fitted.ndim) if i != axis)

    max_err = np.inf
    iterations = 0
    for iterations in range(1, max_iter + 1):
        # Un barrido completo: ajusta cada eje a su marginal objetivo.
        for axis, target in enumerate(targets):
            current = fitted.sum(axis=_other_axes(axis))
            with np.errstate(divide="ignore", invalid="ignore"):
                factor = np.where(current > 0, target / current, 0.0)
            shape = [1] * fitted.ndim
            shape[axis] = fitted.shape[axis]
            fitted = fitted * factor.reshape(shape)
        # Convergencia: máximo error sobre TODOS los marginales tras el barrido
        # completo (ajustar un eje desajusta los demás; hay que remedir todo).
        max_err = max(
            float(np.max(np.abs(fitted.sum(axis=_other_axes(axis)) - target)))
            for axis, target in enumerate(targets)
        )
        if max_err < tol:
            break

    tae, srmse = _fit_metrics(fitted, targets)
    return IPFResult(
        fitted=fitted,
        iterations=iterations,
        converged=max_err < tol,
        max_margin_error=max_err,
        tae=tae,
        srmse=srmse,
    )


def _fit_metrics(fitted: np.ndarray, targets: list[np.ndarray]) -> tuple[float, float]:
    """TAE y SRMSE agregados sobre todos los marginales (validación interna)."""
    abs_errors = []
    sq_errors = []
    observed_total = 0.0
    n_margins = 0
    for axis, target in enumerate(targets):
        current = fitted.sum(axis=tuple(i for i in range(fitted.ndim) if i != axis))
        abs_errors.append(np.abs(current - target).sum())
        sq_errors.append(np.sum((current - target) ** 2))
        observed_total += target.sum()
        n_margins += target.size
    tae = float(np.sum(abs_errors))
    rmse = float(np.sqrt(np.sum(sq_errors) / n_margins))
    mean_count = observed_total / n_margins if n_margins else 1.0
    srmse = rmse / mean_count if mean_count else float("inf")
    return tae, srmse


def joint_to_conditional(fitted: np.ndarray, axis: int) -> np.ndarray:
    """Distribución condicional normalizada a lo largo de `axis` (suma 1 por celda
    del resto de ejes). Útil para muestrear una variable anclada dado el resto."""
    denom = fitted.sum(axis=axis, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        cond = np.where(denom > 0, fitted / denom, 0.0)
    return cond
