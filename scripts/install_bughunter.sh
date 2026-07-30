#!/usr/bin/env bash
set -euo pipefail

# safe installer: clone BugHunter for local inspection only
# - This script CLONES a public repository into tools/Claude-BugHunter
# - It DOES NOT run any code from the cloned repo
# - You MUST inspect and run anything manually in an isolated environment

REPO="https://github.com/elementalsouls/Claude-BugHunter.git"
TARGET_DIR="tools/Claude-BugHunter"

echo "WARNING: This script clones a PUBLIC repo for local inspection only."
echo "Do NOT run networked or offensive code without explicit authorization and proper isolation."

if [ -d "$TARGET_DIR" ]; then
  echo "Target dir '$TARGET_DIR' already exists. To update, remove it first or run 'git -C $TARGET_DIR pull'."
  exit 1
fi

mkdir -p "$(dirname "$TARGET_DIR")"

echo "Cloning $REPO into $TARGET_DIR (shallow clone)..."
# shallow clone to save time; users can fetch more history if needed
git clone --depth 1 "$REPO" "$TARGET_DIR"

cat <<'EOF'
Done.
Next manual steps (recommended):
  1) Review the repository contents without executing anything:
       ls -la "$TARGET_DIR"
       less "$TARGET_DIR"/README.md
  2) Generate an SBOM / dependency list and run static analysis (examples):
       # Python example: run in a controlled environment
       # cd "$TARGET_DIR" && pip install --user pip-tools; pip-tools compile requirements.txt
       # static scanners: semgrep, bandit, trivy (for containers), or your org's approved scanners
  3) If you decide to run tools from the project, do so only in an isolated VM or container you control and with authorization.
  4) To update later (safe): git -C "$TARGET_DIR" pull --ff-only

Notes:
 - This script does not execute code from the cloned repo.
 - If you need me to add automated static scans that run locally and produce reports, I can add a separate safe script.
EOF
