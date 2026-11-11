#!/usr/bin/env bash
# Read-only driver for the live media stack. Does not start or stop containers.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${SKILL_DIR}/../../.." && pwd)"
COMPOSE_DIR="${REPO_ROOT}/compose_files"
ENV_FILE="${COMPOSE_DIR}/.env"
PROOF_DIR="${SKILL_DIR}/proof"
STAMP="${SKILL_DIR}/.run-stamp"

usage() {
  echo "Usage: verify-media-server.sh doctor|cleanup|drive <stack-health|movie-library|tv-library|download-client|dashboards|layout>" >&2
  exit 2
}

load_env() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "DOCTOR_FAIL missing ${ENV_FILE}" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  : "${APPDATA_PATH:?APPDATA_PATH not set}"
  : "${COMMON_PATH:?COMMON_PATH not set}"
}

docker_cmd() {
  if command docker info >/dev/null 2>&1; then
    docker "$@"
  else
    sudo docker "$@"
  fi
}

container_id() {
  docker_cmd inspect --format '{{.Id}}' "$1" 2>/dev/null || true
}

http_code() {
  curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "$1" || echo "000"
}

api_key() {
  local config=$1
  grep -oP '(?<=<ApiKey>)[^<]+' "${config}"
}

begin_proof() {
  local feature=$1
  local dest="${PROOF_DIR}/${feature}"
  mkdir -p "${dest}"
  printf '%s\n' "$2" >"${dest}/action.txt"
  : >"${dest}/stdout.txt"
  : >"${dest}/state.txt"
}

append_out() {
  printf '%s\n' "$2" >>"${PROOF_DIR}/$1/stdout.txt"
}

append_state() {
  printf '%s\n' "$2" >>"${PROOF_DIR}/$1/state.txt"
}

finish_proof() {
  printf '%s\n' "$2" >"${PROOF_DIR}/$1/exit_code.txt"
}

