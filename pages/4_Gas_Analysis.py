import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data, apply_filters

st.set_page_config(page_title="Costco Spend Tracker - Gas Analysis", page_icon="⛽", layout="wide")

receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

f_receipts, f_warehouse, f_gas = apply_filters(receipts_df, warehouse_df, gas_df)

st.header("Gas Analysis")

if f_gas.empty:
    st.info("No gas purchases found in this date range.")
else:
    # Sort chronologically for time-based calculations
    gas_data = f_gas.sort_values('transaction_datetime')
    
    # Calculate KPIs
    total_gallons = gas_data['quantity_gallons'].sum()
    avg_price = gas_data['unit_price'].mean()
    avg_gallons_per_trip = gas_data['quantity_gallons'].mean()
    
    # Calculate days between fill-ups (overall, regardless of user)
    gas_data['prev_date'] = gas_data['transaction_datetime'].shift(1)
    gas_data['days_since_last'] = (gas_data['transaction_datetime'] - gas_data['prev_date']).dt.days
    avg_days_between = gas_data['days_since_last'].mean()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Gallons", f"{total_gallons:,.1f} gal")
    col2.metric("Avg Price / Gal", f"${avg_price:,.2f}")
    col3.metric("Avg Fill-up", f"{avg_gallons_per_trip:,.1f} gal")
    
    if pd.notna(avg_days_between):
        col4.metric("Avg Days Between Fill-ups", f"{avg_days_between:.1f} days")
    else:
        col4.metric("Avg Days Between Fill-ups", "N/A")
        
    st.markdown("---")
    
    # Price Trend Chart
    st.subheader("Price per Gallon Trend")
    fig_price = px.line(gas_data, x='date', y='unit_price', markers=True,
                        title="Costco Gas Price Fluctuations",
                        labels={'unit_price': 'Price per Gallon ($)', 'date': 'Date'})
    fig_price.update_yaxes(tickformat="$.2f")
    st.plotly_chart(fig_price, use_container_width=True)
    
    # Volume per Trip Chart
    st.subheader("Volume Purchased per Trip")
    fig_vol_trip = px.bar(gas_data, x='date', y='quantity_gallons',
                          title="Gallons Pumped per Trip",
                          labels={'quantity_gallons': 'Gallons', 'date': 'Date'})
    st.plotly_chart(fig_vol_trip, use_container_width=True)
    
    # Monthly Spend & Volume Charts (Side by Side)
    st.subheader("Monthly Gas Usage")
    
    gas_data['year_month'] = gas_data['transaction_datetime'].dt.to_period('M').astype(str)
    monthly_gas = gas_data.groupby('year_month').agg(
        total_spend=('amount', 'sum'),
        total_gallons=('quantity_gallons', 'sum')
    ).reset_index()
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_spend = px.bar(monthly_gas, x='year_month', y='total_spend',
                         title="Total Gas Spend per Month",
                         labels={'total_spend': 'Spend ($)', 'year_month': 'Month'})
        fig_spend.update_yaxes(tickformat="$.2f")
        st.plotly_chart(fig_spend, use_container_width=True)
        
    with col_chart2:
        fig_vol = px.bar(monthly_gas, x='year_month', y='total_gallons',
                         title="Total Gallons Pumped per Month",
                         labels={'total_gallons': 'Gallons', 'year_month': 'Month'})
        st.plotly_chart(fig_vol, use_container_width=True)
    
    # Fun Estimate
    st.markdown("---")
    st.subheader("🚗 Mileage Estimator")
    mpg = st.slider("What is your car's average MPG?", min_value=10, max_value=60, value=25)
    
    estimated_miles = total_gallons * mpg
    total_gas_cost = gas_data['amount'].sum()
    cost_per_mile = total_gas_cost / estimated_miles if estimated_miles > 0 else 0
    cost_per_100_miles = cost_per_mile * 100
    
    st.info(f"Based on **{total_gallons:,.1f}** gallons purchased and **{mpg}** MPG:")
    
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("Estimated Miles Driven", f"{estimated_miles:,.0f} mi")
    m_col2.metric("Cost per Mile", f"${cost_per_mile:.2f}")
    m_col3.metric("Cost per 100 Miles", f"${cost_per_100_miles:.2f}")