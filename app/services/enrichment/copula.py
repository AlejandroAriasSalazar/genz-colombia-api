"""Cópula gaussiana para dependencia conjunta (Capa 2 del pipeline).

Las variables Tier 3 (consumo, ingreso, tecnología) solo son representativas a
nivel regional. No se inventa un marginal municipal: se aprende la *estructura de
dependencia* de la encuesta (aquí, una matriz de correlación latente por bloque) y
se muestrea condicionada al bloque demográfico ya anclado.

Procedimiento (Propuesta 4.3, Opción A):
  1. z ~ N(0, R) con R la correlación latente del bloque.
  2. u_j = Phi(z_j)  -> uniformes con la dependencia de la cópula.
  3. x_j = F_j^{-1}(u_j | covariables)  -> categoría/valor vía la CDF condicional.

Esto preserva tanto las marginales condicionales como su co-movimiento. Implementado
en numpy puro; Phi y Phi^{-1} sin scipy (erf + aproximación de Acklam).
"""

from __future__ import annotations

import math

import numpy as np

# --- Normal estándar: CDF e inversa, sin scipy -----------------------------------

_SQRT2 = math.sqrt(2.0)


def norm_cdf(x: np.ndarray | float) -> np.ndarray:
    """Phi(x) = 0.5*(1 + erf(x/√2)), vectorizado sobre numpy."""
    x = np.asarray(x, dtype=float)
    flat = np.array([math.erf(v / _SQRT2) for v in x.ravel()])
    return 0.5 * (1.0 + flat.reshape(x.shape))


# Coeficientes de la aproximación de Acklam para la normal inversa (|err| < 1.15e-9).
_A = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
      1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
_B = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
      6.680131188771972e+01, -1.328068155288572e+01]
_C = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
      -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
_D = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
      3.754408661907416e+00]
_P_LOW = 0.02425
_P_HIGH = 1.0 - _P_LOW


def norm_ppf(p: np.ndarray | float) -> np.ndarray:
    """Phi^{-1}(p) (cuantil normal estándar) por la aproximación de Acklam."""
    p = np.asarray(p, dtype=float)
    p = np.clip(p, 1e-12, 1.0 - 1e-12)
    out = np.empty_like(p)

    low = p < _P_LOW
    high = p > _P_HIGH
    mid = ~(low | high)

    if np.any(low):
        q = np.sqrt(-2.0 * np.log(p[low]))
        out[low] = (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
                   ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    if np.any(high):
        q = np.sqrt(-2.0 * np.log(1.0 - p[high]))
        out[high] = -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
                    ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    if np.any(mid):
        q = p[mid] - 0.5
        r = q * q
        out[mid] = (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / \
                   (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
    return out


# --- Muestreo por cópula ----------------------------------------------------------

def correlated_uniforms(
    corr: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Devuelve un vector de uniformes (0,1) con la dependencia de la cópula `corr`."""
    corr = np.asarray(corr, dtype=float)
    d = corr.shape[0]
    chol = _safe_cholesky(corr)
    z = chol @ rng.standard_normal(d)
    return norm_cdf(z)


def _safe_cholesky(corr: np.ndarray) -> np.ndarray:
    """Cholesky con regularización mínima si la matriz no es definida positiva."""
    try:
        return np.linalg.cholesky(corr)
    except np.linalg.LinAlgError:
        eye = np.eye(corr.shape[0])
        for eps in (1e-9, 1e-6, 1e-4, 1e-2):
            try:
                return np.linalg.cholesky(corr * (1 - eps) + eye * eps)
            except np.linalg.LinAlgError:
                continue
        raise


def inverse_cdf_pick(u: float, probabilities: list[float]) -> int:
    """Mapea un uniforme `u` al índice de categoría vía la CDF discreta (F^{-1})."""
    cdf = 0.0
    for idx, p in enumerate(probabilities):
        cdf += p
        if u <= cdf:
            return idx
    return len(probabilities) - 1
