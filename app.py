import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path

# --- Page Config ---
st.set_page_config(page_title="Costco Spend Tracker", page_icon="🛒", layout="wide")

DB_PATH = Path("costco_spend.db")

@st.cache_data
def load_data():
    if not DB_PATH.exists():
        return None, None, None
        
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Load Receipts (Base for filtering)
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
        53: "Gas Station",
        17: "Dairy & Refrigerated",
        65: "Fresh Produce",
        19: "Refrigerated Deli",
        18: "Frozen Foods",
        61: "Meat & Seafood",
        63: "Deli / Prepared Foods",
        14: "Household & Cleaning",
        23: "Home & Storage",
        13: "Pantry / Dry Goods",
        20: "Personal Care & Wellness",
        93: "Pharmacy / Vitamins",
        34: "Home & Bath",
        32: "Kitchen & Home",
        26: "Clothing & Shoes",
        31: "Clothing & Shoes",
        39: "Clothing & Shoes",
        11: "Snacks & Candy",
        12: "Snacks & Candy",
        88: "Food Court",
        28: "Toys & Games",
        27: "Garden & Patio",
        75: "Automotive / Tolls",
        87: "Tire Center",
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

receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

# --- Sidebar Filters ---
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

f_receipts = receipts_df[r_mask]
f_warehouse = warehouse_df[w_mask]
f_gas = gas_df[g_mask]

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Overview", "🧾 Receipts", "🏥 FSA/HSA", "⛽ Gas Analysis", "🛒 Item Insights", "📋 Product Catalog"])

# --- Tab 1: Overview ---
with tab1:
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

# --- Tab 2: Receipts ---
with tab2:
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

# --- Tab 3: FSA/HSA ---
with tab3:
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

# --- Tab 4: Gas Analysis ---
with tab4:
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

# --- Tab 5: Item Insights (Inflation Tracker) ---
with tab5:
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

# --- Tab 6: Product Catalog ---
with tab6:
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
