#!/bin/bash
# banana — installer
#
# Copies the skill into ~/.claude/skills/banana/. That is the whole job.
# It downloads nothing, installs no packages, and never touches settings.json.
#
#   ./install.sh              install (or reinstall cleanly)
#   ./install.sh --uninstall  remove

set -euo pipefail

SKILL_NAME="banana"
SKILL_DIR="$HOME/.claude/skills/$SKILL_NAME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/skills/$SKILL_NAME"
DATA_DIR="$HOME/.banana"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ "${1:-}" == "--uninstall" ]]; then
    if [[ -d "$SKILL_DIR" ]]; then
        rm -rf "$SKILL_DIR"
        info "Removed $SKILL_DIR"
    else
        warn "Not installed."
    fi
    info "Left in place: $DATA_DIR (your presets and cost ledger). Delete it yourself if you want it gone."
    exit 0
fi

[[ -d "$SOURCE_DIR" ]] || { error "Source not found: $SOURCE_DIR"; exit 1; }
command -v python3 >/dev/null 2>&1 || { error "python3 is required and was not found in PATH."; exit 1; }

# A clean install, not an overlay. Copying over an existing directory leaves
# stale files behind — including anything a previous, different build put there.
# What lands must be exactly what this repo ships.
if [[ -d "$SKILL_DIR" ]]; then
    info "Existing install found — replacing it entirely."
    rm -rf "$SKILL_DIR"
fi

info "Installing the banana skill..."
mkdir -p "$SKILL_DIR"
cp -R "$SOURCE_DIR"/. "$SKILL_DIR/"
chmod +x "$SKILL_DIR/scripts/"*.py 2>/dev/null || true
info "Installed to $SKILL_DIR"

mkdir -p "$DATA_DIR/presets"
info "Data directory ready at $DATA_DIR"

# Preserve a pricing file the user has already verified — reinstalling should
# not silently wipe rates they confirmed against Google's console.
if [[ -f "$DATA_DIR/pricing.json" ]]; then
    cp "$DATA_DIR/pricing.json" "$SKILL_DIR/scripts/pricing.json"
    info "Restored your verified pricing.json"
fi

echo ""
if [[ -n "${GOOGLE_AI_API_KEY:-}" ]]; then
    info "GOOGLE_AI_API_KEY is set."
else
    warn "GOOGLE_AI_API_KEY is not set. Add it to your shell profile:"
    echo ""
    echo "    echo 'export GOOGLE_AI_API_KEY=\"your-key\"' >> ~/.zshrc && source ~/.zshrc"
    echo ""
    echo "  Get a key: https://aistudio.google.com/apikey"
fi

echo ""
info "Done. Restart Claude Code, then try:"
echo "    /banana generate a red cube on a white background"
echo ""
echo "  Cost tracking starts inactive by design — no invented prices."
echo "  Once you have checked Google's rate, record it:"
echo "    python3 $SKILL_DIR/scripts/cost_tracker.py price \\"
echo "        --model gemini-3.1-flash-image-preview --resolution 2K --usd 0.00"
