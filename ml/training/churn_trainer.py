"""
Customer Churn Prediction Trainer
Example implementation using the BaseTrainer
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from ml.training.base_trainer import BaseTrainer


class ChurnTrainer(BaseTrainer):
    """
    Train a customer churn prediction model
    Predicts whether a customer will churn based on behavioral features
    """

    def __init__(self):
        super().__init__(
            model_name="customer_churn",
            model_type="classification",
            description="Predicts customer churn probability using Random Forest",
            tags=["customer", "churn", "classification", "rf"]
        )

    def build_model(self, **kwargs) -> RandomForestClassifier:
        """Build Random Forest classifier"""
        default_params = {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 5,
            'random_state': 42
        }
        default_params.update(kwargs)

        return RandomForestClassifier(**default_params)

    def preprocess_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess customer data for churn prediction

        Expected columns:
        - recency: Days since last purchase
        - frequency: Number of purchases
        - monetary: Total spend
        - avg_order_value: Average order value
        - days_since_signup: Account age
        - churned: Target variable (1=churned, 0=active)
        """
        # Handle missing values
        df = df.fillna(0)

        # Feature engineering
        if 'monetary' in df.columns and 'frequency' in df.columns:
            # Avoid division by zero
            df['avg_spend_per_order'] = df['monetary'] / (df['frequency'] + 1)

        if 'recency' in df.columns and 'frequency' in df.columns:
            # Engagement score
            df['engagement_score'] = df['frequency'] / (df['recency'] + 1)

        # Remove outliers (optional)
        for col in ['monetary', 'frequency', 'recency']:
            if col in df.columns:
                q99 = df[col].quantile(0.99)
                df[col] = df[col].clip(upper=q99)

        return df


if __name__ == "__main__":
    """
    Example usage:

    # Create trainer
    trainer = ChurnTrainer()

    # Train with SQL query
    model_id, metrics = trainer.train_and_register(
        query='''
            SELECT
                customer_id,
                days_since_last_order as recency,
                total_orders as frequency,
                total_spent as monetary,
                avg_order_value,
                days_since_signup,
                churned
            FROM customer_features
        ''',
        target_column='churned',
        connection_id='transformdash'
    )

    # Or train with DataFrame
    import pandas as pd
    df = pd.DataFrame({
        'recency': [10, 30, 5, 90, 15],
        'frequency': [20, 5, 30, 2, 15],
        'monetary': [1000, 200, 1500, 50, 800],
        'avg_order_value': [50, 40, 50, 25, 53],
        'days_since_signup': [365, 180, 730, 90, 400],
        'churned': [0, 1, 0, 1, 0]
    })

    model_id, metrics = trainer.train_and_register(
        df=df,
        target_column='churned'
    )
    """
    print("Churn Trainer Example")
    print("=" * 60)
    print("\nTo train a churn model:")
    print("1. Prepare customer features data")
    print("2. Run: trainer = ChurnTrainer()")
    print("3. Run: model_id, metrics = trainer.train_and_register(...)")
    print("\nSee code for full example")
