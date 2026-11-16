"""E00-07 y E07-04: la copia y el mantenimiento corren en un solo cron.

Cada paso ya tiene sus tests contra la base y el bucket reales (test_backup.py,
test_maintenance_plans.py). Acá solo se prueba el orden y que una falla no frene al otro.
"""

import pytest

from app import nightly_run


def _step(calls: list[str], name: str, result: int | Exception) -> object:
    def run() -> int:
        calls.append(name)
        if isinstance(result, Exception):
            raise result
        return result

    return run


def _patch(
    monkeypatch: pytest.MonkeyPatch, backup: int | Exception, maintenance: int | Exception
) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(
        nightly_run,
        "STEPS",
        (
            ("copia", _step(calls, "copia", backup)),
            ("mantenimiento", _step(calls, "mantenimiento", maintenance)),
        ),
    )
    return calls


def test_runs_backup_first_and_then_maintenance(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch(monkeypatch, 0, 0)

    assert nightly_run.main() == 0
    assert calls == ["copia", "mantenimiento"]


@pytest.mark.parametrize("backup", [1, RuntimeError("bucket rechazó la clave")])
def test_maintenance_runs_even_if_backup_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], backup: int | Exception
) -> None:
    calls = _patch(monkeypatch, backup, 0)

    assert nightly_run.main() == 1
    assert calls == ["copia", "mantenimiento"]
    assert "Falló: copia." in capsys.readouterr().err


def test_fails_if_maintenance_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, 0, RuntimeError("sin base"))

    assert nightly_run.main() == 1


def test_steps_are_the_real_commands() -> None:
    from app import backup_db, maintenance_run

    steps = nightly_run.STEPS
    assert steps == (("copia", backup_db.main), ("mantenimiento", maintenance_run.main))
