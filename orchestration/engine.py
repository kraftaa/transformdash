"""
Orchestration Engine - Executes transformations in DAG order
"""
from typing import List, Dict, Any
from datetime import datetime
from transformations import TransformationModel, DAG

class ExecutionContext:
    """Stores results and metadata from transformation executions"""
    def __init__(self):
        self.results = {}
        self.metadata = {}
        self.start_time = None
        self.end_time = None
        self.logs = []

    def add_result(self, model_name: str, result: Any, execution_time: float):
        self.results[model_name] = result
        self.metadata[model_name] = {
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }

    def add_error(self, model_name: str, error: str, execution_time: float):
        self.metadata[model_name] = {
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "status": "failed",
            "error": error
        }

    def add_log(self, message: str, level: str = "INFO"):
        """Add a log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)

    def get_summary(self) -> Dict[str, Any]:
        total_time = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        successes = sum(1 for m in self.metadata.values() if m["status"] == "success")
        failures = sum(1 for m in self.metadata.values() if m["status"] == "failed")

        return {
            "total_models": len(self.metadata),
            "successes": successes,
            "failures": failures,
            "total_execution_time": total_time,
            "models": self.metadata,
            "logs": self.logs
        }


class TransformationEngine:
    """Main orchestration engine that executes DAG of transformations"""

    def __init__(self, models: List[TransformationModel]):
        self.dag = DAG(models)
        self.context = ExecutionContext()

    def run(self, verbose: bool = True) -> ExecutionContext:
        """Execute all transformations in topological order"""
        self.context.start_time = datetime.now()
        self.context.add_log("Starting transformation pipeline", "INFO")

        if verbose:
            print("\n" + "=" * 60)
            print("TRANSFORMDASH - Transformation Engine")
            print("=" * 60)
            print(self.dag.visualize())
            print("\nStarting execution...")
            print("=" * 60 + "\n")

        execution_order = self.dag.get_execution_order()
        self.context.add_log(f"Execution order: {' → '.join(execution_order)}", "INFO")

        for model_name in execution_order:
            model = self.dag.models[model_name]
            start = datetime.now()

            try:
                self.context.add_log(f"Executing: {model_name} [{model.model_type.value}]", "INFO")

                if verbose:
                    print(f"▶ Executing: {model_name} [{model.model_type.value}]")

                # Execute model with context containing results from dependencies
                result = model.execute(self.context.results)

                end = datetime.now()
                execution_time = (end - start).total_seconds()

                self.context.add_result(model_name, result, execution_time)
                self.context.add_log(f"Completed: {model_name} in {execution_time:.3f}s", "SUCCESS")

                if verbose:
                    print(f"  ✓ Completed in {execution_time:.3f}s")
                    if isinstance(result, dict) and 'rows_affected' in result:
                        print(f"  └─ Rows affected: {result['rows_affected']}")
                    print()

            except Exception as e:
                end = datetime.now()
                execution_time = (end - start).total_seconds()
                self.context.add_error(model_name, str(e), execution_time)
                self.context.add_log(f"Failed: {model_name} - {str(e)}", "ERROR")

                if verbose:
                    print(f"  ✗ Failed after {execution_time:.3f}s")
                    print(f"  └─ Error: {str(e)}")
                    print()

                # Optionally stop on first failure
                # raise

        self.context.end_time = datetime.now()
        total_time = (self.context.end_time - self.context.start_time).total_seconds()
        self.context.add_log(f"Pipeline completed in {total_time:.3f}s", "INFO")

        if verbose:
            self._print_summary()

        return self.context

    def _print_summary(self):
        """Print execution summary"""
        summary = self.context.get_summary()

        print("=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total Models: {summary['total_models']}")
        print(f"✓ Successes: {summary['successes']}")
        print(f"✗ Failures: {summary['failures']}")
        print(f"⏱  Total Time: {summary['total_execution_time']:.3f}s")
        print("=" * 60 + "\n")
