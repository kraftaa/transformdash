"""
Silver Layer Python Model - Product Enrichment
Adds calculated fields and data cleaning to products
"""

def config():
    return {'materialized': 'table'}

def model(dbt):
    """
    Enriches product data with calculated fields

    Args:
        dbt: DBT context with ref() and source() functions

    Returns:
        pd.DataFrame: Enriched product data
    """
    # Reference the bronze layer products model
    products_df = dbt.ref('stg_products')

    # Add calculated fields
    # Price category based on unit price
    def categorize_price(price):
        if pd.isna(price) or price == 0:
            return 'Unknown'
        elif price < 10:
            return 'Budget'
        elif price < 50:
            return 'Mid-Range'
        elif price < 200:
            return 'Premium'
        else:
            return 'Luxury'

    products_df['price_category'] = products_df['price'].apply(categorize_price)

    # Calculate profit margin if cost is available
    if 'cost' in products_df.columns:
        products_df['profit_margin'] = (
            (products_df['price'] - products_df['cost']) /
            products_df['price'] * 100
        ).round(2)

    # Clean product names - remove extra whitespace, title case
    if 'product_name' in products_df.columns:
        products_df['product_name_clean'] = (
            products_df['product_name']
            .str.strip()
            .str.title()
        )

    # Flag discontinued products
    if 'discontinued' in products_df.columns:
        products_df['is_active'] = ~products_df['discontinued'].fillna(False)

    return products_df
