"""
Costco API Fetcher Module

This module handles all communication with the Costco GraphQL API.
It parses manually provided authentication headers and downloads receipt data.

MAIN ENTRY POINTS (To be called from main.py):
----------------------------------------------
1. fetch_quarter(user_name, year, quarter)
   - Downloads the high-level summary of all receipts for a given quarter.
   
2. process_summary(user_name, quarter_name)
   - Reads a downloaded summary and fetches every individual receipt inside it.

INTERNAL HELPERS (Do not need to be called directly):
-----------------------------------------------------
- get_summary_payload()
- get_receipt_payload()
- parse_headers_from_file()
- get_quarter_dates()
- fetch_receipt()
"""

import json
import requests
import time
from pathlib import Path

# The endpoint for all Costco receipt queries
GRAPHQL_URL = "https://ecom-api.costco.com/ebusiness/order/v1/orders/graphql"

def get_summary_payload(start_date: str, end_date: str) -> dict:
    """
    Constructs the GraphQL payload required to fetch a summary of all receipts 
    within a specific date range. This summary contains the barcodes needed 
    to fetch the individual itemized receipts later.
    """
    return {
        "query": """query receiptsWithCounts($startDate: String!, $endDate: String!,$documentType:String!,$documentSubType:String!) {
            receiptsWithCounts(startDate: $startDate, endDate: $endDate,documentType:$documentType,documentSubType:$documentSubType) {
                inWarehouse
                gasStation
                carWash
                gasAndCarWash
                receipts {
                    warehouseName 
                    receiptType  
                    documentType 
                    transactionDateTime 
                    transactionBarcode 
                    transactionType 
                    total 
                    totalItemCount
                }
            }
        }""",
        "variables": {
            "startDate": start_date,
            "endDate": end_date,
            "text": "Custom Range",
            "documentType": "all",
            "documentSubType": "all"
        }
    }

def parse_headers_from_file(user_name: str) -> dict:
    """
    Reads the raw HTTP request headers from a text file and parses them into a Python dictionary.
    This is required because Costco's bot protection blocks automated browsers, so the user
    must manually copy their session headers from their real browser.
    """
    header_file = Path(f"downloads/{user_name}/headers.txt")
    
    if not header_file.exists():
        print(f"Error: Could not find {header_file}")
        print("Please create this file and paste your raw Costco headers into it.")
        return None
        
    with open(header_file, "r") as f:
        raw_text = f.read()
        
    # Parse the raw headers into a dictionary
    headers = {}
    for line in raw_text.split('\n'):
        line = line.strip()
        
        # Ignore empty lines or lines without a colon (like "POST /graphql HTTP/1.1")
        if not line or ':' not in line:
            continue
            
        # Split only on the first colon to handle values that contain colons (like URLs)
        key, value = line.split(':', 1)
        headers[key.strip()] = value.strip()
            
    if 'costco-x-authorization' not in headers:
        print("Warning: Could not find 'costco-x-authorization' in the headers. Requests may fail.")
        
    return headers

