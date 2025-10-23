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

    # Validate dependencies (catches circular dependencies)
    print("🔍 Validating dependencies...")
    try:
        from transformations.dag import DAG
        dag = DAG(models)
        print("✓ No circular dependencies detected")
        print(f"✓ Execution order determined for {len(models)} models\n")
    except ValueError as e:
        print(f"\n❌ DEPENDENCY VALIDATION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print("=" * 60)
        print("\n💡 Common causes:")
        print("  • Model A references Model B, and Model B references Model A")
        print("  • Bronze layer referencing Silver/Gold layers")
        print("  • Model referencing itself")
        print("\n📋 Fix by ensuring dependencies flow in one direction:")
        print("  Bronze (stg_*) → Silver (int_*) → Gold (fct_*)")
        raise

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
