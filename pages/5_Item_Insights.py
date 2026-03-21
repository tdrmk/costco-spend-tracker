import streamlit as st
import plotly.express as px
from data_loader import load_data, apply_filters

st.set_page_config(page_title="Costco Spend Tracker - Item Insights", page_icon="🛒", layout="wide")

receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

f_receipts, f_warehouse, f_gas = apply_filters(receipts_df, warehouse_df, gas_df)

st.header("Item Price History (Inflation Tracker)")
st.write("Track how the price of your favorite staples has changed over time.")

# Filter out items only bought once to make the list more relevant
item_counts = f_warehouse['item_name'].value_counts()
repeat_items = item_counts[item_counts > 1].index.tolist()

if not repeat_items:
    st.info("No repeat items found in the selected date range.")
else:
    selected_item = st.selectbox("Select an item to analyze:", sorted(repeat_items))
    
    item_data = f_warehouse[f_warehouse['item_name'] == selected_item].sort_values('date').copy()
    
    if not item_data.empty:
        # Calculate the effective price per unit (accounting for discounts)
        # We use adjusted_amount (which includes discounts but excludes CRV/Taxes) divided by quantity
        # Prevent division by zero by falling back to the adjusted_amount if quantity is 0
        item_data['effective_price'] = item_data.apply(
            lambda row: row['adjusted_amount'] / row['quantity'] if row['quantity'] > 0 else row['adjusted_amount'], 
            axis=1
        )
        
        min_price = item_data['effective_price'].min()
        max_price = item_data['effective_price'].max()
        last_price = item_data.iloc[-1]['effective_price']
        last_date_str = item_data.iloc[-1]['date'].strftime('%b %d, %Y')
        
        min_date_str = item_data[item_data['effective_price'] == min_price].iloc[0]['date'].strftime('%b %Y')
        max_date_str = item_data[item_data['effective_price'] == max_price].iloc[0]['date'].strftime('%b %Y')
        
        # Get the most recent description and category for this item
        item_desc = item_data.iloc[-1].get('item_details', '')
        item_cat = item_data.iloc[-1].get('category', 'Unknown')
        
        if item_desc:
            st.caption(f"**Category:** {item_cat} | **Details:** {item_desc}")
        else:
            st.caption(f"**Category:** {item_cat}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Last Paid Price", f"${last_price:,.2f}", f"on {last_date_str}", delta_color="off")
        col2.metric("Cheapest", f"${min_price:,.2f}", f"in {min_date_str}", delta_color="off")
        col3.metric("Costliest", f"${max_price:,.2f}", f"in {max_date_str}", delta_color="off")
        
        # Small line graph
        fig = px.line(item_data, x='date', y='effective_price', markers=True, 
                      title=f"Effective Price Trend (After Discounts): {selected_item}")
        fig.update_layout(yaxis_title="Effective Price ($)", xaxis_title="Date", height=300)
        # Add a slight buffer to the y-axis so the line doesn't touch the very top/bottom
        fig.update_yaxes(range=[min_price * 0.9, max_price * 1.1])
        st.plotly_chart(fig, use_container_width=True)
        
        # Show raw purchase history for this item
        with st.expander("View Purchase History"):
            # Add effective_price to the display dataframe
            display_hist = item_data[['date', 'warehouse_name', 'quantity', 'unit_price', 'discount_amount', 'effective_price', 'adjusted_amount']].copy()
            
            # Format for display
            display_hist['unit_price'] = display_hist['unit_price'].apply(lambda x: f"${x:.2f}")
            display_hist['discount_amount'] = display_hist['discount_amount'].apply(lambda x: f"${x:.2f}" if x < 0 else "")
            display_hist['effective_price'] = display_hist['effective_price'].apply(lambda x: f"${x:.2f}")
            display_hist['adjusted_amount'] = display_hist['adjusted_amount'].apply(lambda x: f"${x:.2f}")
            
            display_hist.columns = ['Date', 'Location', 'Qty', 'Shelf Price', 'Discount', 'Effective Price/Unit', 'Total Paid']
            st.dataframe(display_hist, hide_index=True)