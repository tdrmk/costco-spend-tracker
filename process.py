import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

def setup_database(db_path: str = "costco_spend.db") -> sqlite3.Connection:
    """Creates the SQLite database and tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Warehouses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            warehouse_number INTEGER PRIMARY KEY,
            warehouse_name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT
        )
    """)
    
    # 2. Products
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            item_number TEXT PRIMARY KEY,
            item_name TEXT,
            item_details TEXT,
            department_number INTEGER,
            is_taxed TEXT,
            item_identifier TEXT
        )
    """)
    
    # 3. Receipts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            transaction_barcode TEXT PRIMARY KEY,
            user_name TEXT,
            receipt_type TEXT,
            transaction_datetime TEXT,
            warehouse_number INTEGER,
            total REAL,
            subtotal REAL,
            taxes REAL,
            tender_type TEXT,
            account_number TEXT,
            FOREIGN KEY(warehouse_number) REFERENCES warehouses(warehouse_number)
        )
    """)
    
    # 4. Warehouse Purchases
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warehouse_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_barcode TEXT,
            item_number TEXT,
            quantity REAL,
            unit_price REAL,
            amount REAL,
            unit_discount REAL,
            discount_amount REAL,
            adjusted_amount REAL,
            fee_amount REAL,
            calculated_tax REAL,
            true_total REAL,
            FOREIGN KEY(transaction_barcode) REFERENCES receipts(transaction_barcode),
            FOREIGN KEY(item_number) REFERENCES products(item_number),
            UNIQUE(transaction_barcode, item_number)
        )
    """)
    
    # 5. Gas Purchases
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gas_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_barcode TEXT,
            item_number TEXT,
            quantity_gallons REAL,
            unit_price REAL,
            amount REAL,
            fuel_grade TEXT,
            FOREIGN KEY(transaction_barcode) REFERENCES receipts(transaction_barcode),
            FOREIGN KEY(item_number) REFERENCES products(item_number),
            UNIQUE(transaction_barcode, item_number)
        )
    """)
    
    conn.commit()
    return conn

def save_to_db(conn: sqlite3.Connection, warehouses: Dict, products: Dict, receipts: List, warehouse_purchases: List, gas_purchases: List) -> None:
    """Inserts the processed data into the SQLite database."""
    cursor = conn.cursor()
    
    # 1. Insert Warehouses (REPLACE updates existing records if Costco changed the name/address)
    warehouse_tuples = [
        (w["warehouse_number"], w["warehouse_name"], w["address"], w["city"], w["state"], w["zip_code"])
        for w in warehouses.values()
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO warehouses 
        (warehouse_number, warehouse_name, address, city, state, zip_code) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, warehouse_tuples)
    
    # 2. Insert Products (REPLACE updates existing records)
    product_tuples = [
        (p["item_number"], p["item_name"], p["item_details"], p["department_number"], p["is_taxed"], p["item_identifier"])
        for p in products.values()
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO products 
        (item_number, item_name, item_details, department_number, is_taxed, item_identifier) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, product_tuples)
    
    # 3. Insert Receipts (IGNORE skips if we already processed this receipt)
    receipt_tuples = [
        (r["transaction_barcode"], r["user_name"], r["receipt_type"], r["transaction_datetime"], 
         r["warehouse_number"], r["total"], r["subtotal"], r["taxes"], r["tender_type"], r["account_number"])
        for r in receipts
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO receipts 
        (transaction_barcode, user_name, receipt_type, transaction_datetime, warehouse_number, 
         total, subtotal, taxes, tender_type, account_number) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, receipt_tuples)
    
    # 4. Insert Warehouse Purchases (IGNORE skips duplicates thanks to UNIQUE constraint)
    wp_tuples = [
        (wp["transaction_barcode"], wp["item_number"], wp["quantity"], wp["unit_price"], wp["amount"], 
         wp["unit_discount"], wp["discount_amount"], wp["adjusted_amount"], wp["fee_amount"], wp["calculated_tax"], wp["true_total"])
        for wp in warehouse_purchases
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO warehouse_purchases 
        (transaction_barcode, item_number, quantity, unit_price, amount, unit_discount, 
         discount_amount, adjusted_amount, fee_amount, calculated_tax, true_total) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, wp_tuples)
    
    # 5. Insert Gas Purchases (IGNORE skips duplicates thanks to UNIQUE constraint)
    gp_tuples = [
        (gp["transaction_barcode"], gp["item_number"], gp["quantity_gallons"], gp["unit_price"], gp["amount"], gp["fuel_grade"])
        for gp in gas_purchases
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO gas_purchases 
        (transaction_barcode, item_number, quantity_gallons, unit_price, amount, fuel_grade) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, gp_tuples)
    
    conn.commit()
    print("Database insertion complete. Saved to costco_spend.db")

