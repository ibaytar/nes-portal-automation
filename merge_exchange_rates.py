import pandas as pd
import glob
import os

def find_files():
    """
    Look for CSV files to process using both direct filenames and pattern matching
    """
    # First check for the renamed files from the web app
    order_file = "EtsyOrders.csv"
    payment_file = "ExchangeRates.csv"
    
    # If the renamed files exist, use them
    if os.path.exists(order_file) and os.path.exists(payment_file):
        print(f"Using uploaded files: {order_file} and {payment_file}")
        return payment_file, order_file
    
    # Otherwise, look for files matching the original patterns
    payment_files = glob.glob('EtsyDirectCheckoutPayments*.csv')
    order_files = glob.glob('EtsySoldOrders*.csv')
    
    # Check if files exist before trying to find the latest
    if not payment_files:
        raise FileNotFoundError("No payment files found matching 'EtsyDirectCheckoutPayments*.csv' and no 'ExchangeRates.csv' file found. Please ensure you've uploaded the files correctly.")
    
    if not order_files:
        raise FileNotFoundError("No order files found matching 'EtsySoldOrders*.csv' and no 'EtsyOrders.csv' file found. Please ensure you've uploaded the files correctly.")
    
    # Get the most recently modified files
    latest_payment = max(payment_files, key=os.path.getctime)
    latest_order = max(order_files, key=os.path.getctime)
    
    print(f"Using latest files: {latest_payment} and {latest_order}")
    return latest_payment, latest_order

def merge_exchange_rates():
    # Get the input files
    payment_file, order_file = find_files()
    
    # Read the CSV files
    payments_df = pd.read_csv(payment_file)
    orders_df = pd.read_csv(order_file)
    
    # Create a mapping of Order ID to Exchange Rate from payments
    exchange_rates = payments_df[['Order ID', 'Exchange Rate']].copy()
    exchange_rates = exchange_rates.rename(columns={'Exchange Rate': 'Exchange_Rate'})
    
    # Merge the exchange rates with orders
    merged_df = pd.merge(
        orders_df,
        exchange_rates,
        on='Order ID',
        how='left'
    )
    
    # Generate output filename using current month
    current_month = pd.Timestamp.now().strftime("%m")
    output_filename = f'EtsyOrders_with_ExchangeRates_{current_month}.csv'
    
    # Save the merged dataframe
    merged_df.to_csv(output_filename, index=False)
    print(f"Created new file: {output_filename}")
    print(f"Total orders processed: {len(merged_df)}")
    print(f"Orders with exchange rates: {merged_df['Exchange_Rate'].notna().sum()}")

if __name__ == '__main__':
    merge_exchange_rates()
