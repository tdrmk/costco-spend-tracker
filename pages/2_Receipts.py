import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data, apply_filters

st.set_page_config(page_title="Costco Spend Tracker - Receipts", page_icon="🧾", layout="wide")

receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

f_receipts, f_warehouse, f_gas = apply_filters(receipts_df, warehouse_df, gas_df)

st.header("Receipt Explorer")

if f_receipts.empty:
    st.info("No receipts found in this date range.")
else:
    # --- Calendar Heatmap ---
    st.subheader("Trip Calendar")
    
    # Group by date to get total spend per day
    daily_spend = f_receipts.groupby('date')['total'].sum().reset_index()
    # Ensure date is datetime for calplot
    daily_spend['date'] = pd.to_datetime(daily_spend['date'])
    
    # Fallback to a simple Plotly scatter plot that looks like a timeline
    fig_timeline = px.scatter(
        daily_spend, 
        x="date", 
        y="total", 
        size="total", 
        color="total",
        color_continuous_scale="Viridis",
        title="Costco Trips Timeline (Bubble Size = Spend)",
        labels={"date": "Date", "total": "Total Spend ($)"}
    )
    
    fig_timeline.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        ),
        height=400
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
        
    st.markdown("---")
    
    # Create a clean list of receipts for the dropdown
    receipt_options = f_receipts.sort_values('transaction_datetime', ascending=False)
    
    # Format the dropdown labels
    def format_receipt_label(row):
        date_str = row['transaction_datetime'].strftime('%b %d, %Y')
        return f"{date_str} - {row['warehouse_name']} ({row['receipt_type']}) - ${row['total']:.2f}"
        
    receipt_options['label'] = receipt_options.apply(format_receipt_label, axis=1)
    
    selected_label = st.selectbox("Select a Receipt to view:", receipt_options['label'].tolist())
    
    if selected_label:
        # Get the selected receipt row
        selected_row = receipt_options[receipt_options['label'] == selected_label].iloc[0]
        barcode = selected_row['transaction_barcode']
        is_gas = selected_row['receipt_type'] == 'GAS STATION'
        
        st.markdown("---")
        
        # --- Digital Receipt Layout ---
        st.subheader(f"🛒 Costco {selected_row['warehouse_name']}")
        st.caption(f"**Date:** {selected_row['transaction_datetime'].strftime('%B %d, %Y at %I:%M %p')} | **Member:** {selected_row['user_name'].title()} | **Card:** {selected_row['tender_type']} ending in {selected_row['account_number']} | **Barcode:** `{barcode}`")
        
        # Summary Metrics at the top
        s_col1, s_col2, s_col3 = st.columns(3)
        s_col1.metric("Subtotal", f"${selected_row['subtotal']:.2f}")
        s_col2.metric("Tax", f"${selected_row['taxes']:.2f}")
        s_col3.metric("Total", f"${selected_row['total']:.2f}")
        
        st.markdown("##### Items")
        
        if is_gas:
            # Fetch gas items for this barcode
            items = f_gas[f_gas['transaction_barcode'] == barcode]
            
            # Display as a clean dataframe
            display_df = items[['fuel_grade', 'quantity_gallons', 'unit_price', 'amount']].copy()
            display_df.columns = ['Fuel Grade', 'Gallons', 'Price/Gal', 'Total']
            
            # Format currency
            display_df['Price/Gal'] = display_df['Price/Gal'].apply(lambda x: f"${x:.3f}")
            display_df['Total'] = display_df['Total'].apply(lambda x: f"${x:.2f}")
            
            st.dataframe(display_df, hide_index=True, use_container_width=True, height=(len(display_df) + 1) * 35 + 3)
            
        else:
            # Fetch warehouse items for this barcode
            items = f_warehouse[f_warehouse['transaction_barcode'] == barcode]
            
            # Display as a clean dataframe
            display_df = items[['item_number', 'item_name', 'category', 'quantity', 'unit_price', 'discount_amount', 'fee_amount', 'adjusted_amount', 'is_taxed']].copy()
            
            # Format the dataframe for display
            display_df['unit_price'] = display_df['unit_price'].apply(lambda x: f"${x:.2f}")
            display_df['discount_amount'] = display_df['discount_amount'].apply(lambda x: f"${x:.2f}" if x < 0 else "")
            display_df['fee_amount'] = display_df['fee_amount'].apply(lambda x: f"${x:.2f}" if x > 0 else "")
            display_df['adjusted_amount'] = display_df['adjusted_amount'].apply(lambda x: f"${x:.2f}")
            
            display_df.columns = ['Item #', 'Description', 'Category', 'Qty', 'Price', 'Discount', 'Fees (CRV)', 'Taxable Amt', 'Taxed']
            st.dataframe(display_df, hide_index=True, use_container_width=True, height=(len(display_df) + 1) * 35 + 3)
        
        # Move the Category Donut Chart below the columns to give it full width
        if not is_gas:
            st.markdown("---")
            st.subheader("Spend by Category")
            # Group items by category and sum the true_total
            cat_spend = items.groupby('category')['true_total'].sum().reset_index()
            # Sort by spend descending
            cat_spend = cat_spend.sort_values('true_total', ascending=False)
            
            # Create a donut chart
            fig_cat = px.pie(cat_spend, values='true_total', names='category', hole=0.4)
            fig_cat.update_layout(
                margin=dict(t=20, b=20, l=0, r=0),
                height=400
            )
            fig_cat.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_cat, use_container_width=True)