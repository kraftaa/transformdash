"""
Example: Train a customer churn model with sample data
This demonstrates the complete ML workflow
"""
import pandas as pd
import numpy as np
from ml.training.churn_trainer import ChurnTrainer

# Generate sample customer data
np.random.seed(42)

n_customers = 1000

# Create synthetic customer features
data = {
    'customer_id': range(1, n_customers + 1),
    'recency': np.random.randint(1, 180, n_customers),  # Days since last order
    'frequency': np.random.randint(1, 50, n_customers),  # Number of orders
    'monetary': np.random.uniform(10, 5000, n_customers),  # Total spent
    'avg_order_value': np.random.uniform(10, 200, n_customers),
    'days_since_signup': np.random.randint(30, 1000, n_customers),
}

df = pd.DataFrame(data)

# Create target variable (churned)
# Higher recency and lower frequency = higher churn probability
df['churn_score'] = (df['recency'] / df['recency'].max()) - (df['frequency'] / df['frequency'].max())
df['churned'] = (df['churn_score'] > 0.2).astype(int)
df = df.drop('churn_score', axis=1)

print("Sample Customer Data:")
print("=" * 60)
print(df.head(10))
print(f"\nTotal customers: {len(df)}")
print(f"Churned: {df['churned'].sum()} ({df['churned'].mean()*100:.1f}%)")
print(f"Active: {(1-df['churned']).sum()} ({(1-df['churned']).mean()*100:.1f}%)")

# Train model
print("\n" + "=" * 60)
print("Training Churn Prediction Model")
print("=" * 60)

trainer = ChurnTrainer()

model_id, metrics = trainer.train_and_register(
    df=df,
    target_column='churned',
    test_size=0.2,
    # Model hyperparameters
    n_estimators=100,
    max_depth=10,
    min_samples_split=5
)

print("\n" + "=" * 60)
print("✅ Training Complete!")
print("=" * 60)
print(f"Model ID: {model_id}")
print("\nMetrics:")
for metric, value in metrics.items():
    print(f"  {metric}: {value:.4f}")

# Make predictions on new data
print("\n" + "=" * 60)
print("Making Predictions on New Customers")
print("=" * 60)

from ml.inference.predictor import ml_predictor

new_customers = pd.DataFrame({
    'customer_id': [10001, 10002, 10003],
    'recency': [10, 90, 150],
    'frequency': [25, 5, 1],
    'monetary': [2500, 300, 50],
    'avg_order_value': [100, 60, 50],
    'days_since_signup': [365, 200, 400]
})

# Apply same preprocessing as training
new_customers = trainer.preprocess_features(new_customers)

print("\nNew Customer Features:")
print(new_customers)

predictions = ml_predictor.predict_batch(
    model_name='customer_churn',
    features_df=new_customers,
    return_proba=True
)

print("\nPredictions:")
print(predictions[['recency', 'frequency', 'monetary', 'customer_churn_proba']])
print("\nInterpretation:")
for idx, row in predictions.iterrows():
    risk_level = "HIGH" if row['customer_churn_proba'] > 0.7 else "MEDIUM" if row['customer_churn_proba'] > 0.4 else "LOW"
    print(f"  Customer {idx+1}: {row['customer_churn_proba']:.2%} churn probability - {risk_level} RISK")

# Show feature importance
print("\n" + "=" * 60)
print("Feature Importance")
print("=" * 60)

importance = ml_predictor.get_feature_importance('customer_churn')
sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

for feature, score in sorted_importance:
    bar = "█" * int(score * 50)
    print(f"  {feature:20s} {bar} {score:.4f}")

print("\n" + "=" * 60)
print("Example Complete!")
print("=" * 60)
print("\nNext Steps:")
print("  1. View model in registry: python ml/registry/model_registry.py")
print("  2. Make more predictions: python ml/inference/predictor.py")
print("  3. Use in dbt models: See ml/README.md for examples")
