import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data, apply_filters

st.set_page_config(page_title="Costco Spend Tracker - Overview", page_icon="📊", layout="wide")

receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

f_receipts, f_warehouse, f_gas, _, _ = apply_filters(receipts_df, warehouse_df, gas_df)

st.header("Overview")

# Separate warehouse and gas receipts for better stats
warehouse_receipts = f_receipts[f_receipts['receipt_type'] == 'IN-WAREHOUSE']
gas_receipts = f_receipts[f_receipts['receipt_type'] == 'GAS STATION']

col1, col2, col3, col4 = st.columns(4)

total_spend = f_receipts['total'].sum()
total_trips = len(f_receipts)
total_gas = gas_receipts['total'].sum()

col1.metric("Total Spend", f"${total_spend:,.2f}")
col2.metric("Total Trips", total_trips)
col3.metric("Gas Spend", f"${total_gas:,.2f}")

st.subheader("Warehouse Spend Stats")
w_col1, w_col2, w_col3, w_col4 = st.columns(4)

if not warehouse_receipts.empty:
    total_warehouse_spend = warehouse_receipts['total'].sum()
    avg_warehouse_trip = warehouse_receipts['total'].mean()
    median_warehouse_trip = warehouse_receipts['total'].median()
    max_warehouse_trip = warehouse_receipts['total'].max()
    
    w_col1.metric("Total Warehouse Spend", f"${total_warehouse_spend:,.2f}")
    w_col2.metric("Average Trip", f"${avg_warehouse_trip:,.2f}")
    w_col3.metric("Median Trip", f"${median_warehouse_trip:,.2f}")
    w_col4.metric("Highest Trip", f"${max_warehouse_trip:,.2f}")
else:
    st.info("No warehouse trips found in this date range.")

st.markdown("---")

st.subheader("Spend by Month")
monthly_spend = f_receipts.groupby(['year_month', 'receipt_type'])['total'].sum().reset_index()
fig_spend = px.bar(monthly_spend, x='year_month', y='total', color='receipt_type', 
             title="Monthly Spend (Warehouse vs Gas)",
             labels={'total': 'Spend ($)', 'year_month': 'Month', 'receipt_type': 'Type'})
fig_spend.update_yaxes(tickformat="$.2f")
st.plotly_chart(fig_spend, use_container_width=True)

st.subheader("Trips by Month")
monthly_trips = f_receipts.groupby(['year_month', 'receipt_type']).size().reset_index(name='trip_count')
fig_trips = px.bar(monthly_trips, x='year_month', y='trip_count', color='receipt_type', 
             title="Number of Trips (Warehouse vs Gas)",
             labels={'trip_count': 'Number of Trips', 'year_month': 'Month', 'receipt_type': 'Type'})
st.plotly_chart(fig_trips, use_container_width=True)

st.markdown("---")
st.subheader("Warehouse Spend by Category")

if not f_warehouse.empty:
    # 1. Overall Category Donut Chart
    cat_spend_overall = f_warehouse.groupby('category')['true_total'].sum().reset_index()
    # Sort by spend descending to determine the order
    cat_spend_overall = cat_spend_overall.sort_values('true_total', ascending=False)
    
    # Extract the sorted categories to enforce consistent ordering and coloring
    category_order = cat_spend_overall['category'].tolist()
    
    fig_cat_overall = px.pie(cat_spend_overall, values='true_total', names='category', hole=0.4,
                             title="Total Warehouse Spend Breakdown",
                             category_orders={"category": category_order})
    fig_cat_overall.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_cat_overall, use_container_width=True)
    
    # 2. Monthly Category Breakdown (Stacked Bar Chart with Filter)
    st.subheader("Monthly Category Trend")
    
    # Add a multiselect filter specifically for this chart
    all_categories = sorted(f_warehouse['category'].unique())
    selected_trend_cats = st.multiselect(
        "Filter Categories for Trend Chart:", 
        options=all_categories, 
        default=all_categories,
        help="Remove categories (like Electronics or Furniture) to see your core grocery trends more clearly."
    )
    
    if selected_trend_cats:
        # Filter the dataframe based on the multi-select
        trend_df = f_warehouse[f_warehouse['category'].isin(selected_trend_cats)].copy()
        
        # We need year_month in the warehouse_df for this grouping
        trend_df['year_month'] = pd.to_datetime(trend_df['date']).dt.to_period('M').astype(str)
        
        # Group and sum
        monthly_cat_spend = trend_df.groupby(['year_month', 'category'])['true_total'].sum().reset_index()
        
        # Create the stacked bar figure
        fig_monthly_cat = px.bar(
            monthly_cat_spend, 
            x='year_month', 
            y='true_total', 
            color='category',
            title="Warehouse Spend by Category over Time",
            labels={'true_total': 'Spend ($)', 'year_month': 'Month', 'category': 'Category'},
            category_orders={"category": category_order}
        )
        
        # Force the layout to stack the bars
        fig_monthly_cat.update_layout(barmode='stack')
        fig_monthly_cat.update_yaxes(tickformat="$.2f")
        
        st.plotly_chart(fig_monthly_cat, use_container_width=True)
    else:
        st.warning("Please select at least one category to view the trend.")
    
else:
    st.info("No warehouse items found in this date range to categorize.")