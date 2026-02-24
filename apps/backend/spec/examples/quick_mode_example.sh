#!/bin/bash
# Quick Mode Improvements - Example Usage
# ========================================

# Navigate to backend directory
cd "$(dirname "$0")/../.."

echo "Quick Mode Improvements Demo"
echo "============================"
echo ""

# Example 1: Template mode (instant generation)
echo "Example 1: Ultra-fast template mode"
echo "Task: 'fix typo in Header.tsx'"
echo "Expected: Instant generation using template (< 1 second)"
echo ""
python runners/spec_runner.py \
  --task "fix typo in Header.tsx" \
  --auto-approve \
  --no-build
echo ""

# Example 2: HTML plan generation
echo "Example 2: Interactive HTML plan review"
echo "Generating HTML plan for the spec created above..."
echo ""
# Find the most recent spec directory
SPEC_DIR=$(ls -td .auto-claude/specs/*/ | head -1)
if [ -n "$SPEC_DIR" ]; then
    echo "Generating HTML for: $SPEC_DIR"
    python -m review.html_generator "$SPEC_DIR" --open
    echo ""
    echo "HTML plan opened in browser!"
    echo "Location: ${SPEC_DIR}plan_review.html"
else
    echo "No spec directory found. Create one first."
fi
echo ""

# Example 3: Standard task (agent mode with optimized thinking)
echo "Example 3: Standard task with optimized thinking budget"
echo "Task: 'Add dark mode toggle to settings page'"
echo "Expected: Agent mode with reduced thinking budget for efficiency"
echo ""
python runners/spec_runner.py \
  --task "Add dark mode toggle to settings page" \
  --complexity simple \
  --thinking-level low \
  --auto-approve \
  --no-build
echo ""

echo "Demo complete!"
echo ""
echo "Key improvements demonstrated:"
echo "  ✓ Template-based fast path (Example 1)"
echo "  ✓ Interactive HTML plan review (Example 2)"
echo "  ✓ Optimized thinking budgets (Example 3)"
echo ""
echo "See QUICK_MODE_IMPROVEMENTS.md for full documentation"
