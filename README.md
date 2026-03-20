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

### Stage 3: Visualization (`app.py` & `calendar_app.py`)
This stage provides interactive Streamlit dashboards to visualize the processed data directly from the local SQLite database.

1. Run the main dashboard:
   ```bash
   streamlit run app.py
   ```
   This will open a dashboard in your browser with filters for date ranges, household members, and warehouses, along with charts breaking down spend by category and location.

2. Run the calendar view (optional):
   ```bash
   streamlit run calendar_app.py
   ```
   This provides an alternative calendar-based visualization of your spending.