def get_receipt_payload(barcode: str, doc_type: str) -> dict:
    """
    Constructs the GraphQL payload required to fetch the full, itemized details 
    of a single receipt. 
    
    Args:
        barcode: The unique transaction barcode from the summary.
        doc_type: Either 'warehouse' or 'fuel'.
    """
    return {
        "query": """query receiptsWithCounts($barcode: String!,$documentType:String!) {
            receiptsWithCounts(barcode: $barcode,documentType:$documentType) {
                receipts {
                    warehouseName
                    receiptType 
                    documentType 
                    transactionDateTime 
                    transactionDate 
                    companyNumber  
                    warehouseNumber 
                    operatorNumber  
                    warehouseName  
                    warehouseShortName   
                    registerNumber  
                    transactionNumber  
                    transactionType
                    transactionBarcode  
                    total 
                    warehouseAddress1 
                    warehouseAddress2 
                    warehouseCity 
                    warehouseState 
                    warehouseCountry 
                    warehousePostalCode
                    totalItemCount 
                    subTotal 
                    taxes
                    total 
                    invoiceNumber
                    sequenceNumber
                    itemArray {  
                        itemNumber 
                        itemDescription01 
                        frenchItemDescription1 
                        itemDescription02 
                        frenchItemDescription2 
                        itemIdentifier 
                        itemDepartmentNumber
                        unit 
                        amount 
                        taxFlag 
                        merchantID 
                        entryMethod
                        transDepartmentNumber
                        fuelUnitQuantity
                        fuelGradeCode
                        itemUnitPriceAmount
                        fuelUomCode
                        fuelUomDescription
                        fuelUomDescriptionFr
                        fuelGradeDescription
                        fuelGradeDescriptionFr
                    }  
                    tenderArray {   
                        tenderTypeCode
                        tenderSubTypeCode
                        tenderDescription    
                        amountTender    
                        displayAccountNumber   
                        sequenceNumber   
                        approvalNumber   
                        responseCode 
                        tenderTypeName 
                        transactionID   
                        merchantID   
                        entryMethod
                        tenderAcctTxnNumber  
                        tenderAuthorizationCode  
                        tenderTypeName
                        tenderTypeNameFr
                        tenderEntryMethodDescription
                        walletType
                        walletId
                        storedValueBucket
                    }    
                    subTaxes {      
                        tax1      
                        tax2      
                        tax3     
                        tax4     
                        aTaxPercent     
                        aTaxLegend     
                        aTaxAmount
                        aTaxPrintCode
                        aTaxPrintCodeFR     
                        aTaxIdentifierCode     
                        bTaxPercent    
                        bTaxLegend     
                        bTaxAmount
                        bTaxPrintCode
                        bTaxPrintCodeFR     
                        bTaxIdentifierCode      
                        cTaxPercent     
                        cTaxLegend    
                        cTaxAmount
                        cTaxIdentifierCode           
                        dTaxPercent     
                        dTaxLegend     
                        dTaxAmount
                        dTaxPrintCode
                        dTaxPrintCodeFR     
                        dTaxIdentifierCode
                        uTaxLegend
                        uTaxAmount
                        uTaxableAmount
                    }   
                    instantSavings   
                    membershipNumber 
                }
            }
        }""",
        "variables": {
            "barcode": barcode,
            "documentType": doc_type
        }
    }

def get_quarter_dates(year: int, quarter: int) -> tuple[str, str, str]:
    """
    Helper function to convert a year and quarter number into the exact 
    start/end date strings required by the Costco API.
    """
    if quarter == 1:
        start_date = f"1/01/{year}"
        end_date = f"3/31/{year}"
    elif quarter == 2:
        start_date = f"4/01/{year}"
        end_date = f"6/30/{year}"
    elif quarter == 3:
        start_date = f"7/01/{year}"
        end_date = f"9/30/{year}"
    elif quarter == 4:
        start_date = f"10/01/{year}"
        end_date = f"12/31/{year}"
    else:
        raise ValueError("Quarter must be between 1 and 4")
        
    quarter_name = f"{year}_Q{quarter}"
    return start_date, end_date, quarter_name

def fetch_quarter(user_name: str, year: int, quarter: int):
    """
    Fetches the high-level summary of all receipts for a specific quarter 
    and saves it to a JSON file. 
    
    Raises an Exception if the request fails (e.g. invalid headers, server error).
    """
    
    # 1. Parse the headers directly from the text file
    headers = parse_headers_from_file(user_name)
    if not headers:
        raise Exception(f"No valid headers found in downloads/{user_name}/headers.txt")
        
    # 2. Get the dates and payload for this quarter
    start_date, end_date, quarter_name = get_quarter_dates(year, quarter)
    payload = get_summary_payload(start_date, end_date)
    
    # 3. Make the POST request using the Python 'requests' library
    print(f"Fetching {quarter_name} for {user_name} ({start_date} to {end_date})...")
    response = requests.post(GRAPHQL_URL, headers=headers, json=payload)
    
    # 4. Check if it worked and save the result
    if response.status_code == 200:
        output_file = Path(f"downloads/{user_name}/summaries/{quarter_name}.json")
        with open(output_file, "w") as f:
            json.dump(response.json(), f, indent=2)
        print(f"Success! Saved to {output_file}")
    else:
        # If it's a 401/403, we give a specific authentication error message
        if response.status_code in (401, 403):
            error_msg = f"Authentication failed (HTTP {response.status_code}). Your headers have likely expired."
        else:
            error_msg = f"API request failed with status code: {response.status_code}\n{response.text}"
            
        raise Exception(error_msg)

