"""
Jinja2 Functions for ML Integration
These functions can be used directly in dbt models
"""
import pandas as pd
from typing import List, Union, Dict, Any
from ml.inference.predictor import ml_predictor
from ml.registry.model_registry import model_registry
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ml_predict(model_name: str, feature_columns: List[str], version: str = None, return_proba: bool = False) -> str:
    """
    Generate SQL for ML predictions in dbt models

    Usage in dbt model:
        SELECT
            customer_id,
            recency,
            frequency,
            monetary,
            {{ ml_predict('customer_churn', ['recency', 'frequency', 'monetary']) }} as churn_prediction
        FROM customer_features

    Args:
        model_name: Name of registered model
        feature_columns: List of column names to use as features
        version: Model version (optional, uses latest)
        return_proba: Return probability instead of class (for classification)

    Returns:
        SQL expression for prediction
    """
    try:
        # Verify model exists
        metadata = model_registry.get_model_metadata(model_name, version)

        # Build SQL case statement that will call Python function
        # This is a placeholder - actual implementation will use a UDF or external call
        features_str = ", ".join(feature_columns)

        # For now, return a SQL comment with instructions
        # In production, this would create a UDF or call an API
        sql = f"""
        -- ML Prediction: {model_name}
        -- Features: {features_str}
        -- Note: Implement UDF or API call for production use
        0.0  -- Placeholder for {model_name} prediction
        """.strip()

        return sql

    except Exception as e:
        logger.error(f"Error generating ML prediction SQL: {str(e)}")
        return "NULL  -- ML prediction error"


def ml_batch_predict(
    model_name: str,
    table_name: str,
    feature_columns: List[str],
    id_column: str = 'id',
    version: str = None,
    return_proba: bool = False
) -> str:
    """
    Generate SQL for batch ML predictions using lateral join

    Usage in dbt model:
        {{ ml_batch_predict(
            'customer_churn',
            'customer_features',
            ['recency', 'frequency', 'monetary'],
            'customer_id'
        ) }}

    Args:
        model_name: Name of registered model
        table_name: Source table name
        feature_columns: List of feature column names
        id_column: ID column name
        version: Model version
        return_proba: Return probabilities

    Returns:
        SQL query with predictions
    """
    features_str = ", ".join(feature_columns)

    sql = f"""
    SELECT
        t.{id_column},
        {", ".join([f"t.{col}" for col in feature_columns])},
        0.0 as {model_name}_prediction  -- Placeholder
    FROM {table_name} t
    -- Note: Implement batch prediction UDF for production
    """.strip()

    return sql


def ml_feature_importance(model_name: str, version: str = None, limit: int = 10) -> str:
    """
    Get feature importance from trained model

    Usage:
        {{ ml_feature_importance('customer_churn', limit=5) }}

    Returns:
        SQL comment with top features
    """
    try:
        importances = ml_predictor.get_feature_importance(model_name, version)

        # Sort by importance
        sorted_features = sorted(
            importances.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        # Format as SQL comment
        lines = ["-- Feature Importance:"]
        for feature, importance in sorted_features:
            lines.append(f"--   {feature}: {importance:.4f}")

        return "\n".join(lines)

    except Exception as e:
        return f"-- Error getting feature importance: {str(e)}"


def ml_models_list() -> str:
    """
    List all registered ML models as SQL comment

    Usage:
        {{ ml_models_list() }}

    Returns:
        SQL comment with available models
    """
    try:
        models = model_registry.list_models()

        if not models:
            return "-- No ML models registered"

        lines = ["-- Available ML Models:"]
        for model in models:
            lines.append(f"--   • {model['model_name']} (v{model['latest_version']}) - {model['model_type']}")

        return "\n".join(lines)

    except Exception as e:
        return f"-- Error listing models: {str(e)}"


# Dictionary of all ML Jinja functions
ML_JINJA_FUNCTIONS = {
    'ml_predict': ml_predict,
    'ml_batch_predict': ml_batch_predict,
    'ml_feature_importance': ml_feature_importance,
    'ml_models_list': ml_models_list,
}


if __name__ == "__main__":
    print("ML Jinja Functions\n")
    print("=" * 60)

    print("\n📋 Available Functions:")
    print("  • ml_predict() - Single/row-level predictions")
    print("  • ml_batch_predict() - Batch predictions")
    print("  • ml_feature_importance() - Get feature importance")
    print("  • ml_models_list() - List available models")

    print("\n\n📝 Example Usage in dbt model:")
    print("""
    {{ config(materialized='table') }}

    SELECT
        customer_id,
        recency,
        frequency,
        monetary,
        {{ ml_predict('customer_churn', ['recency', 'frequency', 'monetary']) }} as churn_score
    FROM {{ ref('customer_features') }}
    """)
