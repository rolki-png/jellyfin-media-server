#!/usr/bin/env bash
# Run BootCatchup TLC. Broken model must fail; good model must pass.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
JAR="${TLA2TOOLS_JAR:-}"
if [[ -z "${JAR}" ]]; then
  for candidate in \
    "${HOME}/.local/share/mise/installs/http-tla2tools/1.7.4/tla2tools.jar" \
    "${HOME}/.local/share/mise/shims/tla2tools.jar" \
    /usr/share/java/tla2tools.jar; do
    if [[ -f "${candidate}" ]]; then
      JAR="${candidate}"
      break
    fi
  done
fi
if [[ -z "${JAR}" || ! -f "${JAR}" ]]; then
  echo "ERROR: tla2tools.jar not found; set TLA2TOOLS_JAR" >&2
  exit 1
fi

run_tlc() {
  local module=$1
  local cfg=$2
  local metadir out
  metadir="$(mktemp -d "${ROOT}/states.XXXXXX")"
  out="$(mktemp)"
  set +e
  java -XX:+UseParallelGC -jar "${JAR}" -config "${cfg}" -workers auto -deadlock \
    -metadir "${metadir}" "${module}" >"${out}" 2>&1
  local rc=$?
  set -e
  cat "${out}"
  rm -rf "${metadir}"
  if grep -q 'Error: Invariant' "${out}"; then
    rm -f "${out}"
    return 2
  fi
  rm -f "${out}"
  return "${rc}"
}

echo "==> expect FAIL (broken boot without catch-up)"
if run_tlc "${ROOT}/BootCatchupBroken.tla" "${ROOT}/BootCatchupBroken.cfg"; then
  echo "ERROR: broken model passed TLC" >&2
  exit 1
fi
echo "broken model failed as expected"

echo "==> expect PASS (boot covers lookback)"
if ! run_tlc "${ROOT}/BootCatchup.tla" "${ROOT}/BootCatchup.cfg"; then
  echo "ERROR: good model failed TLC" >&2
  exit 1
fi
echo "BootCatchup TLC ok"
