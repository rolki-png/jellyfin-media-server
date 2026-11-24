# shellcheck shell=bash
# Load KEY=VAL from $1 into the current shell without `source` (keeps `&`).
# Usage from a sibling script:
#   # shellcheck source=load-dotenv.sh
#   source "${SCRIPT_DIR}/load-dotenv.sh" "${ENV_FILE}"
_dotenv_file=${1:?dotenv path required}
_dotenv_scripts="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
eval "$(
  ENV_FILE="${_dotenv_file}" PYTHONPATH="${_dotenv_scripts}" python3 - <<'ENVPY'
from __future__ import annotations

import os
import shlex

from stack_policy.envfile import load_env_file

for key, value in load_env_file(os.environ["ENV_FILE"]).items():
    print(f"export {key}={shlex.quote(value)}")
ENVPY
)"
unset _dotenv_file _dotenv_scripts
