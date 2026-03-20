import time
import subprocess
from datetime import datetime
from pathlib import Path

# Import our custom API fetching functions
from fetch_api import fetch_quarter, process_summary

def get_current_quarter() -> tuple[int, int]:
    """
    Returns the current year and quarter based on today's date.
    Used to provide smart defaults so the user doesn't have to type the current year.
    """
    now = datetime.now()
    year = now.year
    # Calculate quarter: Jan-Mar=1, Apr-Jun=2, Jul-Sep=3, Oct-Dec=4
    quarter = (now.month - 1) // 3 + 1
    return year, quarter

def setup_directories(user_name: str):
    """
    Creates the necessary folder structure for a given user.
    Ensures the downloads/ directory exists before we try to save files there.
    
    Creates:
    - downloads/[user_name]/summaries/ : Stores the quarterly JSON lists of barcodes
    - downloads/[user_name]/receipts/  : Stores the detailed itemized JSON receipts
    - downloads/[user_name]/headers.txt: Empty file for the user to paste auth headers
    """
    base_dir = Path(f"downloads/{user_name}")
    
    # Create the subdirectories for raw JSON data
    (base_dir / "summaries").mkdir(parents=True, exist_ok=True)
    (base_dir / "receipts").mkdir(parents=True, exist_ok=True)
    
    # Create an empty headers.txt if it doesn't exist so the user can paste into it
    header_file = base_dir / "headers.txt"
    if not header_file.exists():
        header_file.touch()
        
    return base_dir

def prompt_for_quarters() -> tuple[int, int, int, int]:
    """
    Prompts the user for start and end dates in the terminal.
    Includes validation to ensure the dates make chronological sense.
    Returns a tuple of (start_year, start_q, end_year, end_q).
    """
    current_year, current_q = get_current_quarter()
    
    while True:
        try:
            print("\n--- Start Date ---")
            start_year_input = input("Enter start year (e.g., 2025): ").strip()
            if not start_year_input:
                print("Start year is required.")
                continue
            start_year = int(start_year_input)
            
            print("Quarters: 1 (Jan-Mar), 2 (Apr-Jun), 3 (Jul-Sep), 4 (Oct-Dec)")
            start_q_input = input("Enter start quarter (1-4): ").strip()
            if not start_q_input:
                print("Start quarter is required.")
                continue
            start_q = int(start_q_input)
            
            print("\n--- End Date ---")
            print(f"Press Enter to default to current quarter ({current_year} Q{current_q})")
            
            end_year_input = input("Enter end year (e.g., 2026): ").strip()
            if not end_year_input:
                # If they just press Enter, default to today's year and quarter
                end_year = current_year
                end_q = current_q
            else:
                end_year = int(end_year_input)
                print("Quarters: 1 (Jan-Mar), 2 (Apr-Jun), 3 (Jul-Sep), 4 (Oct-Dec)")
                end_q_input = input("Enter end quarter (1-4): ").strip()
                # If they entered a year but pressed enter for quarter, default to Q4 of that year
                end_q = int(end_q_input) if end_q_input else 4
            
            # Validate the inputs
            if 1 <= start_q <= 4 and 1 <= end_q <= 4:
                # Ensure start date is chronologically before or equal to end date
                if start_year < end_year or (start_year == end_year and start_q <= end_q):
                    return start_year, start_q, end_year, end_q
                else:
                    print("Error: Start date must be before or equal to end date.")
            else:
                print("Error: Quarter must be between 1 and 4.")
                
        except ValueError:
            print("Invalid input. Please enter numbers only.")

def generate_quarter_list(start_year: int, start_q: int, end_year: int, end_q: int) -> list[tuple[int, int]]:
    """
    Takes a start date and end date, and generates a sequential list of all 
    (year, quarter) tuples in between them, handling year boundaries correctly.
    """
    quarters_to_fetch = []
    iter_year = start_year
    iter_q = start_q
    
    # Keep looping as long as iter_year < end_year
    # OR if we are in the end_year, as long as iter_q <= end_q
    while iter_year < end_year or (iter_year == end_year and iter_q <= end_q):
        quarters_to_fetch.append((iter_year, iter_q))
        
        # Advance to the next quarter
        iter_q += 1
        
        # If we pass Q4, roll over to Q1 of the next year
        if iter_q > 4:
            iter_q = 1
            iter_year += 1
            
    return quarters_to_fetch

def prompt_for_users() -> list[str]:
    """
    Prompts for the number of household members and their names.
    Automatically calls setup_directories() for each valid name entered.
    Returns a list of names.
    """
    while True:
        try:
            num_input = input("How many household members are we fetching data for? (e.g., 1 or 2): ").strip()
            if not num_input:
                print("Please enter a number.")
                continue
                
            num_members = int(num_input)
            if num_members > 0:
                break
            else:
                print("Number must be greater than 0.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    users = []
    for i in range(num_members):
        while True:
            name = input(f"Enter name for member {i+1}: ").strip()
            if name:
                users.append(name)
                setup_directories(name)
                break
            else:
                print("Name cannot be empty.")
        
    return users

def main():
    """
    The main orchestration function.
    1. Gets user info.
    2. Gets date ranges.
    3. Loops through every user and every quarter, downloading the data.
    """
    print("=== Costco Spend Tracker: Ingestion ===")
    
    # 1. Prompt for household members
    users = prompt_for_users()

    # 2. Prompt for the start and end quarters
    start_year, start_q, end_year, end_q = prompt_for_quarters()
    quarters_to_fetch = generate_quarter_list(start_year, start_q, end_year, end_q)

    # 3. Execute the fetching pipeline for each user
    for user in users:
        print("\n" + "="*50)
        print(f"STARTING INGESTION FOR: {user.upper()}")
        print("="*50)
        
        header_file = Path(f"downloads/{user}/headers.txt")
        print(f"\nOpening {header_file} in vim...")
        print("Please paste your latest Costco HTTP request headers into it, save, and exit (:wq).")
        
        # Give the user a second to read the prompt before vim takes over the terminal
        time.sleep(2)
        
        # Open the file directly in the terminal using vim
        try:
            # We use check_call so the Python script pauses and waits for vim to close
            subprocess.check_call(['vim', str(header_file)])
        except Exception as e:
            print(f"Could not open vim automatically: {e}")
            input(f"\nPlease manually edit {header_file} and press Enter when done...")
        
        # Loop through the calculated date range
        for year, quarter in quarters_to_fetch:
            quarter_name = f"{year}_Q{quarter}"
            
            print(f"\n--- Processing {quarter_name} ---")
            
            try:
                # Step A: Download the summary JSON
                # This fetches the high-level list of barcodes for the quarter
                fetch_quarter(user, year, quarter)
                
                # Step B: Parse the summary and download individual receipts
                # This reads the summary we just downloaded and fetches the itemized details
                process_summary(user, quarter_name)
                
            except Exception as e:
                print(f"\n❌ ERROR: {e}")
                print("Skipping remaining quarters for this user.")
                break # Exit the quarter loop for this user since the API request failed
                
            # Be nice to the API between quarters to avoid rate limiting
            time.sleep(2)
            
        print(f"\nFinished all downloads for {user}!")

if __name__ == "__main__":
    main()
