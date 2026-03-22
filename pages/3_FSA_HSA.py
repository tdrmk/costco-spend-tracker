import streamlit as st
from data_loader import load_data, apply_filters

st.set_page_config(page_title="Costco Spend Tracker - FSA/HSA", page_icon="🏥", layout="wide")

receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

f_receipts, f_warehouse, f_gas, _, _ = apply_filters(receipts_df, warehouse_df, gas_df)

st.header("FSA / HSA Eligible Items")

# Filter warehouse items for item_identifier == 'F'
fsa_items = f_warehouse[f_warehouse['item_identifier'] == 'F'].copy()

if fsa_items.empty:
    st.info("No FSA/HSA eligible items found in this date range.")
else:
    total_fsa_spend = fsa_items['true_total'].sum()
    
    st.success(f"### Total Eligible Spend: **${total_fsa_spend:,.2f}**")
    st.write("Use the table below for your insurance or tax reimbursement claims.")
    
    # Clean up the dataframe for display/export
    display_fsa = fsa_items[['date', 'warehouse_name', 'item_name', 'item_details', 'quantity', 'true_total']].copy()
    display_fsa = display_fsa.sort_values('date', ascending=False)
    display_fsa.columns = ['Date', 'Location', 'Item', 'Details', 'Qty', 'Total Paid (Inc. Tax)']
    
    # Format currency for display
    display_fsa['Total Paid (Inc. Tax)'] = display_fsa['Total Paid (Inc. Tax)'].apply(lambda x: f"${x:.2f}")
    
    st.dataframe(display_fsa, hide_index=True, use_container_width=True)