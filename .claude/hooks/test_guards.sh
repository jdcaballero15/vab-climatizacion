#!/usr/bin/env bash
# Verifica que los guardas sigan bloqueando lo que deben. Uso: bash .claude/hooks/test_guards.sh
set -u
cd "$(dirname "$0")/../.."
fail=0

run() { printf '%s' "$2" | python3 ".claude/hooks/$1" 2>/dev/null; }

expect_deny() { # hook, nombre, json
  if run "$1" "$3" | grep -q '"permissionDecision": "deny"'; then echo "ok    $2"; else echo "FALLA $2 (debia bloquear)"; fail=1; fi
}
expect_allow() {
  if run "$1" "$3" | grep -q 'deny'; then echo "FALLA $2 (debia permitir)"; fail=1; else echo "ok    $2"; fi
}

bash_cmd() { printf '{"tool_input":{"command":"%s"}}' "$1"; }

expect_deny guard_bash.py "push a main" "$(bash_cmd 'git push origin main')"
expect_deny guard_bash.py "force push" "$(bash_cmd 'git push --force origin feat/x')"
expect_deny guard_bash.py "no-verify" "$(bash_cmd 'git commit --no-verify -m x')"
expect_deny guard_bash.py "rama mal nombrada" "$(bash_cmd 'git checkout -b mi-rama')"
expect_deny guard_bash.py "rm -rf amplio" "$(bash_cmd 'rm -rf /')"
expect_allow guard_bash.py "rama valida" "$(bash_cmd 'git checkout -b feat/E04-03-asignar-orden')"
expect_allow guard_bash.py "push de rama" "$(bash_cmd 'git push -u origin feat/E04-03-asignar-orden')"

edit() { printf '{"tool_input":{"file_path":"%s","content":"%s"}}' "$1" "$2"; }

# En main (el CI de cada push) guard_edit bloquea toda escritura: se comprueba, y el resto
# se prueba en un worktree temporal sin rama, como en un PR.
if [ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" = "main" ]; then
  expect_deny guard_edit.py "escribir en main" "$(edit "$PWD/docs/x.md" 'a - b')"
  tmp="$(mktemp -d)"
  git worktree add --quiet --detach "$tmp/repo" HEAD
  trap 'git worktree remove --force "$tmp/repo"; rm -rf "$tmp"' EXIT
  cd "$tmp/repo"
fi

expect_deny guard_edit.py ".env real" "$(edit "$PWD/backend/.env" 'A=1')"
expect_deny guard_edit.py "clave privada" "$(edit "$PWD/backend/x.pem" 'A')"
expect_deny guard_edit.py "raya en doc" "$(edit "$PWD/docs/x.md" "a $(python3 -c 'print(chr(0x2014))') b")"
expect_deny guard_edit.py "carpeta nueva en raiz" "$(edit "$PWD/nueva/x.md" 'a')"
expect_allow guard_edit.py ".env.example" "$(edit "$PWD/.env.example" 'A=')"
expect_allow guard_edit.py "doc normal" "$(edit "$PWD/docs/x.md" 'a - b')"

exit $fail
