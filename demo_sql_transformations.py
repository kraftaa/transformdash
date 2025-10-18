"""
SQL Transformation Demo
Shows how to use SQL queries in the transformation pipeline (like dbt)
"""

from transformations import TransformationModel, ModelType
from orchestration import TransformationEngine

# ============================================================================
# SQL TRANSFORMATIONS - DBT-style SQL models
# ============================================================================

# Bronze layer - Direct SQL extraction
bronze_beacons_sql = """
SELECT
    id,
    created_at,
    updated_at,
    user_id,
    organization_id,
    beacon_type,
    message,
    severity,
    acknowledged
FROM beacons
LIMIT 100
"""

# Silver layer - Aggregation with SQL
silver_beacon_summary_sql = """
SELECT
    beacon_type,
    severity,
    COUNT(*) as beacon_count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT organization_id) as unique_orgs,
    SUM(CASE WHEN acknowledged THEN 1 ELSE 0 END) as acknowledged_count,
    MIN(created_at) as first_beacon,
    MAX(created_at) as last_beacon
FROM beacons
GROUP BY beacon_type, severity
ORDER BY beacon_count DESC
"""

# Gold layer - Business metrics with window functions
gold_beacon_trends_sql = """
SELECT
    DATE(created_at) as date,
    beacon_type,
    COUNT(*) as daily_count,
    SUM(COUNT(*)) OVER (PARTITION BY beacon_type ORDER BY DATE(created_at)) as cumulative_count,
    AVG(COUNT(*)) OVER (PARTITION BY beacon_type ORDER BY DATE(created_at) ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as rolling_7day_avg
FROM beacons
GROUP BY DATE(created_at), beacon_type
ORDER BY date DESC, beacon_type
LIMIT 50
"""


def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         TransformDash - SQL Transformations Demo          ║")
    print("║         DBT-Style SQL Models with Real Database           ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("\n")

    # Define SQL transformation models
    models = [
        # Bronze: Raw data extraction
        TransformationModel(
            name="bronze_beacons",
            model_type=ModelType.SQL,
            sql_query=bronze_beacons_sql,
            depends_on=[]
        ),

        # Silver: Aggregated summary
        TransformationModel(
            name="silver_beacon_summary",
            model_type=ModelType.SQL,
            sql_query=silver_beacon_summary_sql,
            depends_on=[]
        ),

        # Gold: Trends with window functions
        TransformationModel(
            name="gold_beacon_trends",
            model_type=ModelType.SQL,
            sql_query=gold_beacon_trends_sql,
            depends_on=[]
        )
    ]

    # Create engine and execute
    engine = TransformationEngine(models)
    context = engine.run(verbose=True)

    # Display results
    print("\n" + "=" * 60)
    print("📊 SQL TRANSFORMATION RESULTS")
    print("=" * 60)

    print("\n📋 Bronze Layer - Raw Beacons:")
    bronze = context.results['bronze_beacons']
    print(f"Total beacons extracted: {len(bronze)}")
    if len(bronze) > 0:
        print(bronze.head(5).to_string(index=False))

    print("\n\n📊 Silver Layer - Beacon Summary by Type & Severity:")
    silver = context.results['silver_beacon_summary']
    if len(silver) > 0:
        print(silver.to_string(index=False))

    print("\n\n📈 Gold Layer - Beacon Trends (7-day rolling average):")
    gold = context.results['gold_beacon_trends']
    if len(gold) > 0:
        print(gold.head(10).to_string(index=False))

    print("\n" + "=" * 60)
    print("✅ SQL Transformations Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
