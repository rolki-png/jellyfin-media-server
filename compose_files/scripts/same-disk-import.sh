#!/usr/bin/env bash
# Sonarr/Radarr Connect → Custom Script (On Import / On Upgrade)
#
# Policy (lazy same-disk):
# - Prefer a single inode via hardlink (download path is canonical for seeding).
# - If the title library folder is on a different disk than the download, migrate
#   that whole title folder onto the download's disk, then hardlink.
#
# Requires branch roots mounted in the *arr container (see compose).
set -euo pipefail

log() { echo "same-disk-import: $*" >&2; }

COMMON_PATH="${COMMON_PATH:-/mnt/combined-media/Isyrr}"
SSD_ROOT="${SAME_DISK_SSD_ROOT:-/mnt/samsung-media/Isyrr}"
HDD_ROOT="${SAME_DISK_HDD_ROOT:-/mnt/4tb-media-2/Isyrr}"

event="${sonarr_eventtype:-${radarr_eventtype:-}}"
case "${event}" in
  Test) log "test ok"; exit 0 ;;
  Download|Upgrade|ImportComplete) ;;
  *) log "ignore event=${event:-empty}"; exit 0 ;;
esac

if [[ -n "${sonarr_eventtype:-}" ]]; then
  title_path="${sonarr_series_path:-}"
  library_file="${sonarr_episodefile_path:-}"
  source_file="${sonarr_episodefile_sourcepath:-}"
elif [[ -n "${radarr_eventtype:-}" ]]; then
  title_path="${radarr_movie_path:-}"
  library_file="${radarr_moviefile_path:-}"
  source_file="${radarr_moviefile_sourcepath:-}"
else
  log "no sonarr/radarr env; exit"
  exit 0
fi

if [[ -z "${library_file}" || -z "${source_file}" ]]; then
  log "missing library/source path; library=${library_file:-} source=${source_file:-}"
  exit 0
fi

if [[ ! -f "${source_file}" ]]; then
  log "source missing: ${source_file}"
  exit 0
fi

# Already hardlinked → nothing to do
if [[ -f "${library_file}" ]]; then
  lib_ino="$(stat -c '%d:%i' "${library_file}")"
  src_ino="$(stat -c '%d:%i' "${source_file}")"
  if [[ "${lib_ino}" == "${src_ino}" ]]; then
    log "already hardlinked: ${library_file}"
    exit 0
  fi
fi

branch_of() {
  local f=$1
  local rel=""
  case "${f}" in
    "${COMMON_PATH}"/*) rel="${f#"${COMMON_PATH}"/}" ;;
    "${SSD_ROOT}"/*) echo ssd; return 0 ;;
    "${HDD_ROOT}"/*) echo hdd; return 0 ;;
  esac
  if [[ -n "${rel}" ]]; then
    # mergerfs use_ino exposes synthetic inodes that do NOT match the
    # underlying branch inode — detect by real path existence instead.
    local hdd_p="${HDD_ROOT}/${rel}"
    local ssd_p="${SSD_ROOT}/${rel}"
    if [[ -e "${hdd_p}" && -e "${ssd_p}" ]]; then
      # Both present (rare): pick the larger / non-empty file.
      local hs ss
      hs=$(stat -c '%s' "${hdd_p}" 2>/dev/null || echo 0)
      ss=$(stat -c '%s' "${ssd_p}" 2>/dev/null || echo 0)
      if [[ "${hs}" -ge "${ss}" ]]; then echo hdd; else echo ssd; fi
      return 0
    fi
    if [[ -e "${hdd_p}" ]]; then echo hdd; return 0; fi
    if [[ -e "${ssd_p}" ]]; then echo ssd; return 0; fi
  fi
  echo unknown
}

rel_from_common() {
  local f=$1
  case "${f}" in
    "${COMMON_PATH}"/*) echo "${f#"${COMMON_PATH}"/}" ;;
    "${SSD_ROOT}"/*) echo "${f#"${SSD_ROOT}"/}" ;;
    "${HDD_ROOT}"/*) echo "${f#"${HDD_ROOT}"/}" ;;
    *) echo "" ;;
  esac
}

src_branch="$(branch_of "${source_file}")"
log "source_branch=${src_branch} source=${source_file}"

if [[ "${src_branch}" != "ssd" && "${src_branch}" != "hdd" ]]; then
  # Fallback: try hardlink via mergerfs only
  log "branch unknown; attempting mergerfs hardlink replace"
  mkdir -p "$(dirname "${library_file}")"
  tmp="${library_file}.same-disk-new"
  rm -f "${tmp}"
  if ln "${source_file}" "${tmp}"; then
    rm -f "${library_file}"
    mv -f "${tmp}" "${library_file}"
    log "hardlinked via mergerfs"
    exit 0
  fi
  rm -f "${tmp}"
  log "hardlink failed (unknown branch)"
  exit 0
fi

target_root=$SSD_ROOT
[[ "${src_branch}" == "hdd" ]] && target_root=$HDD_ROOT
other_root=$HDD_ROOT
[[ "${src_branch}" == "hdd" ]] && other_root=$SSD_ROOT

title_rel="$(rel_from_common "${title_path}")"
if [[ -z "${title_rel}" ]]; then
  log "cannot map title_path=${title_path}"
  exit 0
fi

target_title="${target_root}/${title_rel}"
other_title="${other_root}/${title_rel}"

# Migrate whole title folder onto the download's disk when it still exists elsewhere
if [[ -d "${other_title}" ]]; then
  log "migrating title ${title_rel} -> ${src_branch}"
  mkdir -p "${target_title}"
  # Copy missing/different files onto target, then remove other-branch copies of same names
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --ignore-existing "${other_title}/" "${target_title}/"
  else
    cp -a --no-clobber "${other_title}/." "${target_title}/" 2>/dev/null || \
      cp -a "${other_title}/." "${target_title}/"
  fi
  # Remove other-branch tree only after target has the files
  rm -rf "${other_title}"
fi

mkdir -p "$(dirname "${target_root}/$(rel_from_common "${library_file}")")"
lib_rel="$(rel_from_common "${library_file}")"
target_lib="${target_root}/${lib_rel}"
src_rel="$(rel_from_common "${source_file}")"
# Prefer real source on target branch
if [[ -f "${target_root}/${src_rel}" ]]; then
  source_real="${target_root}/${src_rel}"
else
  source_real="${source_file}"
fi

mkdir -p "$(dirname "${target_lib}")"
if [[ -f "${target_lib}" ]]; then
  if [[ "$(stat -c '%d:%i' "${target_lib}")" == "$(stat -c '%d:%i' "${source_real}")" ]]; then
    log "target already hardlinked"
    # Clear leftover on other branch if any
    other_lib="${other_root}/${lib_rel}"
    [[ -f "${other_lib}" ]] && rm -f "${other_lib}"
    exit 0
  fi
  rm -f "${target_lib}"
fi

ln "${source_real}" "${target_lib}"
# Drop duplicate on the other branch if present
other_lib="${other_root}/${lib_rel}"
if [[ -f "${other_lib}" ]] && [[ "$(stat -c '%d:%i' "${other_lib}")" != "$(stat -c '%d:%i' "${source_real}")" ]]; then
  rm -f "${other_lib}"
fi

log "hardlinked ${source_real} -> ${target_lib}"
exit 0
