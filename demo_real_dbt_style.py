"""
Real DBT-Style Transformation Pipeline
Uses actual sci_rx_production data with Bronze → Silver → Gold layers
Mimics patterns from sparkle-dbt project
"""

import pandas as pd
from transformations import TransformationModel, ModelType
from orchestration import TransformationEngine
from postgres import PostgresConnector

# ============================================================================
# BRONZE LAYER - Extract raw data from source tables
# ============================================================================

def bronze_proposals(context):
    """
    Bronze layer: proposals table
    Pattern: Direct extraction with filtering (like sparkle-dbt bronze_proposals)
    """
    with PostgresConnector() as pg:
        query = """
        SELECT *
        FROM proposals
        WHERE exclude_from_reporting <> TRUE
        LIMIT 100
        """
        df = pg.query_to_dataframe(query)
        print(f"    Extracted {len(df)} proposals from source")
        return df


def bronze_currencies(context):
    """
    Bronze layer: currencies table
    Pattern: Direct extraction for currency conversions
    """
    with PostgresConnector() as pg:
        query = """
        SELECT *
        FROM currencies
        WHERE exchangable_type = 'Pg::Proposal'
        LIMIT 100
        """
        df = pg.query_to_dataframe(query)
        print(f"    Extracted {len(df)} currency records")
        return df


def bronze_providers(context):
    """
    Bronze layer: providers table
    Pattern: Direct extraction of supplier data
    """
    with PostgresConnector() as pg:
        query = """
        SELECT *
        FROM providers
        LIMIT 100
        """
        df = pg.query_to_dataframe(query)
        print(f"    Extracted {len(df)} providers")
        return df


def bronze_users(context):
    """
    Bronze layer: users table
    Pattern: Direct extraction with computed full_name (like sparkle-dbt)
    """
    with PostgresConnector() as pg:
        query = """
        SELECT
            id,
            email,
            first_name,
            last_name,
            first_name || ' ' || last_name AS full_name,
            activated_at,
            created_at,
            updated_at
        FROM users
        LIMIT 100
        """
        df = pg.query_to_dataframe(query)
        print(f"    Extracted {len(df)} users")
        return df


# ============================================================================
# SILVER LAYER - Cleansed, joined, and enriched data
# ============================================================================

def silver_proposals(context):
    """
    Silver layer: enriched proposals with joins
    Pattern: Multi-table joins with currency conversion (like sparkle-dbt silver_proposals)
    """
    proposals = context['bronze_proposals']
    currencies = context['bronze_currencies']
    providers = context['bronze_providers']
    users = context['bronze_users']

    # Join proposals with currencies
    merged = proposals.merge(
        currencies[['exchangable_id', 'conversion_rate']],
        left_on='id',
        right_on='exchangable_id',
        how='left'
    )

    # Join with providers
    merged = merged.merge(
        providers[['id', 'name']].rename(columns={'id': 'provider_id', 'name': 'provider_name'}),
        left_on='provider_pg_id',
        right_on='provider_id',
        how='left'
    )

    # Join with users
    merged = merged.merge(
        users[['id', 'email', 'full_name']].rename(columns={
            'id': 'user_id_ref',
            'email': 'user_email',
            'full_name': 'user_full_name'
        }),
        left_on='user_id',
        right_on='user_id_ref',
        how='left'
    )

    # Currency conversions to USD (sparkle-dbt pattern)
    if 'retail_total_price' in merged.columns and 'conversion_rate' in merged.columns:
        merged['retail_total_price_usd'] = merged['retail_total_price'] / merged['conversion_rate']
        merged['wholesale_total_price_usd'] = merged['wholesale_total_price'] / merged['conversion_rate']

    # Add ranking (sparkle-dbt window function pattern)
    if 'confirmed_at' in merged.columns:
        merged['proposal_rank'] = merged.groupby('quoted_ware_pg_id')['confirmed_at'].rank(method='first')
        merged['is_first_proposal'] = merged['proposal_rank'] == 1

    print(f"    Created silver_proposals with {len(merged)} enriched records")
    print(f"    Added columns: retail_total_price_usd, wholesale_total_price_usd, proposal_rank")

    return merged


# ============================================================================
# GOLD LAYER - Business-ready aggregations and reports
# ============================================================================

