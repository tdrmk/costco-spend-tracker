# Project Plan & Architecture

This document outlines the architecture and planned implementation for the Costco Spend Tracker. The project is broken down into a three-stage pipeline: Ingestion, Processing, and Visualization.

## Directory Structure

```text
costco-spend-tracker/
├── ingest.py              # Stage 1: Main orchestration script for fetching data
├── fetch_api.py           # Stage 1: Helper module for Costco GraphQL API requests
├── process.py             # Stage 2: Parses JSON and updates SQLite database
├── app.py                 # Stage 3: Streamlit dashboard for visualization
├── costco_spend.db        # SQLite database storing processed receipts
├── downloads/             # Raw JSON responses from the GraphQL API
│   ├── [user_1]/
│   │   ├── headers.txt    # Paste your raw HTTP headers here!
│   │   ├── summaries/
│   │   └── receipts/
│   └── [user_2]/
```

## Stage 1: Ingestion (`ingest.py` & `fetch_api.py`)
**Goal:** Download raw receipt data from Costco using manually provided headers.
*   **Prompting (`ingest.py`):** Ask the user for the names of household members and the date range (start/end quarters) they want to fetch.
*   **Authentication (`ingest.py`):** The script opens `downloads/[user]/headers.txt` in `vim` directly in the terminal. The user logs into Costco manually, copies the raw HTTP request headers from the Network tab, pastes them into `vim`, and saves.
*   **Fetching Summaries (`fetch_api.py`):** The script parses the saved headers and uses them to make GraphQL XHR requests to fetch receipt summaries quarter by quarter.
*   **Fetching Receipts (`fetch_api.py`):** Parse the summaries to get individual `transactionBarcode`s, then make subsequent GraphQL requests to fetch the full itemized receipts (handling both Warehouse and Gas Station receipts).
*   **Storage:** Save all responses as raw JSON files in `downloads/[user]/...`.

## Stage 2: Processing (`process.py`)
**Goal:** Transform the raw JSON data into a structured, highly normalized SQLite database.
*   **Parsing:** Iterate through the downloaded JSON receipt files.
*   **Normalization:** Extract data into 5 distinct tables (`warehouses`, `products`, `receipts`, `warehouse_purchases`, `gas_purchases`) to eliminate redundancy.
*   **Business Logic:** Correctly apply Costco's unique discount format (negative items) to the preceding product and calculate proportional taxes based on the adjusted item amounts.
*   **Database Loading:** Insert the records into a local SQLite database (`costco_spend.db`). Uses `INSERT OR IGNORE` for lookup tables (`warehouses`, `products`) so reruns do not overwrite rows (e.g. manual `friendly_name`), and `INSERT OR IGNORE` for receipts and line items with unique constraints so idempotent runs never duplicate transaction data.

## Stage 3: Visualization (`app.py`)
**Goal:** Provide an interactive dashboard to view and analyze spending.
*   **Framework:** Built using Streamlit.
*   **Data Source:** Reads directly from the normalized `costco_spend.db`.
*   **Features:** Will include filters to toggle between individual household members or view combined household spending, along with charts and tables breaking down spend by category, date, and location.
