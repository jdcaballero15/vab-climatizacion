#!/usr/bin/env python3
"""Hook PreToolUse (Bash): bloquea comandos que rompen el workflow del repositorio.

Reglas (ver CLAUDE.md y CONTRIBUTING.md):
  1. No commitear estando en `main` ni en `develop`.
  2. No pushear directo a `main` ni a `develop`: todo entra por Pull Request.
  3. No reescribir historia (force push, reset --hard, rebase) sobre `main` ni `develop`.
  4. No saltear los chequeos (--no-verify, SKIP=).
  5. Las ramas nuevas siguen el esquema tipo/descripcion.
  6. No borrados recursivos sobre rutas demasiado amplias.

Salida de emergencia: OT_UNSAFE=1 (solo con autorizacion explicita, ver CLAUDE.md).
Si el hook falla por un error interno, deja pasar el comando y avisa por stderr.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

PROTECTED_BRANCHES = {"main", "develop"}

# El ID de la historia (E04-03) puede ir en mayusculas al principio de la descripcion.
BRANCH_NAMING = re.compile(
    r"^(feat|fix|docs|chore|refactor|test|ci|perf)/[A-Za-z0-9][A-Za-z0-9._-]*$"
)

BRANCH_HELP = (
    "Esquema de ramas (CONTRIBUTING.md):\n"
    "    feat/E04-03-asignar-orden     historia nueva\n"
    "    fix/E05-02-firma-sin-dni      correccion\n"
    "    docs/..., chore/..., refactor/..., test/..., ci/..., perf/...\n"
    "Ejemplo: git checkout -b feat/E04-03-asignar-orden"
)


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


def current_branch() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def check_skipped_verification(cmd: str) -> None:
    if "--no-verify" in cmd or re.search(r"\bSKIP=", cmd):
        deny(
            "BLOQUEADO: los chequeos no se saltean.\n\n"
            "Los hooks de pre-commit existen para atrapar lo que estas por commitear. "
            "Si fallan, arreglá la causa:\n"
            "    make fmt && make lint && make test"
        )


def check_commit(cmd: str) -> None:
    if not re.search(r"\bgit\s+(-C\s+\S+\s+)?commit\b", cmd):
        return
    branch = current_branch()
    if branch in PROTECTED_BRANCHES:
        deny(
            f"BLOQUEADO: commit directo sobre la rama protegida '{branch}'.\n"
            "Todo cambio nace en una rama de trabajo y entra por Pull Request.\n\n"
            "Pasá tu trabajo a una rama nueva:\n"
            "    git checkout -b feat/EXX-NN-descripcion\n\n" + BRANCH_HELP
        )


def check_push(cmd: str) -> None:
    if not re.search(r"\bgit\s+(-C\s+\S+\s+)?push\b", cmd):
        return

    forced = bool(re.search(r"(^|\s)(--force\b|--force-with-lease\b|-f\b)", cmd))
    protected_target = re.search(
        r"\b(origin|upstream)\s+(?:\+?\S+:)?(?:refs/heads/)?(main|develop)(?![\w/.-])", cmd
    ) or re.search(r"\bpush\b[^|;&]*(?<![\w/.-])(main|develop)(?![\w/.-])", cmd)

    if protected_target:
        target = protected_target.group(protected_target.lastindex or 0)
        deny(
            f"BLOQUEADO: push directo a '{target}'.\n"
            "Nadie escribe directo en main ni en develop: todo entra por Pull Request "
            "con CI en verde.\n\n"
            "Subí tu rama y abrí el PR:\n"
            "    git push -u origin <tu-rama>\n"
            "    gh pr create"
        )

    if forced:
        deny(
            "BLOQUEADO: push forzado.\n"
            "Reescribir historia publicada rompe el trabajo de los demás.\n\n"
            "Para corregir commits ya subidos, hacelo con un commit nuevo. "
            "Si el force es inevitable, necesita autorizacion explicita de la persona responsable."
        )


def check_history(cmd: str) -> None:
    dangerous = re.search(r"\bgit\s+(-C\s+\S+\s+)?(reset\s+--hard|rebase)\b", cmd)
    if not dangerous:
        return
    branch = current_branch()
    if branch in PROTECTED_BRANCHES:
        deny(
            f"BLOQUEADO: '{dangerous.group(0)}' sobre la rama protegida '{branch}'.\n"
            f"Para deshacer algo que ya está en {branch} usá:\n"
            "    git revert <sha>\n"
            "que deja registro del cambio en lugar de borrarlo."
        )


def check_new_branch(cmd: str) -> None:
    match = re.search(
        r"\bgit\s+(?:-C\s+\S+\s+)?(?:checkout\s+-b|switch\s+-c)\s+(?P<name>[^\s;|&]+)",
        cmd,
    )
    if not match:
        return
    name = match.group("name").strip("\"'`,;")
    if BRANCH_NAMING.match(name):
        return
    deny(f"BLOQUEADO: '{name}' no sigue el esquema de nombres de rama.\n\n" + BRANCH_HELP)


def check_bulk_delete(cmd: str) -> None:
    if re.search(r"\brm\s+(-\w*[rR]\w*f|-\w*f\w*[rR])\w*\s+(/|~|\.\s*$|\*)", cmd):
        deny(
            "BLOQUEADO: borrado recursivo forzado sobre una ruta demasiado amplia.\n"
            "Acotá el comando a los archivos puntuales, o corré 'git clean -n' antes."
        )


def main() -> None:
    if os.environ.get("OT_UNSAFE") == "1":
        return

    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input") or {}
    cmd = tool_input.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return

    check_skipped_verification(cmd)
    check_bulk_delete(cmd)
    check_new_branch(cmd)
    check_commit(cmd)
    check_push(cmd)
    check_history(cmd)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - un hook roto no debe frenar al equipo
        print(f"[guard_bash] falla interna del hook, se deja pasar: {exc}", file=sys.stderr)
    sys.exit(0)
