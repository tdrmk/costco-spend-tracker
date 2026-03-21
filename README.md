# Costco Spend Tracker

A tool to fetch, process, and visualize Costco household spend data using Python, Pandas, and Streamlit.

## Setup Instructions

0. **Create and activate a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

1. **Install Python dependencies**:
   Make sure to use the standard PyPI index to avoid any internal artifact registry issues.
   ```bash
   pip install --index-url https://pypi.org/simple/ -r requirements.txt
   ```

## Usage

The project is broken down into three stages:

### Stage 1: Ingestion (`ingest.py`)
Because Costco uses strict bot protection (Akamai), this script requires a manual authentication step.

1. Run the ingestion script:
   ```bash
   python ingest.py
   ```
2. The script will ask for the names of the household members and the date ranges you want to fetch.
3. It will then open a `headers.txt` file in `vim` directly in your terminal.
4. Open your normal web browser, log into Costco.com, open the Network tab, and copy the "Request Headers" from any `graphql` request.
5. Paste those headers into `vim`, save, and exit (`:wq`).
6. The script will automatically download all receipt summaries and itemized receipts for the requested date range!

### Stage 2: Processing (`process.py`)
This script parses the downloaded JSON receipts, normalizes the data, applies discounts correctly, calculates proportional taxes, and loads everything into a highly normalized local SQLite database (`costco_spend.db`).

1. Run the processing script:
   ```bash
   python process.py
   ```

### Stage 3: Visualization (`Home.py` + `pages/`)
This stage is a **multi-page Streamlit app** that reads from the local SQLite database (`costco_spend.db`). Use the sidebar to switch between views.

1. Run the app from the project root:
   ```bash
   streamlit run Home.py
   ```

2. **Pages** (sidebar):
   - **Overview** — metrics, monthly trends, warehouse spend by category
   - **Receipts** — trip timeline and receipt explorer
   - **FSA/HSA** — eligible items for reimbursement
   - **Gas Analysis** — fuel usage and price trends
   - **Item Insights** — price history for repeat purchases
   - **Product Catalog** — searchable purchase history
   - **Trip History** — calendar view of visits (warehouse vs gas), respects sidebar filters

Shared filters (date range and household member) are in the sidebar on each page.

The app uses `data_loader.py` for cached database reads and consistent filtering across pages.
