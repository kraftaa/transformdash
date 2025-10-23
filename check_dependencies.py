#!/usr/bin/env python
"""
Check Model Dependencies - Visualize and validate dependency graph
Usage: python check_dependencies.py
"""
import sys
from pathlib import Path
from transformations.dbt_loader import DBTModelLoader
from transformations.dag import DAG

def main():
    models_dir = Path(__file__).parent / "models"

    print("\n" + "="*60)
    print("DEPENDENCY CHECKER")
    print("="*60 + "\n")

    # Load models
    loader = DBTModelLoader(models_dir=str(models_dir))
    models = loader.load_all_models()

    print(f"📂 Loaded {len(models)} models\n")

    # Try to build DAG (this will catch cycles)
    try:
        dag = DAG(models)
        print("✅ No circular dependencies detected!\n")

        # Show execution order
        execution_order = dag.get_execution_order()
        print("Execution Order:")
        print("-" * 60)

        for i, model_name in enumerate(execution_order, 1):
            model = dag.models[model_name]
            deps = ", ".join(model.depends_on) if model.depends_on else "None"
            print(f"{i:2}. {model_name:30} ← {deps}")

        # Show layer breakdown
        print("\n" + "="*60)
        print("LAYER BREAKDOWN")
        print("="*60)

        bronze = [m for m in models if not m.depends_on]
        silver = [m for m in models if m.depends_on and all(d.startswith('stg_') for d in m.depends_on)]
        gold = [m for m in models if m.depends_on and any(d.startswith('int_') or d.startswith('fct_') for d in m.depends_on)]

        print(f"\n🥉 Bronze Layer: {len(bronze)} models (no dependencies)")
        for m in bronze:
            print(f"   • {m.name}")

        print(f"\n🥈 Silver Layer: {len(silver)} models")
        for m in silver:
            print(f"   • {m.name} ← {', '.join(m.depends_on)}")

        print(f"\n🥇 Gold Layer: {len(gold)} models")
        for m in gold:
            print(f"   • {m.name} ← {', '.join(m.depends_on)}")

        print("\n" + "="*60)
        print("✅ ALL CHECKS PASSED")
        print("="*60 + "\n")

        return 0

    except ValueError as e:
        print(f"❌ ERROR: {e}\n")
        print("="*60)
        print("CIRCULAR DEPENDENCY DETECTED!")
        print("="*60)
        print("\nPlease review your {{ ref() }} statements to remove cycles.")
        print("Remember: Bronze → Silver → Gold (never backwards!)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
