"""
TransformDash MVP Demo
Shows end-to-end data transformation pipeline with DAG execution
"""

import pandas as pd
from transformations import TransformationModel, ModelType
from orchestration import TransformationEngine

# Sample transformation functions
def extract_users(context):
    """Extract raw user data from source"""
    users = pd.DataFrame({
        'user_id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'age': [25, 30, 35, 28, 42],
        'country': ['USA', 'UK', 'USA', 'Canada', 'UK']
    })
    print(f"    Extracted {len(users)} users")
    return users

def extract_orders(context):
    """Extract raw order data from source"""
    orders = pd.DataFrame({
        'order_id': [101, 102, 103, 104, 105, 106],
        'user_id': [1, 2, 1, 3, 2, 4],
        'amount': [100, 250, 75, 300, 150, 200],
        'status': ['completed', 'completed', 'pending', 'completed', 'cancelled', 'completed']
    })
    print(f"    Extracted {len(orders)} orders")
    return orders

def clean_users(context):
    """Clean and standardize user data"""
    users = context['raw_users']

    # Add some cleaning logic
    users['name'] = users['name'].str.upper()
    users['age_group'] = pd.cut(users['age'], bins=[0, 30, 40, 100], labels=['Young', 'Middle', 'Senior'])

    print(f"    Cleaned {len(users)} users, added age_group column")
    return users

def aggregate_orders(context):
    """Aggregate orders by user"""
    orders = context['raw_orders']

    # Filter completed orders only
    completed_orders = orders[orders['status'] == 'completed']

    # Aggregate by user
    user_orders = completed_orders.groupby('user_id').agg({
        'order_id': 'count',
        'amount': 'sum'
    }).reset_index()
    user_orders.columns = ['user_id', 'order_count', 'total_spent']

    print(f"    Aggregated orders for {len(user_orders)} users")
    return user_orders

def create_user_summary(context):
    """Create final user summary by joining cleaned users with aggregated orders"""
    users = context['cleaned_users']
    orders = context['aggregated_orders']

    # Join users with their order summary
    summary = users.merge(orders, on='user_id', how='left')
    summary['total_spent'] = summary['total_spent'].fillna(0)
    summary['order_count'] = summary['order_count'].fillna(0)

    # Calculate average order value
    summary['avg_order_value'] = summary.apply(
        lambda row: row['total_spent'] / row['order_count'] if row['order_count'] > 0 else 0,
        axis=1
    )

    print(f"    Created summary for {len(summary)} users")
    return summary

def generate_insights(context):
    """Generate business insights from the final summary"""
    summary = context['user_summary']

    insights = {
        'total_users': len(summary),
        'total_revenue': summary['total_spent'].sum(),
        'avg_revenue_per_user': summary['total_spent'].mean(),
        'total_orders': summary['order_count'].sum(),
        'top_spender': summary.loc[summary['total_spent'].idxmax()]['name'],
        'top_spender_amount': summary['total_spent'].max(),
        'users_by_country': summary.groupby('country')['user_id'].count().to_dict(),
        'users_by_age_group': summary.groupby('age_group')['user_id'].count().to_dict()
    }

    print(f"    Generated {len(insights)} insights")
    return insights


def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           TransformDash MVP - Live Demo                   ║")
    print("║   Hybrid Data Transformation & Dashboard Platform          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("\n")

    # Define transformation models with dependencies
    models = [
        # Stage 1: Extract raw data (no dependencies)
        TransformationModel(
            name="raw_users",
            model_type=ModelType.PYTHON,
            python_func=extract_users,
            depends_on=[]
        ),
        TransformationModel(
            name="raw_orders",
            model_type=ModelType.PYTHON,
            python_func=extract_orders,
            depends_on=[]
        ),

        # Stage 2: Clean and transform (depends on raw data)
        TransformationModel(
            name="cleaned_users",
            model_type=ModelType.PYTHON,
            python_func=clean_users,
            depends_on=["raw_users"]
        ),
        TransformationModel(
            name="aggregated_orders",
            model_type=ModelType.PYTHON,
            python_func=aggregate_orders,
            depends_on=["raw_orders"]
        ),

        # Stage 3: Create summary (depends on cleaned data)
        TransformationModel(
            name="user_summary",
            model_type=ModelType.PYTHON,
            python_func=create_user_summary,
            depends_on=["cleaned_users", "aggregated_orders"]
        ),

        # Stage 4: Generate insights (depends on summary)
        TransformationModel(
            name="insights",
            model_type=ModelType.PYTHON,
            python_func=generate_insights,
            depends_on=["user_summary"]
        )
    ]

    # Create engine and execute
    engine = TransformationEngine(models)
    context = engine.run(verbose=True)

    # Display final results
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    print("\n📊 User Summary (Top 3):")
    user_summary = context.results['user_summary']
    print(user_summary.head(3).to_string(index=False))

    print("\n\n💡 Business Insights:")
    insights = context.results['insights']
    for key, value in insights.items():
        if isinstance(value, float):
            print(f"  • {key.replace('_', ' ').title()}: ${value:,.2f}" if 'revenue' in key or 'amount' in key else f"  • {key.replace('_', ' ').title()}: {value:.2f}")
        else:
            print(f"  • {key.replace('_', ' ').title()}: {value}")

    print("\n" + "=" * 60)
    print("✅ MVP Demo Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
