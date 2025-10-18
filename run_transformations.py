"""
Run Transformations - Execute the full dbt-style transformation pipeline
Runs Bronze → Silver → Gold layers in order
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from transformations.dbt_loader import DBTModelLoader
from orchestration.engine import TransformationEngine
from orchestration.history import RunHistory
from datetime import datetime


def run_pipeline():
    """Execute the full transformation pipeline"""
    print("\n" + "=" * 60)
    print("🚀 RUNNING TRANSFORMATION PIPELINE")
    print("=" * 60 + "\n")

    # Load models from files
    models_dir = Path(__file__).parent / "models"
    loader = DBTModelLoader(models_dir=str(models_dir))

    print("📂 Loading SQL models...")
    models = loader.load_all_models()
    print(f"✓ Loaded {len(models)} models\n")

    # Create engine and run
    engine = TransformationEngine(models)
    context = engine.run(verbose=True)

    # Save to history
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    history = RunHistory()
    summary = context.get_summary()
    history.save_run(run_id, summary, context.logs)

    print(f"\n💾 Run saved to history: {run_id}")

    return context


if __name__ == "__main__":
    try:
        context = run_pipeline()

        # Exit with error code if any failures
        if context.get_summary()['failures'] > 0:
            print("\n⚠️  Pipeline completed with failures")
            sys.exit(1)
        else:
            print("\n✅ Pipeline completed successfully!")
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