def fetch_receipt(user_name: str, barcode: str, receipt_type: str, date_time: str, location: str):
    """
    Fetches the detailed itemized list for a single receipt (Warehouse or Gas) 
    and saves it to a beautifully formatted JSON file.
    """
    headers = parse_headers_from_file(user_name)
    if not headers:
        return
        
    # Map the summary receipt type to the GraphQL documentType
    if receipt_type == "In-Warehouse":
        doc_type = "warehouse"
    elif receipt_type == "Gas Station":
        doc_type = "fuel"
    else:
        print(f"Unknown receipt type: {receipt_type} for barcode {barcode}")
        return
        
    # Format filename parameters for maximum readability
    # Input: '2026-03-10T20:41:00' -> Output: '2026-03-10 20-41-00'
    formatted_date = date_time.replace("T", " ").replace(":", "-")
    
    # Make location ALL CAPS and remove slashes which break file paths
    formatted_loc = location.upper().replace("/", " ")
    
    # Make receipt type ALL CAPS (e.g. "IN-WAREHOUSE" or "GAS STATION")
    formatted_type = receipt_type.upper().replace("/", " ")
    
    # Final format: 2026-03-10 20-41-00 SANTA CLARA IN-WAREHOUSE.json
    filename = f"{formatted_date} {formatted_loc} {formatted_type}.json"
    output_file = Path(f"downloads/{user_name}/receipts/{filename}")
    
    # Skip if we already downloaded it to save time and API calls
    if output_file.exists():
        print(f"Skipping {filename} (already exists)")
        return
        
    payload = get_receipt_payload(barcode, doc_type)
    
    print(f"Fetching receipt: {filename}...")
    response = requests.post(GRAPHQL_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        with open(output_file, "w") as f:
            json.dump(response.json(), f, indent=2)
    else:
        # If the individual receipt fails, we print an error but don't crash the whole script
        print(f"Failed to fetch receipt {barcode}! Status code: {response.status_code}")

def process_summary(user_name: str, quarter_name: str):
    """
    Reads a previously downloaded summary JSON file, extracts all the barcodes,
    and sequentially downloads every individual receipt found in that quarter.
    """
    summary_file = Path(f"downloads/{user_name}/summaries/{quarter_name}.json")
    if not summary_file.exists():
        print(f"Error: Summary file {summary_file} not found.")
        return
        
    with open(summary_file, "r") as f:
        data = json.load(f)
        
    try:
        receipts = data.get("data", {}).get("receiptsWithCounts", {}).get("receipts", [])
    except AttributeError:
        print(f"Error parsing summary file {summary_file}. Unexpected format.")
        return
        
    if not receipts:
        print(f"No receipts found in {quarter_name}.")
        return
        
    print(f"Found {len(receipts)} receipts in {quarter_name}. Fetching details...")
    
    for receipt in receipts:
        barcode = receipt.get("transactionBarcode")
        r_type = receipt.get("receiptType")
        date_time = receipt.get("transactionDateTime")
        location = receipt.get("warehouseName", "Unknown")
        
        if barcode and r_type and date_time:
            fetch_receipt(user_name, barcode, r_type, date_time, location)
            # Be nice to the API
            time.sleep(1)

if __name__ == "__main__":
    # Example usage:
    # fetch_quarter("dinesh", 2026, 1)
    # process_summary("dinesh", "2026_Q1")
    pass
