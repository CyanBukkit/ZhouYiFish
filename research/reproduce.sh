#!/bin/sh
# One-command reproduction of the tests and the frozen offline trial.
set -eu
cd "$(dirname "$0")/.."
if ! python3 -c "import zhdate, pytest" 2>/dev/null; then
  echo "请先安装：python3 -m pip install -r research/requirements.txt" >&2
  exit 1
fi
python3 -m pytest research/tests -q
if [ -f research/experiments/offline_v1/score_summary.json ]; then
  python3 -m research.cli verify-offline
else
  python3 -m research.cli run-offline
fi