def normalize_tender(tender_obj: dict) -> str:
    """Extracts and normalizes the payment method from a tender object to 'CREDIT' or 'DEBIT'."""
    if not tender_obj:
        return "UNKNOWN"
        
    code = tender_obj.get("tenderTypeCode") or ""
    type_name = tender_obj.get("tenderTypeName") or ""
    
    # 1. Primary check: Use the internal code if available (Warehouse)
    if code == "061":
        return "CREDIT"
    if code == "011":
        return "DEBIT"
        
    # 2. Fallback: Gas stations use "CreditDebit" for the code, so we must check the type name
    if code == "CreditDebit":
        if type_name == "VI Acct #":
            return "CREDIT"
        if type_name == "DB Acct #":
            return "DEBIT"
            
    # 3. If we hit something we haven't seen before, fail loudly so we can investigate
    raise ValueError(f"Unknown tender type encountered! Code: '{code}', TypeName: '{type_name}'")

def process_receipt(file_path: Path, user_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parses a single JSON receipt and returns the normalized table data."""
    with open(file_path, "r") as f:
        try:
            data = json.load(f)
            receipt = data["data"]["receiptsWithCounts"]["receipts"][0]
        except (json.JSONDecodeError, KeyError, IndexError):
            print(f"Error parsing {file_path}")
            return None

    # 1. Extract Receipt Metadata
    barcode = receipt.get("transactionBarcode")
    receipt_type = receipt.get("receiptType", "").upper()
    
    tender_array = receipt.get("tenderArray", [])
    tender = tender_array[0] if tender_array else {}
    
    # We can safely use the top-level 'taxes' field instead of digging into 'subTaxes'
    total_tax = float(receipt.get("taxes") or 0.0)
    
    receipt_data = {
        "transaction_barcode": barcode,
        "user_name": user_name,
        "receipt_type": receipt_type,
        "transaction_datetime": receipt.get("transactionDateTime"),
        "warehouse_number": receipt.get("warehouseNumber"),
        "total": float(receipt.get("total") or 0.0),
        "subtotal": float(receipt.get("subTotal") or 0.0),
        "taxes": total_tax,
        "tender_type": normalize_tender(tender),
        "account_number": tender.get("displayAccountNumber")
    }
    
    warehouse_data = {
        "warehouse_number": receipt.get("warehouseNumber"),
        "warehouse_name": receipt.get("warehouseName", "").upper(),
        "address": receipt.get("warehouseAddress1"),
        "city": receipt.get("warehouseCity"),
        "state": receipt.get("warehouseState"),
        "zip_code": receipt.get("warehousePostalCode")
    }

    # 2. Extract Items (Pass 1: Apply Discounts & Calculate Taxable Subtotal)
    raw_items = receipt.get("itemArray", [])
    processed_items = []
    taxable_subtotal = 0.0
    
    for item in raw_items:
        desc = (item.get("itemDescription01") or "").strip()
        amount = float(item.get("amount") or 0.0)
        
        # If it's a discount, apply it to the PREVIOUS item
        if desc.startswith("/"):
            if processed_items:
                prev = processed_items[-1]
                prev["discount_amount"] += amount # amount is negative
                prev["adjusted_amount"] += amount
                if prev["quantity"] > 0:
                    prev["unit_discount"] = prev["discount_amount"] / prev["quantity"]
            continue
            
        # If it's a CRV fee, apply it to the PREVIOUS item
        if "CA REDEMP VAL" in desc:
            if processed_items:
                prev = processed_items[-1]
                # CRV is NOT taxable, so we do NOT add it to adjusted_amount.
                # We store it separately so it can be added to the true_total at the end.
                prev["fee_amount"] += amount
            continue
            
        # Otherwise, it's a normal item
        qty = float(item.get("unit") or 1.0)
        
        desc1 = item.get("itemDescription01") or ""
        desc2 = item.get("itemDescription02") or ""
        
        processed_item = {
            "transaction_barcode": barcode,
            "item_number": item.get("itemNumber"),
            "item_name": desc1.strip(),
            "item_details": desc2.strip(),
            "department_number": item.get("itemDepartmentNumber"),
            "is_taxed": item.get("taxFlag", "N"),
            "item_identifier": item.get("itemIdentifier"),
            
            "quantity": qty,
            "unit_price": float(item.get("itemUnitPriceAmount") or 0.0),
            "amount": amount,
            "unit_discount": 0.0,
            "discount_amount": 0.0,
            "adjusted_amount": amount,
            "fee_amount": 0.0,
            "calculated_tax": 0.0,
            "true_total": 0.0,
            
            # Gas specific
            "fuel_gallons": float(item.get("fuelUnitQuantity") or 0.0) if receipt_type == "GAS STATION" else None,
            "fuel_grade": item.get("fuelGradeDescription")
        }
        processed_items.append(processed_item)
        
    # Calculate taxable subtotal based on adjusted amounts
    for item in processed_items:
        if item["is_taxed"] == "Y":
            taxable_subtotal += item["adjusted_amount"]
            
    # 3. Extract Items (Pass 2: Distribute Taxes)
    products = {} # Use dict to automatically deduplicate products by item_number
    warehouse_purchases = []
    gas_purchases = []
    
    for item in processed_items:
        # Build Product Lookup
        if item["item_number"]:
            products[item["item_number"]] = {
                "item_number": item["item_number"],
                "item_name": item["item_name"],
                "item_details": item["item_details"],
                "department_number": item["department_number"],
                "is_taxed": item["is_taxed"],
                "item_identifier": item["item_identifier"]
            }
            
        # Calculate proportional tax
        if item["is_taxed"] == "Y" and taxable_subtotal > 0:
            tax_proportion = item["adjusted_amount"] / taxable_subtotal
            item["calculated_tax"] = round(total_tax * tax_proportion, 2)
            
        item["true_total"] = round(item["adjusted_amount"] + item["fee_amount"] + item["calculated_tax"], 2)
        
        # Route to correct purchase table
        if receipt_type == "GAS STATION":
            gas_purchases.append({
                "transaction_barcode": item["transaction_barcode"],
                "item_number": item["item_number"],
                "quantity_gallons": item["fuel_gallons"],
                "unit_price": item["unit_price"],
                "amount": item["amount"],
                "fuel_grade": item["fuel_grade"]
            })
        else:
            warehouse_purchases.append({
                "transaction_barcode": item["transaction_barcode"],
                "item_number": item["item_number"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "amount": item["amount"],
                "unit_discount": item["unit_discount"],
                "discount_amount": item["discount_amount"],
                "adjusted_amount": item["adjusted_amount"],
                "fee_amount": item["fee_amount"],
                "calculated_tax": item["calculated_tax"],
                "true_total": item["true_total"]
            })

    return {
        "warehouse": warehouse_data,
        "receipt": receipt_data,
        "products": products, # Return the dictionary directly
        "warehouse_purchases": warehouse_purchases,
        "gas_purchases": gas_purchases
    }

def main():
    print("=== Costco Spend Tracker: Data Processing ===")
    
    downloads_dir = Path("downloads")
    if not downloads_dir.exists():
        print("No downloads directory found. Run ingest.py first.")
        return
        
    # Global in-memory storage
    all_warehouses = {}
    all_products = {}
    all_receipts = []
    all_warehouse_purchases = []
    all_gas_purchases = []
    
    # Find all receipt JSON files for all users
    # Pattern: downloads/[user]/receipts/*.json
    receipt_files = list(downloads_dir.glob("*/receipts/*.json"))
    
    if not receipt_files:
        print("No receipt files found to process.")
        return
        
    print(f"Found {len(receipt_files)} receipts. Processing...")
    
    for file_path in receipt_files:
        # Extract user_name from the path (e.g., downloads/dinesh/receipts/... -> dinesh)
        user_name = file_path.parent.parent.name
        
        result = process_receipt(file_path, user_name)
        if not result:
            continue
            
        # 1. Deduplicate Warehouses (Use dictionary to keep only unique locations)
        w = result["warehouse"]
        all_warehouses.update({w["warehouse_number"]: w})
        
        # 2. Deduplicate Products (Use dictionary to keep only unique items)
        all_products.update(result["products"])
        
        # 3. Append Transaction Data (Use lists to keep every single purchase event)
        all_receipts.append(result["receipt"])
        all_warehouse_purchases.extend(result["warehouse_purchases"])
        all_gas_purchases.extend(result["gas_purchases"])

    print("\n=== PROCESSING COMPLETE ===")
    print(f"Unique Warehouses: {len(all_warehouses)}")
    print(f"Unique Products:   {len(all_products)}")
    print(f"Total Receipts:    {len(all_receipts)}")
    print(f"Warehouse Items:   {len(all_warehouse_purchases)}")
    print(f"Gas Station Trips: {len(all_gas_purchases)}")
    
    # 4. Save to Database
    print("\nSaving to database...")
    conn = setup_database()
    save_to_db(conn, all_warehouses, all_products, all_receipts, all_warehouse_purchases, all_gas_purchases)
    conn.close()
    
    # Optional: Print a small sample to verify
    if all_products:
        print("\nSample Product:")
        print(json.dumps(next(iter(all_products.values())), indent=2))

if __name__ == "__main__":
    main()