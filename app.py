import streamlit as st
import pandas as pd
import os
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from datetime import datetime, timedelta
import subprocess
import json

# Set page config for wide mode and hide sidebar by default
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# Initialize session state for authentication and data
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'name' not in st.session_state:
    st.session_state['name'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None
if 'show_controls' not in st.session_state:
    st.session_state['show_controls'] = False
if 'auto_mode' not in st.session_state:
    st.session_state['auto_mode'] = False
if 'date_distribution' not in st.session_state:
    st.session_state['date_distribution'] = None
if 'current_processing_date' not in st.session_state:
    st.session_state['current_processing_date'] = None
if 'orders_processed_today' not in st.session_state:
    st.session_state['orders_processed_today'] = 0

# Load configuration for authentication
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# --- Add this line for debugging ---
print("DEBUG: Loaded config:", config)
# ----------------------------------

# Create the authenticator
authenticator = stauth.Authenticate(
    credentials=config['credentials'],
    cookie_name=config['cookie']['name'],
    cookie_expiry_days=config['cookie']['expiry_days'],
    cookie_key=config['cookie']['key']
)

# Add login to sidebar
st.sidebar.title("Login")
authenticator.login(fields={'Form name': 'Login Form'})

if st.session_state['authentication_status']:
    authenticator.logout('Logout')
    st.write(f'Welcome *{st.session_state["name"]}*')
    
    st.title('NES Portal Invoice Generator')
    
    # Create two columns for CSV uploads
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload Orders CSV")
        orders_csv = st.file_uploader("Choose orders CSV file", type='csv', key='orders')
    
    with col2:
        st.subheader("Upload Exchange Rates CSV")
        rates_csv = st.file_uploader("Choose exchange rates CSV file", type='csv', key='rates')
    
    # Process button for merging CSVs
    if orders_csv is not None and rates_csv is not None:
        if st.button('Process CSVs', type="primary"):
            # Save the uploaded files
            orders_path = "EtsyOrders.csv"
            rates_path = "ExchangeRates.csv"
            
            with open(orders_path, "wb") as f:
                f.write(orders_csv.getbuffer())
            with open(rates_path, "wb") as f:
                f.write(rates_csv.getbuffer())
            
            # Call merge_exchange_rates.py
            try:
                subprocess.run(['python', 'merge_exchange_rates.py'], check=True)
                st.success("Files processed successfully!")
                
                # Get current month for the output file
                current_month = datetime.now().strftime("%m")
                output_file = f'EtsyOrders_with_ExchangeRates_{current_month}.csv'
                
                # Check for the output file and load it
                if os.path.exists(output_file):
                    # Read the CSV and convert date column
                    df = pd.read_csv(output_file)
                    df['Date'] = pd.to_datetime(df['Sale Date'], format='%m/%d/%y')
                    st.session_state['processed_data'] = df
                    st.session_state['show_controls'] = True
                else:
                    st.error(f"Output file {output_file} not found!")
            except subprocess.CalledProcessError as e:
                st.error(f"Error processing files: {str(e)}")
            except FileNotFoundError as e:
                st.error(f"File not found: {str(e)}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
    
    # Show data filtering and automation controls if we have processed data
    if st.session_state['show_controls'] and st.session_state['processed_data'] is not None:
        st.markdown("---")  # Add a separator
        left_col, right_col = st.columns(2)
        
        with left_col:
            st.subheader("Date Range Selection")
            
            # Get min and max dates from the data
            min_date = st.session_state['processed_data']['Date'].min()
            max_date = st.session_state['processed_data']['Date'].max()
            
            # Create two date pickers in a flex container
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                start_date = st.date_input(
                    "Start Date",
                    value=min_date,
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                    key='start_date',
                    disabled=st.session_state.get('auto_mode', False)
                )
            with date_col2:
                end_date = st.date_input(
                    "End Date",
                    value=max_date,
                    min_value=start_date,
                    max_value=max_date.date(),
                    key='end_date',
                    disabled=st.session_state.get('auto_mode', False)
                )
            
            # Filter and display data based on date range
            mask = (st.session_state['processed_data']['Date'].dt.date >= start_date) & \
                   (st.session_state['processed_data']['Date'].dt.date <= end_date)
            filtered_data = st.session_state['processed_data'][mask]
            
            # Display filtered data with specific columns
            if not filtered_data.empty:
                st.write(f"Showing {len(filtered_data)} orders between {start_date} and {end_date}")
                display_columns = ['Date', 'Order ID', 'Full Name', 'Ship Country', 'Order Value']
                st.dataframe(filtered_data[display_columns], use_container_width=True, height=400)
                
                # Save filtered data to a temporary CSV
                filtered_csv_path = "filtered_orders.csv"
                filtered_data.to_csv(filtered_csv_path, index=False)
            else:
                st.warning("No orders found in the selected date range")
        
        with right_col:
            st.subheader("Automation Controls")
            
            # 1. Dropdown for row replacement
            row_replacement = st.selectbox(
                "Row yerine yazılacak",
                options=["Personalize Defter", "Fular"],
                key='row_replacement'
            )
            
            # 2. Invoice start date picker and Screenshot checkbox in the same row
            col1, col2, col3 = st.columns(3)
            
            with col1:
                invoice_date = st.date_input(
                    "Fatura kesim başlangıç",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key='invoice_date',
                    disabled=st.session_state.get('auto_mode', False)
                )
            
            with col2:
                take_screenshot = st.checkbox("Ekran Görüntüsü al?", value=True, key='screenshot')
            
            with col3:
                auto_mode = st.checkbox("Auto Mode", key='auto_mode', value=st.session_state.get('auto_mode', False))

            # If auto mode is enabled, calculate date distribution
            if auto_mode:
                # Calculate auto mode dates based on today
                auto_today = datetime.now().date()
                auto_max_date = auto_today
                auto_min_date = auto_today - timedelta(days=7)
                
                total_orders = len(filtered_data)
                days_between = (auto_max_date - auto_min_date).days + 1
                
                # Calculate even distribution with ceiling
                base_orders_per_day = total_orders // days_between
                if total_orders % days_between > 0:
                    base_orders_per_day += 1
                
                # Create a dictionary to store orders per date
                date_distribution = {}
                current_date = auto_min_date
                remaining_orders = total_orders
                
                # Distribute orders evenly
                while current_date <= auto_max_date and remaining_orders > 0:
                    if current_date == auto_max_date or remaining_orders <= base_orders_per_day:
                        # On last day or if we have fewer orders than base_orders_per_day
                        date_distribution[current_date] = remaining_orders
                    else:
                        date_distribution[current_date] = base_orders_per_day
                    remaining_orders -= date_distribution[current_date]
                    current_date += timedelta(days=1)

                # Store the distribution in session state for use during processing
                st.session_state['date_distribution'] = date_distribution
                st.session_state['current_processing_date'] = auto_min_date
                st.session_state['orders_processed_today'] = 0

                # Show the distribution plan
                st.write("Auto Mode Distribution Plan:")
                for date, count in date_distribution.items():
                    st.write(f"{date.strftime('%d.%m')}: {count} orders")
            
            # 4. Start button
            if st.button("Başla", type="primary", key='start_button'):
                if len(filtered_data) > 0:
                    try:
                        # Setup progress bar, status text, and log container
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Create a collapsible debug section
                        with st.expander("Debug Log", expanded=False):
                            log_container = st.empty()
                        
                        log_lines = []
                        total_orders = len(filtered_data)
                        processed_orders = 0

                        # Prepare command line arguments for automation.py
                        date_file = "current_date.json"
                        cmd = ['python', 'automation.py']
                        if take_screenshot:
                            cmd.append('--screenshot')
                        if row_replacement:
                            cmd.extend(['--row-replacement', row_replacement])
                        
                        # Handle invoice date based on mode
                        if auto_mode:
                            # Start with auto_min_date in auto mode
                            formatted_date = f"{auto_min_date.month:02d}-{auto_min_date.day:02d}"
                            # Create initial date file
                            with open(date_file, 'w') as f:
                                json.dump({'invoice_date': formatted_date}, f)
                            cmd.extend(['--date-file', date_file])
                        else:
                            # Use selected invoice_date in manual mode
                            formatted_date = invoice_date.strftime('%m-%d')
                            month, day = formatted_date.split('-')
                            formatted_date = f"{int(month):02d}-{int(day):02d}"
                        
                        cmd.extend(['--invoice-date', formatted_date])
                        cmd.extend(['--input-csv', filtered_csv_path])

                        # Initialize counter for current task
                        current_task = 0
                        
                        # Create and start the subprocess
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1
                        )

                        # Process output in real time
                        if process.stdout:
                            for line in process.stdout:
                                # Only update status if we haven't processed all tasks
                                if current_task < total_orders:
                                    current_customer = filtered_data.iloc[current_task]
                                    
                                    if auto_mode:
                                        # Get current processing date and orders for today
                                        current_date = st.session_state['current_processing_date']
                                        orders_today = st.session_state['orders_processed_today']
                                        max_orders_today = st.session_state['date_distribution'][current_date]
                                        
                                        # Update orders processed for today
                                        if "Successfully processed" in line:
                                            current_task += 1
                                            st.session_state['orders_processed_today'] += 1
                                            orders_today = st.session_state['orders_processed_today']
                                            
                                            # If we've processed all orders for today, move to next day
                                            if orders_today >= max_orders_today and current_date < auto_max_date:
                                                # Move to next day
                                                current_date += timedelta(days=1)
                                                st.session_state['current_processing_date'] = current_date
                                                st.session_state['orders_processed_today'] = 0
                                                
                                                # Update the date file
                                                formatted_date = f"{current_date.month:02d}-{current_date.day:02d}"
                                                with open(date_file, 'w') as f:
                                                    json.dump({'invoice_date': formatted_date}, f)
                                            
                                            progress_bar.progress(min(current_task / total_orders, 1.0))
                                        
                                        status_text.info(f"{current_customer['Full Name']}, {current_task + 1}/{total_orders}, {current_customer['Order ID']} (Date: {current_date.strftime('%d.%m')})")
                                    else:
                                        if "Successfully processed" in line:
                                            current_task += 1
                                            progress_bar.progress(min(current_task / total_orders, 1.0))
                                        status_text.info(f"{current_customer['Full Name']}, {current_task + 1}/{total_orders}, {current_customer['Order ID']}")

                                # Update log container
                                log_lines.append(line)
                                log_container.text("".join(log_lines))
                                
                                # Check if all orders are processed
                                if current_task >= total_orders:
                                    progress_bar.progress(1.0)
                                    
                                    # Create notification container at the top of the page
                                    notification_placeholder = st.empty()
                                    with notification_placeholder.container():
                                        col1, col2 = st.columns([3,1])
                                        with col1:
                                            st.success(f"🎉 All {total_orders} orders have been successfully processed!")
                                        with col2:
                                            if st.button("Clear"):
                                                notification_placeholder.empty()
                                    
                                    # Show detailed completion info
                                    completion_info = st.container()
                                    with completion_info:
                                        if auto_mode:
                                            st.markdown("### 📊 Auto Mode Summary")
                                            st.markdown("**Orders processed by date:**")
                                            for date, count in date_distribution.items():
                                                st.markdown(f"- **{date.strftime('%d.%m')}**: {count} orders")
                                        else:
                                            st.markdown("### ✅ Manual Mode Summary")
                                            st.markdown(f"**Date**: {invoice_date.strftime('%d.%m')}")
                                            st.markdown(f"**Total Orders**: {total_orders}")
                                        
                                        st.balloons()  # Add celebratory balloons animation
                    except Exception as e:
                        st.error(f"Error running automation: {str(e)}")
                else:
                    st.error("Please select a date range with orders before starting automation")

elif st.session_state['authentication_status'] == False:
    st.error('Username/password is incorrect')
elif st.session_state['authentication_status'] is None:
    st.warning('Please enter your username and password')
