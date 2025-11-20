# TransformDash ML Module

Machine Learning infrastructure for training, versioning, and serving predictions in your data transformation pipelines.

## 🏗️ Architecture

```
ml/
├── registry/          # Model versioning and storage
│   └── model_registry.py
├── training/          # Training pipelines
│   ├── base_trainer.py
│   └── churn_trainer.py
├── inference/         # Prediction serving
│   └── predictor.py
├── features/          # Feature engineering (optional)
├── models/            # Stored model artifacts (.pkl files)
└── jinja_functions.py # Jinja integration functions
```

## 🚀 Quick Start

### 1. Train a Model

```python
from ml.training.churn_trainer import ChurnTrainer

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

print(f"Model trained: {model_id}")
print(f"Metrics: {metrics}")
```

### 2. Make Predictions (Python)

```python
from ml.inference.predictor import ml_predictor

# Single prediction
prediction = ml_predictor.predict(
    model_name='customer_churn',
    features={
        'recency': 30,
        'frequency': 5,
        'monetary': 200
    },
    return_proba=True
)

print(f"Churn probability: {prediction}")

# Batch predictions
import pandas as pd
df = pd.DataFrame({
    'recency': [10, 30, 60],
    'frequency': [20, 5, 2],
    'monetary': [1000, 200, 50]
})

predictions_df = ml_predictor.predict_batch('customer_churn', df, return_proba=True)
```

### 3. Use in SQL Models

```sql
{{ config(materialized='table') }}

-- List available models
{{ ml_models_list() }}

-- Feature importance
{{ ml_feature_importance('customer_churn', limit=5) }}

SELECT
    customer_id,
    recency,
    frequency,
    monetary,
    -- ML predictions (placeholder for now)
    {{ ml_predict('customer_churn', ['recency', 'frequency', 'monetary']) }} as churn_score
FROM {{ ref('customer_features') }}
```

## 📚 Core Components

### Model Registry

Manages model versions, metadata, and artifacts:

```python
from ml.registry.model_registry import model_registry

# List all models
models = model_registry.list_models()

# Load specific version
model = model_registry.load_model('customer_churn', version='20251114_120000')

# Get metadata
metadata = model_registry.get_model_metadata('customer_churn')

# List versions
versions = model_registry.list_model_versions('customer_churn')
```

### Base Trainer

Template for creating custom training pipelines:

```python
from ml.training.base_trainer import BaseTrainer
from sklearn.linear_model import LogisticRegression

class MyTrainer(BaseTrainer):
    def __init__(self):
        super().__init__(
            model_name="my_model",
            model_type="classification",
            description="My custom model",
            tags=["custom", "classification"]
        )

    def build_model(self, **kwargs):
        return LogisticRegression(**kwargs)

    def preprocess_features(self, df):
        # Custom preprocessing
        df = df.fillna(0)
        # ... more preprocessing
        return df
```

### ML Predictor

Make predictions using registered models:

```python
from ml.inference.predictor import ml_predictor

# Predict from SQL query
results = ml_predictor.predict_from_query(
    model_name='customer_churn',
    query='SELECT * FROM customer_features',
    connection_id='transformdash',
    return_proba=True
)

# Get feature importance
importance = ml_predictor.get_feature_importance('customer_churn')
```

## 🎯 Example: Customer Churn Prediction

### Step 1: Prepare Data

```sql
-- Create features table
CREATE TABLE customer_features AS
SELECT
    customer_id,
    DATEDIFF(CURRENT_DATE, last_order_date) as recency,
    COUNT(order_id) as frequency,
    SUM(order_amount) as monetary,
    AVG(order_amount) as avg_order_value,
    DATEDIFF(CURRENT_DATE, signup_date) as days_since_signup,
    CASE WHEN last_order_date < CURRENT_DATE - INTERVAL '90 days' THEN 1 ELSE 0 END as churned
FROM orders
GROUP BY customer_id;
```

### Step 2: Train Model

```python
from ml.training.churn_trainer import ChurnTrainer

trainer = ChurnTrainer()
model_id, metrics = trainer.train_and_register(
    query='SELECT * FROM customer_features',
    target_column='churned',
    n_estimators=200,  # Model hyperparameters
    max_depth=15
)

# Output:
# ✓ Loaded 10000 rows from query
# ✓ Split data: 8000 train, 2000 test
# ✓ Features: 5
# 🚀 Training model...
# ✓ Training complete
# 📊 Evaluating model...
# ✓ Evaluation complete
#   accuracy: 0.8950
#   precision: 0.8765
#   recall: 0.8654
#   f1_score: 0.8709
# ✓ Registered model: customer_churn_v20251114_120000
```

### Step 3: Make Predictions

```python
from ml.inference.predictor import ml_predictor

# Predict churn for all active customers
results = ml_predictor.predict_from_query(
    model_name='customer_churn',
    query='''
        SELECT *
        FROM customer_features
        WHERE churned = 0
    ''',
    return_proba=True
)

# Get high-risk customers
high_risk = results[results['customer_churn_proba'] > 0.7]
print(f"High-risk customers: {len(high_risk)}")
```

## 🔧 Jinja Functions Reference

### ml_predict()
Generate SQL for row-level predictions

```sql
{{ ml_predict(model_name, feature_columns, version=None, return_proba=False) }}
```

### ml_batch_predict()
Generate SQL for batch predictions

```sql
{{ ml_batch_predict(model_name, table_name, feature_columns, id_column='id') }}
```

### ml_feature_importance()
Show feature importance as SQL comment

```sql
{{ ml_feature_importance(model_name, version=None, limit=10) }}
```

### ml_models_list()
List available models as SQL comment

```sql
{{ ml_models_list() }}
```

## 📊 Supported Model Types

### Classification
- Binary classification (churn, fraud, etc.)
- Multi-class classification
- Returns classes or probabilities

### Regression
- Continuous value prediction (LTV, sales, etc.)
- Returns numeric predictions

### Clustering
- Customer segmentation
- Anomaly detection
- Returns cluster labels

## 🎓 Best Practices

1. **Version Models**: Always version your models with meaningful names
2. **Track Metrics**: Log training metrics for comparison
3. **Feature Engineering**: Use consistent feature engineering in training and inference
4. **Model Monitoring**: Track prediction distributions and performance
5. **Retraining**: Set up regular retraining schedules for production models

## 🔜 Roadmap

- [ ] PostgreSQL UDF for in-database predictions
- [ ] API endpoints for model serving
- [ ] Model monitoring dashboard
- [ ] A/B testing framework
- [ ] AutoML capabilities
- [ ] Feature store integration

## 📖 Additional Resources

- [BaseTrainer API Documentation](training/base_trainer.py)
- [Model Registry API](registry/model_registry.py)
- [Inference API](inference/predictor.py)
- [Example Models](training/)

---

**Need Help?** Check the examples or create an issue on GitHub.
