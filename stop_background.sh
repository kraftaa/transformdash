#!/bin/bash
# Script to stop TransformDash running in background
#
# Usage:
#   ./stop_background.sh
#
# This will:
#   - Read PID from transformdash.pid
#   - Kill the process
#   - Clean up the PID file

if [ -f transformdash.pid ]; then
    PID=$(cat transformdash.pid)
    kill $PID 2>/dev/null && echo "✓ Stopped TransformDash (PID: $PID)" || echo "✗ Process not found (may have already stopped)"
    rm transformdash.pid
else
    echo "✗ No PID file found. Is TransformDash running?"
    echo "  Check manually: ps aux | grep 'python ui/app.py' | grep -v grep"
fi
