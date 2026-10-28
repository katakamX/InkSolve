import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import normalize_equation, solve_equation


def test_linear_equation():
    result, normalized = solve_equation("2*x + 3 = 7")
    assert "Solutions" in result
    assert "2" in result


def test_quadratic_equation():
    result, _ = solve_equation("x^2 - 4 = 0")
    assert "-2" in result and "2" in result


def test_numeric_expression():
    result, _ = solve_equation("2 + 3 * 4")
    assert "14" in result


def test_unicode_math_normalization():
    assert normalize_equation("x² − 4 = 0") == "x**2-4=0"


def test_reject_multiple_equals():
    try:
        solve_equation("x=2=3")
    except ValueError as exc:
        assert "one equals sign" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