cmd_doctor() {
  load_env
  local fstype
  fstype="$(findmnt -n -o FSTYPE --target "${APPDATA_PATH}" 2>/dev/null || echo '?')"
  if printf '%s' "${fstype}" | grep -qi 'fuse.mergerfs'; then
    echo "DOCTOR_FAIL APPDATA_PATH ${APPDATA_PATH} is ${fstype}" >&2
    exit 1
  fi

  local missing=()
  local name
  for name in plex radarr sonarr qbittorrent; do
    if [[ -z "$(container_id "${name}")" ]]; then
      missing+=("${name}")
    fi
  done
  if ((${#missing[@]} > 0)); then
    echo "DOCTOR_FAIL containers not running: ${missing[*]}" >&2
    echo "Start with: cd ${COMPOSE_DIR} && docker compose --env-file .env up -d" >&2
    exit 1
  fi

  local plex_code radarr_body sonarr_body qbit_code
  plex_code="$(http_code http://127.0.0.1:32400/identity)"
  radarr_body="$(curl -sf --max-time 10 http://127.0.0.1:7878/ping || true)"
  sonarr_body="$(curl -sf --max-time 10 http://127.0.0.1:8989/ping || true)"
  qbit_code="$(http_code http://127.0.0.1:8080/)"

  if [[ "${plex_code}" != "200" ]]; then
    echo "DOCTOR_FAIL plex identity HTTP ${plex_code}" >&2
    exit 1
  fi
  if [[ "${radarr_body}" != *'"status": "OK"'* && "${radarr_body}" != *'"status":"OK"'* ]]; then
    echo "DOCTOR_FAIL radarr /ping did not report status OK" >&2
    exit 1
  fi
  if [[ "${sonarr_body}" != *'"status": "OK"'* && "${sonarr_body}" != *'"status":"OK"'* ]]; then
    echo "DOCTOR_FAIL sonarr /ping did not report status OK" >&2
    exit 1
  fi
  if [[ "${qbit_code}" != "200" ]]; then
    echo "DOCTOR_FAIL qbittorrent WebUI HTTP ${qbit_code}" >&2
    exit 1
  fi

  local run_id scratch
  run_id="$(date +%Y%m%dT%H%M%S)-$$"
  scratch="/tmp/verify-media-server-${run_id}"
  mkdir -p "${scratch}"
  cat >"${STAMP}" <<EOF
run_id=${run_id}
scratch=${scratch}
started_by_verify=no
plex_id=$(container_id plex)
radarr_id=$(container_id radarr)
sonarr_id=$(container_id sonarr)
qbittorrent_id=$(container_id qbittorrent)
appdata_fstype=${fstype}
EOF
  echo "DOCTOR_OK"
  echo "run_id=${run_id}"
  echo "appdata_fstype=${fstype}"
  echo "plex_id=$(container_id plex)"
  echo "radarr_id=$(container_id radarr)"
  echo "sonarr_id=$(container_id sonarr)"
  echo "qbittorrent_id=$(container_id qbittorrent)"
  echo "started_by_verify=no"
}

require_doctor() {
  if [[ ! -f "${STAMP}" ]]; then
    cmd_doctor >/dev/null
  fi
  # shellcheck disable=SC1090
  source "${STAMP}"
}

arr_summary() {
  local feature=$1 label=$2 config=$3 url=$4
  local key body
  key="$(api_key "${config}")"
  body="$(curl -sf --max-time 30 -H "X-Api-Key: ${key}" "${url}")"
  SUMMARY_LINE="$(printf '%s' "${body}" | python3 -c '
import json, sys
rows = json.load(sys.stdin)
titles = []
for row in rows:
    title = row.get("title") or ""
    year = row.get("year")
    if year:
        titles.append(f"{title} ({year})")
    elif title:
        titles.append(title)
print(f"count={len(rows)}")
for title in titles[:5]:
    print(f"title={title}")
')"
  append_out "${feature}" "${label}"
  append_out "${feature}" "${SUMMARY_LINE}"
}

plex_sections() {
  local feature=$1
  load_env
  local prefs token sections
  prefs="${APPDATA_PATH}/plex/Library/Application Support/Plex Media Server/Preferences.xml"
  token="$(python3 -c 'import xml.etree.ElementTree as ET,sys; print(ET.parse(sys.argv[1]).getroot().attrib.get("PlexOnlineToken",""))' "${prefs}")"
  sections="$(curl -sf --max-time 15 "http://127.0.0.1:32400/library/sections?X-Plex-Token=${token}")"
  local parsed
  parsed="$(printf '%s' "${sections}" | python3 -c '
import sys, xml.etree.ElementTree as ET
root = ET.fromstring(sys.stdin.read())
for d in root.findall("Directory"):
    locs = ",".join(l.get("path") or "" for l in d.findall("Location"))
    print(f"section={d.get(\"title\")} type={d.get(\"type\")} paths={locs}")
')"
  append_state "${feature}" "${parsed}"
}

cmd_drive() {
  local feature=${1:-}
  case "${feature}" in
    stack-health|movie-library|tv-library|download-client|dashboards|layout) ;;
    *) usage ;;
  esac
  require_doctor
  load_env
  case "${feature}" in
    stack-health)
      begin_proof stack-health "bash compose_files/scripts/health-check.sh"
      set +e
      bash "${COMPOSE_DIR}/scripts/health-check.sh" >"${PROOF_DIR}/stack-health/stdout.txt" 2>"${PROOF_DIR}/stack-health/stderr.txt"
      local code=$?
      set -e
      append_state stack-health "plex_identity_http=$(http_code http://127.0.0.1:32400/identity)"
      append_state stack-health "radarr_ping=$(curl -sf --max-time 10 http://127.0.0.1:7878/ping || true)"
      append_state stack-health "sonarr_ping=$(curl -sf --max-time 10 http://127.0.0.1:8989/ping || true)"
      finish_proof stack-health "${code}"
      echo "PROOF ${PROOF_DIR}/stack-health exit=${code}"
      return "${code}"
      ;;
    movie-library)
      begin_proof movie-library "GET /api/v3/movie and Plex library sections"
      arr_summary movie-library "radarr" "${APPDATA_PATH}/radarr/config.xml" "http://127.0.0.1:7878/api/v3/movie"
      plex_sections movie-library
      finish_proof movie-library 0
      echo "PROOF ${PROOF_DIR}/movie-library exit=0"
      ;;
    tv-library)
      begin_proof tv-library "GET /api/v3/series and Plex library sections"
      arr_summary tv-library "sonarr" "${APPDATA_PATH}/sonarr/config.xml" "http://127.0.0.1:8989/api/v3/series"
      plex_sections tv-library
      finish_proof tv-library 0
      echo "PROOF ${PROOF_DIR}/tv-library exit=0"
      ;;
    download-client)
      begin_proof download-client "GET http://127.0.0.1:8080/"
      local body
      body="$(curl -sf --max-time 10 http://127.0.0.1:8080/ || true)"
      if printf '%s' "${body}" | grep -q "qBittorrent WebUI"; then
        append_out download-client "http=200 title=qBittorrent WebUI"
        append_state download-client "title=qBittorrent WebUI"
        finish_proof download-client 0
        echo "PROOF ${PROOF_DIR}/download-client exit=0"
      else
        append_out download-client "title missing"
        finish_proof download-client 1
        echo "PROOF ${PROOF_DIR}/download-client exit=1" >&2
        return 1
      fi
      ;;
    dashboards)
      begin_proof dashboards "GET Panelarr :8000, Homarr :7575, Seerr :5055"
      local panel homarr seerr fail=0
      panel="$(http_code http://127.0.0.1:8000/)"
      homarr="$(http_code http://127.0.0.1:7575/)"
      seerr="$(http_code http://127.0.0.1:5055/)"
      append_out dashboards "panelarr_http=${panel}"
      append_out dashboards "homarr_http=${homarr}"
      append_out dashboards "seerr_http=${seerr}"
      local panel_html homarr_html seerr_html
      panel_html="$(curl -sf --max-time 10 http://127.0.0.1:8000/ || true)"
      homarr_html="$(curl -sf --max-time 10 http://127.0.0.1:7575/ || true)"
      seerr_html="$(curl -sf --max-time 10 http://127.0.0.1:5055/ || true)"
      if printf '%s' "${panel_html}" | grep -q "<title>Panelarr</title>"; then
        append_state dashboards "panelarr_title=Panelarr"
      else
        append_state dashboards "panelarr_title=missing"
        fail=1
      fi
      if printf '%s' "${homarr_html}" | grep -q 'data-mantine-color-scheme'; then
        append_state dashboards "homarr_shell=mantine"
      else
        append_state dashboards "homarr_shell=missing"
        fail=1
      fi
      if printf '%s' "${seerr_html}" | grep -q 'data-next-head'; then
        append_state dashboards "seerr_shell=next"
      else
        append_state dashboards "seerr_shell=missing"
        fail=1
      fi
      finish_proof dashboards "${fail}"
      echo "PROOF ${PROOF_DIR}/dashboards exit=${fail}"
      return "${fail}"
      ;;
    layout)
      begin_proof layout "bash compose_files/validate.sh"
      set +e
      bash "${COMPOSE_DIR}/validate.sh" >"${PROOF_DIR}/layout/stdout.txt" 2>"${PROOF_DIR}/layout/stderr.txt"
      local code=$?
      set -e
      if [[ "${code}" -eq 0 ]]; then
        append_state layout "validate=ok"
      else
        append_state layout "validate=fail"
      fi
      finish_proof layout "${code}"
      echo "PROOF ${PROOF_DIR}/layout exit=${code}"
      return "${code}"
      ;;
  esac
}

cmd_cleanup() {
  local scratch=""
  if [[ -f "${STAMP}" ]]; then
    # shellcheck disable=SC1090
    source "${STAMP}"
    scratch="${scratch:-}"
  fi
  if [[ -n "${scratch}" && "${scratch}" == /tmp/verify-media-server-* ]]; then
    rm -rf "${scratch}"
  fi
  rm -f "${STAMP}"
  echo "CLEANUP_OK proof=${PROOF_DIR}"
}

main() {
  local cmd=${1:-}
  shift || true
  case "${cmd}" in
    doctor) cmd_doctor ;;
    drive) cmd_drive "${1:-}" ;;
    cleanup) cmd_cleanup ;;
    *) usage ;;
  esac
}

main "$@"
