#!/usr/bin/env python
"""
Test: Simulate Circular Dependency Detection

This script demonstrates what happens when you accidentally create
a circular dependency in your models.

Usage: python test_circular_dependency.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from transformations.model import TransformationModel, ModelType
from transformations.dbt_loader import DBTModelLoader
from transformations.dag import DAG

def test_circular_dependency():
    """
    Simulate a circular dependency:
    model_a → model_b → model_c → model_a (CYCLE!)
    """
    print("\n" + "=" * 60)
    print("🧪 TESTING CIRCULAR DEPENDENCY DETECTION")
    print("=" * 60 + "\n")

    print("Creating models with circular dependency:")
    print("  model_a → model_b → model_c → model_a (CYCLE!)\n")

    # Create circular dependency
    model_a = TransformationModel(
        name='model_a',
        model_type=ModelType.SQL,
        sql_query='SELECT * FROM {{ ref("model_c") }}',
        depends_on=['model_c']
    )

    model_b = TransformationModel(
        name='model_b',
        model_type=ModelType.SQL,
        sql_query='SELECT * FROM {{ ref("model_a") }}',
        depends_on=['model_a']
    )

    model_c = TransformationModel(
        name='model_c',
        model_type=ModelType.SQL,
        sql_query='SELECT * FROM {{ ref("model_b") }}',
        depends_on=['model_b']
    )

    # Try to create DAG
    try:
        print("Attempting to create DAG...")
        dag = DAG([model_a, model_b, model_c])
        print("\n❌ TEST FAILED: Cycle was not detected!")
        print("   This should never happen!\n")
        return 1

    except ValueError as e:
        print(f"\n✅ TEST PASSED: Cycle detected!")
        print("=" * 60)
        print(f"Error message: {e}")
        print("=" * 60)
        print("\n💡 This is exactly what should happen when you have")
        print("   circular dependencies in your models.")
        print("\n📋 Your pipeline is protected against circular dependencies!")
        return 0


def test_valid_dependency():
    """
    Test valid dependency chain:
    stg_orders (bronze) → int_orders (silver) → fct_sales (gold)
    """
    print("\n" + "=" * 60)
    print("🧪 TESTING VALID DEPENDENCY CHAIN")
    print("=" * 60 + "\n")

    print("Creating models with valid dependencies:")
    print("  stg_orders → int_orders → fct_sales\n")

    # Create valid chain
    stg_orders = TransformationModel(
        name='stg_orders',
        model_type=ModelType.SQL,
        sql_query='SELECT * FROM raw.orders',
        depends_on=[]
    )

    int_orders = TransformationModel(
        name='int_orders',
        model_type=ModelType.SQL,
        sql_query='SELECT * FROM {{ ref("stg_orders") }}',
        depends_on=['stg_orders']
    )

    fct_sales = TransformationModel(
        name='fct_sales',
        model_type=ModelType.SQL,
        sql_query='SELECT * FROM {{ ref("int_orders") }}',
        depends_on=['int_orders']
    )

    # Try to create DAG
    try:
        print("Attempting to create DAG...")
        dag = DAG([stg_orders, int_orders, fct_sales])
        execution_order = dag.get_execution_order()

        print("\n✅ TEST PASSED: Valid DAG created!")
        print("=" * 60)
        print("Execution order:", " → ".join(execution_order))
        print("=" * 60)
        print("\n📋 This is the correct pattern for dependencies!")
        return 0

    except ValueError as e:
        print(f"\n❌ TEST FAILED: Valid chain rejected!")
        print(f"   Error: {e}\n")
        return 1


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CIRCULAR DEPENDENCY PROTECTION TEST SUITE")
    print("=" * 60)

    # Run tests
    test1_result = test_circular_dependency()
    test2_result = test_valid_dependency()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    if test1_result == 0 and test2_result == 0:
        print("\n✅ ALL TESTS PASSED")
        print("\nYour pipeline is protected against circular dependencies!")
        print("Every time you run 'python run_transformations.py',")
        print("the system will validate dependencies BEFORE execution.\n")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nPlease check the error messages above.\n")
        sys.exit(1)
