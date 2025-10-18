"""
Execution History and Logging
Tracks all transformation runs with detailed logs
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import os


class RunHistory:
    """Track execution history for all transformation runs"""

    def __init__(self, history_dir: str = "runs"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(exist_ok=True)

    def save_run(self, run_id: str, summary: Dict[str, Any], logs: List[str]) -> None:
        """Save a completed run to history"""
        run_data = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "logs": logs
        }

        run_file = self.history_dir / f"{run_id}.json"
        with open(run_file, 'w') as f:
            json.dump(run_data, f, indent=2)

    def get_all_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all runs, most recent first"""
        runs = []

        for run_file in sorted(self.history_dir.glob("*.json"), reverse=True):
            try:
                with open(run_file, 'r') as f:
                    run_data = json.load(f)
                    runs.append(run_data)

                if len(runs) >= limit:
                    break
            except Exception:
                continue

        return runs

    def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get specific run details"""
        run_file = self.history_dir / f"{run_id}.json"

        if not run_file.exists():
            raise FileNotFoundError(f"Run {run_id} not found")

        with open(run_file, 'r') as f:
            return json.load(f)

    def delete_old_runs(self, keep_last: int = 100):
        """Delete old run history, keeping only the most recent"""
        run_files = sorted(self.history_dir.glob("*.json"), reverse=True)

        for run_file in run_files[keep_last:]:
            run_file.unlink()


class LogCapture:
    """Capture logs during execution"""

    def __init__(self):
        self.logs = []

    def log(self, message: str, level: str = "INFO"):
        """Add a log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        print(log_entry)  # Also print to console

    def get_logs(self) -> List[str]:
        """Get all captured logs"""
        return self.logs

    def clear(self):
        """Clear all logs"""
        self.logs = []
