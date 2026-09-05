#!/usr/bin/env bash
set -euo pipefail
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"
for required_tool in git gitleaks; do
  command -v "$required_tool" >/dev/null 2>&1 || { echo "Missing required tool: $required_tool; see project/RELEASING.md" >&2; exit 1; }
done
test -x .venv/bin/python || { echo "Run the validation setup in project/RELEASING.md first." >&2; exit 1; }
bash -n scripts/validate-repository.sh scripts/validate-release.sh
.venv/bin/python -m unittest discover -s tests -q
exec .venv/bin/python scripts/validate.py repository
