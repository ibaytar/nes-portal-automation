import pandas as pd
import glob
import os

def find_latest_files():
    # Find the latest payment and order files
    payment_files = glob.glob('EtsyDirectCheckoutPayments*.csv')
    order_files = glob.glob('EtsySoldOrders*.csv')
    
    latest_payment = max(payment_files, key=os.path.getctime)
    latest_order = max(order_files, key=os.path.getctime)
    
    return latest_payment, latest_order

def merge_exchange_rates():
    # Get the latest files
    payment_file, order_file = find_latest_files()
    
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
