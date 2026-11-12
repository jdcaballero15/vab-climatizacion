"""E12-02, criterio 3: el código no borra filas de negocio. Nada de DELETE físico."""

import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"
# session.delete(objeto), delete(Modelo) de SQLAlchemy o SQL a mano.
PHYSICAL_DELETE = re.compile(
    r"session\.delete\(|(?<!\.)\bdelete\(\s*[A-Z]\w*\s*\)|(?i:DELETE\s+FROM)"
)


def test_no_hay_delete_fisico_en_la_app() -> None:
    hits = [
        f"{path.relative_to(APP.parent)}:{number}: {line.strip()}"
        for path in APP.rglob("*.py")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if PHYSICAL_DELETE.search(line)
    ]
    assert hits == [], "Borrado físico: usá deleted_at (CLAUDE.md, regla 2).\n" + "\n".join(hits)
