import streamlit as st
import pandas as pd
from data_loader import load_data, apply_filters

st.set_page_config(page_title="Costco Spend Tracker - Product Catalog", page_icon="📋", layout="wide")

receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

f_receipts, f_warehouse, f_gas, _, _ = apply_filters(receipts_df, warehouse_df, gas_df)

st.header("Product Catalog")

if not f_warehouse.empty:
    # Calculate effective price for all items first
    f_warehouse_calc = f_warehouse.copy()
    # Prevent division by zero by falling back to the adjusted_amount if quantity is 0
    f_warehouse_calc['effective_price'] = f_warehouse_calc.apply(
        lambda row: row['adjusted_amount'] / row['quantity'] if row['quantity'] > 0 else row['adjusted_amount'], 
        axis=1
    )
    
    # Group by item_number to aggregate stats
    # We dropna=False so we don't accidentally drop items that have a NULL item_identifier
    catalog_df = f_warehouse_calc.groupby(
        ['item_number', 'item_name', 'friendly_name', 'item_details', 'category', 'item_identifier'], 
        dropna=False
    ).agg(
        times_bought=('transaction_barcode', 'count'),
        total_qty=('quantity', 'sum'),
        total_spend=('true_total', 'sum'),
        min_price=('effective_price', 'min'),
        max_price=('effective_price', 'max'),
        first_bought=('date', 'min'),
        last_bought=('date', 'max')
    ).reset_index()
    
    st.write(f"A complete history of all **{len(catalog_df)}** unique items you've purchased.")
    
    # We need to get the "Last Price" by sorting the original dataframe by date, then grouping and taking the last row
    last_prices = f_warehouse_calc.sort_values('date').groupby('item_number')['effective_price'].last().reset_index()
    last_prices.rename(columns={'effective_price': 'last_price'}, inplace=True)
    
    # Merge the last price back into the catalog
    catalog_df = pd.merge(catalog_df, last_prices, on='item_number', how='left')
    
    # Map the item_identifier to human readable tags
    def map_eligibility(identifier):
        if identifier == 'F':
            return 'FSA/HSA'
        elif identifier == 'E':
            return 'EBT'
        return ''
        
    catalog_df['eligibility'] = catalog_df['item_identifier'].apply(map_eligibility)
    
    # Reorder and format columns for display
    display_catalog = catalog_df[[
        'item_name', 'friendly_name', 'item_details', 'category', 'eligibility', 
        'times_bought', 'total_spend', 
        'min_price', 'max_price', 'last_price', 
        'first_bought', 'last_bought'
    ]].copy()
    
    # Sort by most frequently bought
    display_catalog = display_catalog.sort_values('times_bought', ascending=False)
    
    # Format currency columns
    for col in ['total_spend', 'min_price', 'max_price', 'last_price']:
        display_catalog[col] = display_catalog[col].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "")
        
    # Rename columns for the UI
    display_catalog.columns = [
        'Receipt Name', 'Friendly Name', 'Details', 'Category', 'Eligibility', 
        'Times Bought', 'Total Spend', 
        'Lowest Price', 'Highest Price', 'Last Price', 
        'First Bought', 'Last Bought'
    ]
    
    # Add a search box to filter the dataframe
    search_term = st.text_input("🔍 Search for an item:", "")
    if search_term:
        mask = display_catalog['Receipt Name'].str.contains(search_term, case=False, na=False) | \
               display_catalog['Friendly Name'].str.contains(search_term, case=False, na=False) | \
               display_catalog['Details'].str.contains(search_term, case=False, na=False) | \
               display_catalog['Category'].str.contains(search_term, case=False, na=False)
        display_catalog = display_catalog[mask]
        st.caption(f"Showing {len(display_catalog)} matching items.")
        
    st.dataframe(display_catalog, hide_index=True, use_container_width=True, height=600)
else:
    st.info("No warehouse items found.")