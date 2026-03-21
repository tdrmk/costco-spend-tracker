import streamlit as st

st.set_page_config(
    page_title="Costco Spend Tracker",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Costco Spend Tracker")

st.markdown("""
Welcome to your Costco Spend Tracker! 

Please select a page from the sidebar to view your data:

- **📊 Overview:** High-level metrics, monthly trends, and category breakdowns.
- **🧾 Receipts:** A digital receipt explorer and timeline.
- **🏥 FSA/HSA:** Filters for eligible health items for easy reimbursement.
- **⛽ Gas Analysis:** Tracks fuel volume, prices, and estimates mileage.
- **🛒 Item Insights:** An inflation tracker for repeat purchases.
- **📋 Product Catalog:** A searchable history of all unique items bought.
""")