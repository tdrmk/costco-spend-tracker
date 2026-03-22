import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

# --- Shared Data Loading ---
DB_PATH = Path("costco_spend.db")

@st.cache_data
def load_data():
    if not DB_PATH.exists():
        return None, None, None
        
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Load Receipts
    receipts_df = pd.read_sql("""
        SELECT r.*, w.warehouse_name 
        FROM receipts r
        JOIN warehouses w ON r.warehouse_number = w.warehouse_number
    """, conn)
    receipts_df['transaction_datetime'] = pd.to_datetime(receipts_df['transaction_datetime'])
    receipts_df['date'] = receipts_df['transaction_datetime'].dt.date
    receipts_df['year_month'] = receipts_df['transaction_datetime'].dt.to_period('M').astype(str)
    
    # 2. Load Warehouse Purchases
    warehouse_df = pd.read_sql("""
        SELECT wp.*, p.item_name, p.item_details, p.friendly_name, p.department_number, p.item_identifier, p.is_taxed,
               r.transaction_datetime, r.user_name, w.warehouse_name
        FROM warehouse_purchases wp
        JOIN products p ON wp.item_number = p.item_number
        JOIN receipts r ON wp.transaction_barcode = r.transaction_barcode
        JOIN warehouses w ON r.warehouse_number = w.warehouse_number
    """, conn)
    warehouse_df['transaction_datetime'] = pd.to_datetime(warehouse_df['transaction_datetime'])
    warehouse_df['date'] = warehouse_df['transaction_datetime'].dt.date
    
    # Map department numbers to human-readable categories
    dept_mapping = {
        53: "Gas Station", 17: "Dairy & Refrigerated", 65: "Fresh Produce",
        19: "Refrigerated Deli", 18: "Frozen Foods", 61: "Meat & Seafood",
        63: "Deli / Prepared Foods", 14: "Household & Cleaning", 23: "Home & Storage",
        13: "Pantry / Dry Goods", 20: "Personal Care & Wellness", 93: "Pharmacy / Vitamins",
        34: "Home & Bath", 32: "Kitchen & Home", 26: "Clothing & Shoes",
        31: "Clothing & Shoes", 39: "Clothing & Shoes", 11: "Snacks & Candy",
        12: "Snacks & Candy", 88: "Food Court", 28: "Toys & Games",
        27: "Garden & Patio", 75: "Automotive / Tolls", 87: "Tire Center",
        0: "Fees & Deposits"
    }
    warehouse_df['category'] = warehouse_df['department_number'].map(dept_mapping).fillna("Other / Unknown")
    
    # 3. Load Gas Purchases
    gas_df = pd.read_sql("""
        SELECT gp.*, 
               r.transaction_datetime, r.user_name, w.warehouse_name
        FROM gas_purchases gp
        JOIN receipts r ON gp.transaction_barcode = r.transaction_barcode
        JOIN warehouses w ON r.warehouse_number = w.warehouse_number
    """, conn)
    gas_df['transaction_datetime'] = pd.to_datetime(gas_df['transaction_datetime'])
    gas_df['date'] = gas_df['transaction_datetime'].dt.date
    
    conn.close()
    return receipts_df, warehouse_df, gas_df

def apply_filters(receipts_df, warehouse_df, gas_df):
    """Applies sidebar filters and returns filtered dataframes plus the selected date range (inclusive)."""
    st.sidebar.title("🛒 Costco Tracker")
    
    min_date = receipts_df['date'].min()
    max_date = receipts_df['date'].max()
    
    date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = date_range[0], date_range[0]
        
    users = ["All"] + list(receipts_df['user_name'].unique())
    selected_user = st.sidebar.selectbox("User", users)
    
    # Apply Filters
    r_mask = (receipts_df['date'] >= start_date) & (receipts_df['date'] <= end_date)
    w_mask = (warehouse_df['date'] >= start_date) & (warehouse_df['date'] <= end_date)
    g_mask = (gas_df['date'] >= start_date) & (gas_df['date'] <= end_date)
    
    if selected_user != "All":
        r_mask &= (receipts_df['user_name'] == selected_user)
        w_mask &= (warehouse_df['user_name'] == selected_user)
        g_mask &= (gas_df['user_name'] == selected_user)

    return (
        receipts_df[r_mask],
        warehouse_df[w_mask],
        gas_df[g_mask],
        start_date,
        end_date,
    )