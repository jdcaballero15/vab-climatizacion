#!/usr/bin/env python3
"""Hook PreToolUse (Write|Edit|MultiEdit): protege reglas del repositorio.

Reglas:
  1. No escribir archivos de secretos (.env reales, claves, certificados).
  2. No crear directorios nuevos en la raiz sin un ADR aprobado (ALLOWED_TOPLEVEL).
  3. No usar el guion largo (raya) en documentos del repo: se usa guion simple.
  4. No escribir sobre `main` ni `develop`.

Salida de emergencia: OT_UNSAFE=1 (solo con autorizacion explicita).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Para agregar una carpeta a la raiz: ADR aprobado y luego sumarla aca.
ALLOWED_TOPLEVEL = {
    ".claude",
    ".github",
    "backend",
    "docs",
    "pwa-tecnico",
    "scripts",
    "web-admin",
}

SECRET_NAME = re.compile(r"(^\.env(\..+)?$|\.(pem|key|p12|crt|pfx)$)")
SECRET_ALLOWED = re.compile(r"^\.env\.example$")
LONG_DASHES = (chr(0x2014), chr(0x2013))
DOC_SUFFIXES = {".md", ".yml", ".yaml", ".dbml", ".txt"}
PROTECTED_BRANCHES = {"main", "develop"}


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def repo_root() -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return Path(__file__).resolve().parents[2]
    if out.returncode == 0 and out.stdout.strip():
        return Path(out.stdout.strip())
    return Path(__file__).resolve().parents[2]


def current_branch() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def written_text(tool_input: dict) -> str:
    parts = [tool_input.get("content"), tool_input.get("new_string")]
    for edit in tool_input.get("edits") or []:
        parts.append(edit.get("new_string"))
    return "\n".join(p for p in parts if isinstance(p, str))


def main() -> None:
    if os.environ.get("OT_UNSAFE") == "1":
        return

    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input") or {}
    raw_path = tool_input.get("file_path")
    if not isinstance(raw_path, str) or not raw_path:
        return
    path = Path(raw_path)

    if SECRET_NAME.search(path.name) and not SECRET_ALLOWED.match(path.name):
        deny(
            f"BLOQUEADO: '{path.name}' es un archivo de secretos.\n"
            "Nunca se escriben claves, tokens ni .env reales. Usá variables de entorno "
            "y documentá el nombre en .env.example, con el valor vacio."
        )

    root = repo_root()
    if root is not None:
        try:
            rel = path.resolve().relative_to(root.resolve())
        except ValueError:
            rel = None
        if rel is not None and len(rel.parts) > 1 and rel.parts[0] not in ALLOWED_TOPLEVEL:
            deny(
                f"BLOQUEADO: '{rel.parts[0]}/' no es una carpeta permitida en la raiz.\n"
                "Una carpeta nueva en la raiz necesita un ADR aprobado y sumarla a "
                "ALLOWED_TOPLEVEL en .claude/hooks/guard_edit.py (plantilla: "
                "docs/architecture/adr/0000-template.md)."
            )
        branch = current_branch()
        if branch in PROTECTED_BRANCHES:
            deny(
                f"BLOQUEADO: no se escribe sobre '{branch}'.\n"
                "Creá una rama de trabajo: git checkout -b feat/EXX-NN-descripcion"
            )

    if path.suffix in DOC_SUFFIXES:
        text = written_text(tool_input)
        if any(d in text for d in LONG_DASHES):
            deny(
                "BLOQUEADO: el texto tiene un guion largo (raya).\n"
                "En este repositorio se usa el guion simple (-)."
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - un hook roto no debe frenar al equipo
        print(f"[guard_edit] falla interna del hook, se deja pasar: {exc}", file=sys.stderr)
    sys.exit(0)
