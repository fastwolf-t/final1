#!/usr/bin/env bash
set -e

# moves to the project root
cd "$(dirname "$0")/.."

bash shell/check.sh
bash shell/test.sh
bash shell/run.sh