"""
ML Training Script - Customer Segmentation
Trains a KMeans clustering model to segment customers based on behavior
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime
from postgres import PostgresConnector


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare features for customer segmentation"""
    # Calculate RFM metrics (Recency, Frequency, Monetary)
    features_df = df.groupby('customer_id').agg({
        'order_id': 'count',  # Frequency
        'total_amount': ['sum', 'mean'],  # Monetary
        'order_date': 'max'  # For Recency
    }).reset_index()

    features_df.columns = ['customer_id', 'order_count', 'total_spent', 'avg_order_value', 'last_order_date']

    # Calculate recency (days since last order)
    features_df['recency_days'] = (pd.Timestamp.now() - pd.to_datetime(features_df['last_order_date'])).dt.days

    # Select features for clustering
    feature_cols = ['order_count', 'total_spent', 'avg_order_value', 'recency_days']
    X = features_df[feature_cols]

    return X, features_df['customer_id']


def train_customer_segmentation():
    """Train customer segmentation model"""
    print("\n" + "="*60)
    print("TRAINING CUSTOMER SEGMENTATION MODEL")
    print("="*60 + "\n")

    # Load data from database
    print("Loading customer order data from database...")
    with PostgresConnector() as pg:
        query = """
        SELECT
            customer_id,
            order_id,
            total_amount,
            order_date
        FROM public.fct_orders
        """
        df = pg.query_to_dataframe(query)

    print(f"Loaded {len(df)} orders from {df['customer_id'].nunique()} customers")

    # Prepare features
    print("\nPreparing features...")
    X, customer_ids = prepare_features(df)
    print(f"Feature matrix shape: {X.shape}")
    print(f"Features: {list(X.columns)}")

    # Scale features
    print("\nScaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train KMeans
    print("\nTraining KMeans clustering model...")
    n_clusters = 4
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(X_scaled)

    # Get predictions
    segments = kmeans.predict(X_scaled)

    # Analyze segments
    print(f"\nModel trained with {n_clusters} customer segments")
    print("\nSegment Analysis:")

    X_with_segments = X.copy()
    X_with_segments['segment'] = segments
    X_with_segments['customer_id'] = customer_ids.values

    for segment_id in range(n_clusters):
        segment_data = X_with_segments[X_with_segments['segment'] == segment_id]
        print(f"\n  Segment {segment_id}: {len(segment_data)} customers")
        print(f"    Avg Orders: {segment_data['order_count'].mean():.1f}")
        print(f"    Avg Total Spent: ${segment_data['total_spent'].mean():,.2f}")
        print(f"    Avg Order Value: ${segment_data['avg_order_value'].mean():.2f}")
        print(f"    Avg Recency: {segment_data['recency_days'].mean():.1f} days")

    # Save model and scaler
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = models_dir / f"customer_segmentation_{timestamp}.pkl"
    scaler_path = models_dir / f"customer_segmentation_scaler_{timestamp}.pkl"

    joblib.dump(kmeans, model_path)
    joblib.dump(scaler, scaler_path)

    # Also save as "latest"
    latest_model_path = models_dir / "customer_segmentation_latest.pkl"
    latest_scaler_path = models_dir / "customer_segmentation_scaler_latest.pkl"
    joblib.dump(kmeans, latest_model_path)
    joblib.dump(scaler, latest_scaler_path)

    print(f"\n\nModel saved to:")
    print(f"  {model_path}")
    print(f"  {latest_model_path}")

    # Save results to database
    print("\nSaving customer segments to database...")
    X_with_segments_df = X_with_segments[['customer_id', 'segment']]

    with PostgresConnector() as pg:
        # Drop and recreate table
        pg.execute("DROP TABLE IF EXISTS public.customer_segments")
        pg.execute("""
            CREATE TABLE public.customer_segments (
                customer_id INTEGER PRIMARY KEY,
                segment INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert data
        from sqlalchemy import create_engine
        import os

        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "transformdash")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")

        engine = create_engine(f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")
        X_with_segments_df.to_sql(
            name='customer_segments',
            con=engine,
            schema='public',
            if_exists='replace',
            index=False
        )
        engine.dispose()

    print(f"Saved {len(X_with_segments_df)} customer segments to database")
    print("\n✅ Training completed successfully!")

    return kmeans, scaler, X_with_segments


if __name__ == "__main__":
    try:
        kmeans, scaler, results = train_customer_segmentation()
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