def gold_proposal_summary(context):
    """
    Gold layer: Aggregated proposal metrics by provider
    Pattern: Daily/provider aggregation (like sparkle-dbt gold_revenue_daily)
    """
    silver = context['silver_proposals']

    # Aggregate by provider
    summary = silver.groupby(['provider_name', 'proposal_type']).agg({
        'id': 'count',
        'retail_total_price_usd': ['sum', 'mean', 'max'],
        'wholesale_total_price_usd': ['sum', 'mean', 'max']
    }).reset_index()

    # Flatten column names
    summary.columns = [
        'provider_name', 'proposal_type',
        'proposal_count',
        'retail_total_usd', 'retail_avg_usd', 'retail_max_usd',
        'wholesale_total_usd', 'wholesale_avg_usd', 'wholesale_max_usd'
    ]

    # Sort by total value
    summary = summary.sort_values('retail_total_usd', ascending=False)

    print(f"    Created gold summary with {len(summary)} provider aggregations")
    return summary


def gold_insights(context):
    """
    Gold layer: Business insights and KPIs
    Pattern: High-level metrics for dashboards
    """
    silver = context['silver_proposals']
    gold_summary = context['gold_proposal_summary']

    insights = {
        'total_proposals': len(silver),
        'total_providers': silver['provider_name'].nunique(),
        'total_users': silver['user_email'].nunique(),
        'total_value_usd': silver['retail_total_price_usd'].sum() if 'retail_total_price_usd' in silver.columns else 0,
        'avg_proposal_value_usd': silver['retail_total_price_usd'].mean() if 'retail_total_price_usd' in silver.columns else 0,
        'top_provider': gold_summary.iloc[0]['provider_name'] if len(gold_summary) > 0 else 'N/A',
        'top_provider_value': gold_summary.iloc[0]['retail_total_usd'] if len(gold_summary) > 0 else 0,
        'proposal_types': silver['proposal_type'].value_counts().to_dict() if 'proposal_type' in silver.columns else {}
    }

    print(f"    Generated {len(insights)} business insights")
    return insights


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║      TransformDash - Real DBT-Style Pipeline              ║")
    print("║      Bronze → Silver → Gold with sci_rx_production        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("\n")

    # Define transformation models following DBT medallion architecture
    models = [
        # ===== BRONZE LAYER (Raw Data Extraction) =====
        TransformationModel(
            name="bronze_proposals",
            model_type=ModelType.PYTHON,
            python_func=bronze_proposals,
            depends_on=[]
        ),
        TransformationModel(
            name="bronze_currencies",
            model_type=ModelType.PYTHON,
            python_func=bronze_currencies,
            depends_on=[]
        ),
        TransformationModel(
            name="bronze_providers",
            model_type=ModelType.PYTHON,
            python_func=bronze_providers,
            depends_on=[]
        ),
        TransformationModel(
            name="bronze_users",
            model_type=ModelType.PYTHON,
            python_func=bronze_users,
            depends_on=[]
        ),

        # ===== SILVER LAYER (Cleansed & Enriched) =====
        TransformationModel(
            name="silver_proposals",
            model_type=ModelType.PYTHON,
            python_func=silver_proposals,
            depends_on=["bronze_proposals", "bronze_currencies", "bronze_providers", "bronze_users"]
        ),

        # ===== GOLD LAYER (Business Reports) =====
        TransformationModel(
            name="gold_proposal_summary",
            model_type=ModelType.PYTHON,
            python_func=gold_proposal_summary,
            depends_on=["silver_proposals"]
        ),
        TransformationModel(
            name="gold_insights",
            model_type=ModelType.PYTHON,
            python_func=gold_insights,
            depends_on=["silver_proposals", "gold_proposal_summary"]
        )
    ]

    # Create engine and execute DAG
    engine = TransformationEngine(models)
    context = engine.run(verbose=True)

    # Display final results
    print("\n" + "=" * 60)
    print("📊 GOLD LAYER RESULTS")
    print("=" * 60)

    print("\n📈 Top Providers by Total Value:")
    gold_summary = context.results['gold_proposal_summary']
    print(gold_summary.head(10).to_string(index=False))

    print("\n\n💡 Business Insights:")
    insights = context.results['gold_insights']
    for key, value in insights.items():
        if isinstance(value, float):
            if 'value' in key or 'usd' in key:
                print(f"  • {key.replace('_', ' ').title()}: ${value:,.2f}")
            else:
                print(f"  • {key.replace('_', ' ').title()}: {value:.2f}")
        elif isinstance(value, dict):
            print(f"  • {key.replace('_', ' ').title()}:")
            for k, v in value.items():
                print(f"      - {k}: {v}")
        else:
            print(f"  • {key.replace('_', ' ').title()}: {value}")

    print("\n" + "=" * 60)
    print("✅ Real DBT-Style Pipeline Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
