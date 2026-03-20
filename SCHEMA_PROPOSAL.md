## Proposed Highly Normalized Schema

Based on the goal of strict normalization, we can break the data down into 5 distinct tables to eliminate all redundancy.

### 1. `warehouses` (Lookup Table)
Stores unique Costco locations.
*   `warehouse_number` (INTEGER PRIMARY KEY) - e.g., `129`
*   `warehouse_name` (TEXT) - e.g., `"SANTA CLARA"`
*   `address` (TEXT) - e.g., `"1601 COLEMAN AVE"`
*   `city` (TEXT) - e.g., `"SANTA CLARA"`
*   `state` (TEXT) - e.g., `"CA"`
*   `zip_code` (TEXT) - e.g., `"95050"`

### 2. `products` (Lookup Table)
Stores unique items sold at Costco (both warehouse and gas).
*   `item_number` (TEXT PRIMARY KEY) - e.g., `"1303463"` or `"800599"` (Gas)
*   `item_name` (TEXT) - e.g., `"VITALPROTEIN"`
*   `item_details` (TEXT) - e.g., `"COLLAGEN 1.5LBS P360 CU45"`
*   `friendly_name` (TEXT) - Optional, human-readable name for UI display (e.g., `"Vital Proteins Collagen"`)
*   `department_number` (INTEGER) - e.g., `20`
*   `is_taxed` (TEXT) - `"Y"` or `"N"` (Assuming this is static per product in your state)
*   `item_identifier` (TEXT) - `"E"`, `"F"`, or null

### 3. `receipts` (Core Table)
Stores the trip metadata.
*   `transaction_barcode` (TEXT PRIMARY KEY)
*   `user_name` (TEXT)
*   `receipt_type` (TEXT) - `"IN-WAREHOUSE"` or `"GAS STATION"`
*   `transaction_datetime` (TEXT)
*   `warehouse_number` (INTEGER) - **FOREIGN KEY** to `warehouses`
*   `total` (REAL)
*   `subtotal` (REAL)
*   `taxes` (REAL)
*   `tender_type` (TEXT) - Strictly `"CREDIT"` or `"DEBIT"`
*   `account_number` (TEXT) - e.g., `"8052"`

### 4. `warehouse_purchases` (Line Items)
Stores individual items bought inside the store.
*   `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
*   `transaction_barcode` (TEXT) - **FOREIGN KEY** to `receipts`
*   `item_number` (TEXT) - **FOREIGN KEY** to `products`
*   `quantity` (REAL)
*   `unit_price` (REAL) - The base price per unit
*   `amount` (REAL) - The total line amount (`quantity * unit_price`)
*   `unit_discount` (REAL) - The negative discount applied per unit (e.g. `-6.00`)
*   `discount_amount` (REAL) - The total negative discount (`quantity * unit_discount`)
*   `adjusted_amount` (REAL) - The amount after discount (`amount + discount_amount`). **Used for tax calculation.**
*   `fee_amount` (REAL) - Non-taxable fees applied to the item (e.g., CRV bottle deposit).
*   `calculated_tax` (REAL) - Proportional tax based on `adjusted_amount`
*   `true_total` (REAL) - `adjusted_amount + fee_amount + calculated_tax`
*   **CONSTRAINT**: `UNIQUE(transaction_barcode, item_number)` to prevent duplicate inserts.

### 5. `gas_purchases` (Line Items)
Stores fuel purchases (separated because the schema is entirely different).
*   `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
*   `transaction_barcode` (TEXT) - **FOREIGN KEY** to `receipts`
*   `item_number` (TEXT) - **FOREIGN KEY** to `products` (Usually "800599" for Regular)
*   `quantity_gallons` (REAL)
*   `unit_price` (REAL) - Price per gallon
*   `amount` (REAL) - Total cost
*   `fuel_grade` (TEXT) - e.g., `"Regular"`
*   **CONSTRAINT**: `UNIQUE(transaction_barcode, item_number)` to prevent duplicate inserts.