#!/bin/bash
# Script to run TransformDash in the background
#
# Usage:
#   ./run_in_background.sh
#
# This will:
#   - Start TransformDash in background
#   - Save process ID to transformdash.pid
#   - Save logs to transformdash.log
#
# To view logs:
#   tail -f transformdash.log    OR  tail -n 15 transformdash.log
#
# To stop:
#   ./stop_background.sh
#   OR
#   kill $(cat transformdash.pid)
#
# To check if running:
#   ps aux | grep "python ui/app.py" | grep -v grep

source venv/bin/activate
nohup python3 ui/app.py > transformdash.log 2>&1 &
echo $! > transformdash.pid
echo "✓ TransformDash started in background (PID: $(cat transformdash.pid))"
echo "✓ Access at: http://localhost:8000"
echo "✓ View logs: tail -f transformdash.log"
echo "✓ Stop with: ./stop_background.sh"
