"""
ML Inference Module - Make predictions using trained models
"""
import pandas as pd
import numpy as np
from typing import Union, List, Dict, Any
import logging
from ml.registry.model_registry import model_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLPredictor:
    """
    Handles predictions using registered models
    Supports single and batch predictions
    """

    def __init__(self):
        self.loaded_models = {}  # Cache for loaded models

    def _get_model(self, model_name: str, version: str = None):
        """Get model from cache or load from registry"""
        cache_key = f"{model_name}_{version}" if version else model_name

        if cache_key not in self.loaded_models:
            model = model_registry.load_model(model_name, version)
            metadata = model_registry.get_model_metadata(model_name, version)
            self.loaded_models[cache_key] = {
                "model": model,
                "metadata": metadata
            }
            logger.info(f"Loaded and cached model: {cache_key}")

        return self.loaded_models[cache_key]

    def predict(
        self,
        model_name: str,
        features: Union[Dict, pd.DataFrame, List],
        version: str = None,
        return_proba: bool = False
    ) -> Union[float, int, np.ndarray, List]:
        """
        Make prediction(s) using a registered model

        Args:
            model_name: Name of the registered model
            features: Input features (dict for single, DataFrame/list for batch)
            version: Model version (uses latest if not specified)
            return_proba: Return probabilities for classification (default: False)

        Returns:
            Prediction(s) - format depends on input type and return_proba
        """
        try:
            model_info = self._get_model(model_name, version)
            model = model_info["model"]
            metadata = model_info["metadata"]

            # Convert input to DataFrame
            if isinstance(features, dict):
                df = pd.DataFrame([features])
                single_pred = True
            elif isinstance(features, list):
                df = pd.DataFrame(features)
                single_pred = False
            elif isinstance(features, pd.DataFrame):
                df = features
                single_pred = len(df) == 1
            else:
                raise ValueError(f"Unsupported features type: {type(features)}")

            # Ensure correct feature order
            feature_columns = metadata.get("feature_columns", [])
            if feature_columns:
                # Check if all required features are present
                missing_features = set(feature_columns) - set(df.columns)
                if missing_features:
                    raise ValueError(f"Missing features: {missing_features}")

                # Reorder columns to match training
                df = df[feature_columns]

            # Make prediction
            if return_proba and hasattr(model, 'predict_proba'):
                predictions = model.predict_proba(df)
                # For binary classification, return probability of positive class
                if predictions.shape[1] == 2:
                    predictions = predictions[:, 1]
            else:
                predictions = model.predict(df)

            # Return format
            if single_pred:
                return float(predictions[0]) if predictions.ndim == 1 else predictions[0].tolist()
            else:
                return predictions.tolist() if isinstance(predictions, np.ndarray) else predictions

        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise

    def predict_batch(
        self,
        model_name: str,
        features_df: pd.DataFrame,
        version: str = None,
        return_proba: bool = False
    ) -> pd.DataFrame:
        """
        Make batch predictions and return DataFrame with predictions

        Args:
            model_name: Name of the registered model
            features_df: DataFrame with features
            version: Model version
            return_proba: Return probabilities

        Returns:
            Original DataFrame with prediction column(s) added
        """
        predictions = self.predict(model_name, features_df, version, return_proba)

        result_df = features_df.copy()

        if return_proba:
            result_df[f"{model_name}_proba"] = predictions
        else:
            result_df[f"{model_name}_prediction"] = predictions

        return result_df

    def predict_from_query(
        self,
        model_name: str,
        query: str,
        connection_id: str = None,
        version: str = None,
        return_proba: bool = False
    ) -> pd.DataFrame:
        """
        Execute SQL query and make predictions on results

        Args:
            model_name: Name of the registered model
            query: SQL query to fetch features
            connection_id: Database connection ID
            version: Model version
            return_proba: Return probabilities

        Returns:
            DataFrame with query results and predictions
        """
        from connection_manager import connection_manager

        # Execute query
        with connection_manager.get_connection(connection_id) as pg:
            df = pg.query_to_dataframe(query)

        logger.info(f"Fetched {len(df)} rows from query")

        # Make predictions
        return self.predict_batch(model_name, df, version, return_proba)

    def get_feature_importance(self, model_name: str, version: str = None) -> Dict[str, float]:
        """
        Get feature importance from model (if available)

        Args:
            model_name: Name of the registered model
            version: Model version

        Returns:
            Dictionary of feature names and their importance scores
        """
        model_info = self._get_model(model_name, version)
        model = model_info["model"]
        metadata = model_info["metadata"]

        feature_columns = metadata.get("feature_columns", [])

        # Try different methods to get feature importance
        if hasattr(model, 'feature_importances_'):
            # Tree-based models (RF, GBM, etc.)
            importances = model.feature_importances_
        elif hasattr(model, 'coef_'):
            # Linear models
            importances = np.abs(model.coef_).flatten()
        else:
            raise AttributeError(f"Model {model_name} does not support feature importance")

        return dict(zip(feature_columns, importances.tolist()))


# Global predictor instance
ml_predictor = MLPredictor()


if __name__ == "__main__":
    # Test predictor
    print("ML Predictor Test\n")
    print("=" * 60)

    # List available models
    models = model_registry.list_models()
    if models:
        print("\n📊 Available Models:")
        for model in models:
            print(f"  • {model['model_name']} (v{model['latest_version']})")
    else:
        print("\n⚠️  No models registered yet")
        print("   Train a model first using the training module")
