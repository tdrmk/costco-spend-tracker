import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from data_loader import load_data, apply_filters

st.set_page_config(page_title="Costco Trip History", page_icon="🗓️", layout="wide")
st.title("🗓️ Trip History")

# 1. Fetch Data from Shared Loader
receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

# Apply global sidebar filters
f_receipts, _, _ = apply_filters(receipts_df, warehouse_df, gas_df)

# 2. Format Data for the Calendar Component
calendar_events = []

for _, row in f_receipts.iterrows():
    is_gas = row['receipt_type'] == 'GAS STATION'
    
    # Customize the appearance based on the visit type
    if is_gas:
        title = f"⛽ ${row['total']:.2f}"
        color = "#FF4B4B"  # Streamlit Red
    else:
        title = f"🛒 ${row['total']:.2f}"
        color = "#0068C9"  # Streamlit Blue

    # Append to the events list in the format FullCalendar expects
    calendar_events.append({
        "title": title,
        "start": row['transaction_datetime'].isoformat(),
        "backgroundColor": color,
        "borderColor": color,
        "textColor": "white",
    })

# 3. Configure Calendar Options
if not f_receipts.empty:
    # Open calendar to the most recent visit
    initial_date = f_receipts['transaction_datetime'].max().strftime('%Y-%m-%d')
    
    # Restrict navigation: Start of the first month to the end of the last month
    min_date = f_receipts['transaction_datetime'].min()
    max_date = f_receipts['transaction_datetime'].max()
    
    # Start of the first month (e.g., if first visit is Jan 15, start range at Jan 1)
    start_date = min_date.replace(day=1).strftime('%Y-%m-%d')
    
    # End of the last month (e.g., if last visit is Mar 10, end range at Apr 1 since it's exclusive)
    # We add a month to the max date, then set day to 1
    end_date = (max_date + pd.DateOffset(months=1)).replace(day=1).strftime('%Y-%m-%d')
    
    valid_range = {"start": start_date, "end": end_date}
else:
    initial_date = pd.Timestamp.today().strftime('%Y-%m-%d')
    valid_range = {}

calendar_options = {
    "headerToolbar": {
        "left": "prev",
        "center": "title",
        "right": "next", # Only using month view
    },
    "initialView": "dayGridMonth",
    "initialDate": initial_date,
    "validRange": valid_range,
    "eventDisplay": "list-item", # Minimalist dot style
    "height": 700,
    "displayEventTime": False, # Hide time, only show icon and price
}

# 4. Render the Calendar
calendar(events=calendar_events, options=calendar_options)
