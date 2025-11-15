"""
Base Trainer - Template for creating ML training pipelines
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, r2_score, mean_absolute_error
)
import logging
from abc import ABC, abstractmethod
from ml.registry.model_registry import model_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseTrainer(ABC):
    """
    Abstract base class for ML training pipelines
    Provides common functionality for training, evaluation, and registration
    """

    def __init__(
        self,
        model_name: str,
        model_type: str,
        description: str = "",
        tags: List[str] = None
    ):
        self.model_name = model_name
        self.model_type = model_type  # 'classification', 'regression', 'clustering'
        self.description = description
        self.tags = tags or []
        self.model = None
        self.feature_columns = None
        self.target_column = None
        self.metrics = {}

    @abstractmethod
    def build_model(self, **kwargs) -> Any:
        """
        Build the ML model
        Must be implemented by subclass
        """
        pass

    @abstractmethod
    def preprocess_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess features before training
        Must be implemented by subclass
        """
        pass

    def load_data(
        self,
        query: str = None,
        df: pd.DataFrame = None,
        connection_id: str = None
    ) -> pd.DataFrame:
        """
        Load training data from SQL query or DataFrame

        Args:
            query: SQL query to fetch data
            df: Pre-loaded DataFrame
            connection_id: Database connection ID

        Returns:
            DataFrame with training data
        """
        if df is not None:
            logger.info(f"Using provided DataFrame with {len(df)} rows")
            return df

        if query is None:
            raise ValueError("Must provide either query or df")

        from connection_manager import connection_manager

        with connection_manager.get_connection(connection_id) as pg:
            df = pg.query_to_dataframe(query)

        logger.info(f"✓ Loaded {len(df)} rows from query")
        return df

    def split_data(
        self,
        df: pd.DataFrame,
        target_column: str,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Split data into train/test sets

        Args:
            df: Full dataset
            target_column: Name of target column
            test_size: Proportion of data for testing
            random_state: Random seed

        Returns:
            X_train, X_test, y_train, y_test
        """
        self.target_column = target_column

        # Separate features and target
        X = df.drop(columns=[target_column])
        y = df[target_column]

        self.feature_columns = list(X.columns)

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state
        )

        logger.info(f"✓ Split data: {len(X_train)} train, {len(X_test)} test")
        logger.info(f"✓ Features: {len(self.feature_columns)}")

        return X_train, X_test, y_train, y_test

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        **kwargs
    ) -> Any:
        """
        Train the model

        Args:
            X_train: Training features
            y_train: Training targets
            **kwargs: Additional arguments for model training

        Returns:
            Trained model
        """
        if self.model is None:
            self.model = self.build_model(**kwargs)

        logger.info("🚀 Training model...")
        self.model.fit(X_train, y_train)
        logger.info("✓ Training complete")

        return self.model

    def evaluate_classification(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, float]:
        """Evaluate classification model"""
        y_pred = self.model.predict(X_test)

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
        }

        return metrics

    def evaluate_regression(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, float]:
        """Evaluate regression model"""
        y_pred = self.model.predict(X_test)

        metrics = {
            "mse": float(mean_squared_error(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "r2_score": float(r2_score(y_test, y_pred))
        }

        return metrics

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, float]:
        """
        Evaluate model performance

        Args:
            X_test: Test features
            y_test: Test targets

        Returns:
            Dictionary of evaluation metrics
        """
        logger.info("📊 Evaluating model...")

        if self.model_type == 'classification':
            self.metrics = self.evaluate_classification(X_test, y_test)
        elif self.model_type == 'regression':
            self.metrics = self.evaluate_regression(X_test, y_test)
        else:
            raise ValueError(f"Unsupported model type for evaluation: {self.model_type}")

        logger.info("✓ Evaluation complete")
        for metric_name, metric_value in self.metrics.items():
            logger.info(f"  {metric_name}: {metric_value:.4f}")

        return self.metrics

    def register(self, version: str = None) -> str:
        """
        Register trained model in registry

        Args:
            version: Model version (auto-generated if not provided)

        Returns:
            model_id: Unique identifier for registered model
        """
        if self.model is None:
            raise ValueError("No model to register. Train model first.")

        model_id = model_registry.register_model(
            model=self.model,
            model_name=self.model_name,
            model_type=self.model_type,
            version=version,
            metrics=self.metrics,
            feature_columns=self.feature_columns,
            target_column=self.target_column,
            description=self.description,
            tags=self.tags
        )

        return model_id

    def train_and_register(
        self,
        df: pd.DataFrame = None,
        query: str = None,
        target_column: str = None,
        connection_id: str = None,
        test_size: float = 0.2,
        version: str = None,
        **model_kwargs
    ) -> Tuple[str, Dict[str, float]]:
        """
        Complete training pipeline: load, train, evaluate, register

        Args:
            df: Pre-loaded DataFrame
            query: SQL query to load data
            target_column: Name of target column
            connection_id: Database connection ID
            test_size: Test set proportion
            version: Model version
            **model_kwargs: Additional model parameters

        Returns:
            (model_id, metrics): Registered model ID and evaluation metrics
        """
        # Load data
        data = self.load_data(query=query, df=df, connection_id=connection_id)

        # Preprocess
        data = self.preprocess_features(data)

        # Split
        X_train, X_test, y_train, y_test = self.split_data(
            data, target_column, test_size
        )

        # Train
        self.train(X_train, y_train, **model_kwargs)

        # Evaluate
        self.evaluate(X_test, y_test)

        # Register
        model_id = self.register(version)

        logger.info(f"\n✅ Training pipeline complete!")
        logger.info(f"   Model ID: {model_id}")

        return model_id, self.metrics
