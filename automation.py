import logging
from playwright.sync_api import sync_playwright
import pandas as pd
import os
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configure logging to output debug messages to the terminal
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Set up argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('--invoice-date', type=str, required=True, help="Invoice date in MM-DD format")
parser.add_argument('--screenshot', action='store_true', help="Take a screenshot during automation")
parser.add_argument('--row-replacement', type=str, default="Personalize Defter", help="Row replacement value")
parser.add_argument('--input-csv', type=str, required=True, help="Path to the filtered CSV file to process")
parser.add_argument('--date-file', type=str, help="Path to file for dynamic date updates")
args = parser.parse_args()

invoice_date = args.invoice_date
take_screenshot = args.screenshot
row_replacement = args.row_replacement
input_csv = args.input_csv
date_file = args.date_file

# Get credentials from environment variables
NES_USERNAME = os.getenv('NES_USERNAME')
NES_PASSWORD = os.getenv('NES_PASSWORD')

if not NES_USERNAME or not NES_PASSWORD:
    logging.error("NES_USERNAME and NES_PASSWORD environment variables must be set.")
    exit(1)

# Country mapping dictionary (English to Turkish)
COUNTRY_MAPPING = {
    'United States': 'Amerika Birleşik Devletleri',
    'Canada': 'Kanada',
    'United Kingdom': 'Birleşik Krallık',
    'Australia': 'Avustralya',
    'France': 'Fransa',
    'Germany': 'Almanya',
    'Italy': 'İtalya',
    'Spain': 'İspanya',
    'Ireland': 'İrlanda',
    'Netherlands': 'Hollanda',
    'Belgium': 'Belçika',
    'Switzerland': 'İsviçre',
    'Austria': 'Avusturya',
    'Sweden': 'İsveç',
    'Norway': 'Norveç',
    'Denmark': 'Danimarka',
    'Finland': 'Finlandiya',
    'Portugal': 'Portekiz',
    'Greece': 'Yunanistan',
    'Poland': 'Polonya',
    'Czech Republic': 'Çek Cumhuriyeti',
    'Hungary': 'Macaristan',
    'Slovakia': 'Slovakya',
    'Slovenia': 'Slovenya',
    'Croatia': 'Hırvatistan',
    'Romania': 'Romanya',
    'Bulgaria': 'Bulgaristan',
    'Russia': 'Rusya',
    'Ukraine': 'Ukrayna',
    'Turkey': 'Türkiye',
    'Israel': 'İsrail',
    'Saudi Arabia': 'Suudi Arabistan',
    'United Arab Emirates': 'Birleşik Arap Emirlikleri',
    'Japan': 'Japonya',
    'China': 'Çin',
    'South Korea': 'Güney Kore',
    'India': 'Hindistan',
    'Brazil': 'Brezilya',
    'Mexico': 'Meksika',
    'Argentina': 'Arjantin',
    'South Africa': 'Güney Afrika'
}

def get_turkish_country(english_country):
    return COUNTRY_MAPPING.get(english_country, english_country)

def get_current_date():
    """Get the current invoice date, either from date file or command line argument"""
    if date_file and Path(date_file).exists():
        try:
            with open(date_file, 'r') as f:
                data = json.load(f)
                return data.get('invoice_date', invoice_date)
        except:
            pass
    return invoice_date

def process_orders():
    logging.debug(f"Reading CSV file: {input_csv}")
    df = pd.read_csv(input_csv)
    
    # Generate a unique directory name based on the current timestamp
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_screenshots_dir = 'screenshots'
    run_screenshots_dir = os.path.join(base_screenshots_dir, run_timestamp)

    # Create the base and run-specific screenshot directories
    try:
        os.makedirs(run_screenshots_dir, exist_ok=True)
        logging.debug(f"Screenshots for this run will be saved in: {run_screenshots_dir}")
    except OSError as e:
        logging.error(f"Failed to create screenshot directory {run_screenshots_dir}: {e}")
        # Decide if you want to exit or continue without screenshots
        # For now, let's exit if we can't create the directory
        return

    successful_orders = 0 # Counter for successfully processed orders

    with sync_playwright() as p:
        logging.debug("Launching Chromium browser in headless mode")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # Set a generous default timeout (30 seconds)
        page.set_default_timeout(30000)
        
        try:
            for index, row in df.iterrows():
                try:
                    current_date = get_current_date()  # Get potentially updated date
                    logging.debug(f"Processing order {index + 1} of {len(df)}: {row['Order ID']} with date {current_date}")
                    
                    # NAVIGATE
                    logging.debug("Navigating to invoice editor URL")
                    page.goto('https://portal.nes.com.tr/invoice/editor/general', wait_until='networkidle')
                    page.wait_for_load_state('domcontentloaded')
                    
                    # LOGIN (if needed)
                    login_selector = 'input[placeholder="Kullanıcı Adı"]'
                    login_input = page.query_selector(login_selector)
                    if login_input and login_input.is_visible():
                        logging.debug("Login screen detected, performing login")
                        page.locator(login_selector).fill(NES_USERNAME)
                        page.locator('input[placeholder="Parola"]').fill(NES_PASSWORD)
                        login_button = page.get_by_role('button', name='Giriş')
                        page.wait_for_selector('button:has-text("Giriş")', state='visible')
                        login_button.click()
                        page.wait_for_load_state('networkidle')
                    else:
                        logging.debug("Already logged in, skipping login step")
                    
                    # FILL CUSTOMER FORM
                    logging.debug("Filling customer form")
                    customer_selector = '#rc_select_3'
                    page.wait_for_selector(customer_selector, state='visible').click()
                    page.locator(customer_selector).fill('2222222222')
                    page.wait_for_function("() => document.querySelector('#rc_select_3').value === '2222222222'")
                    
                    # Close any popup from the customer form
                    target_selector = (
                        ".d-flex > .ant-form > div > div:nth-child(2) > div > div > "
                        ".ant-row > div:nth-child(2) > .ant-form-item-control-input > "
                        ".ant-form-item-control-input-content > .ant-input-affix-wrapper"
                    )
                    page.wait_for_selector(target_selector, state='visible')
                    page.locator(target_selector).first.click()
                    
                    close_button = page.get_by_label("Close", exact=True)
                    page.wait_for_selector('button[aria-label="Close"]', state='visible')
                    close_button.click()
                    page.wait_for_selector('button[aria-label="Close"]', state='hidden')
                    
                    # FILL CUSTOMER INFORMATION (Name, Address, etc.)
                    logging.debug("Handling customer name field with popup handling if needed")
                    name_selector = '[id="accountingCustomerPartyForm_party\\.partyName\\.name"]'
                    page.wait_for_selector(name_selector, state='visible')
                    page.locator(name_selector).click()
                    if page.locator('.show').is_visible():
                        logging.debug("Popup detected, closing it")
                        page.get_by_label('Close', exact=True).click()
                        page.wait_for_function("() => !document.querySelector('.show')")
                    page.locator(name_selector).click()
                    logging.debug(f"Filling customer name with value: {row['Full Name']}")
                    page.locator(name_selector).fill(row['Full Name'])
                    page.wait_for_function(f"() => document.querySelector('{name_selector}').value === '{row['Full Name']}'")
                    
                    logging.debug("Filling customer address information")
                    street = f"{row['Street 1']} {row['Street 2']}" if pd.notna(row['Street 2']) else row['Street 1']
                    street_selector = '[id="accountingCustomerPartyForm_party\\.postalAddress\\.streetName"]'
                    page.locator(street_selector).fill(street)
                    page.wait_for_function(f"() => document.querySelector('{street_selector}').value === '{street}'")
                    
                    logging.debug("Filling customer city")
                    city_selector = '[id="accountingCustomerPartyForm_party\\.postalAddress\\.citySubdivisionName\\.value"]'
                    page.locator(city_selector).fill(row['Ship City'])
                    page.wait_for_function(f"() => document.querySelector('{city_selector}').value === '{row['Ship City']}'")
                    
                    logging.debug("Filling customer state/county")
                    state_value = str(row['Ship State']) if pd.notna(row['Ship State']) else str(row['Ship City'])
                    state_selector = '[id="accountingCustomerPartyForm_party\\.postalAddress\\.cityName\\.value"]'
                    page.locator(state_selector).fill(state_value)
                    page.wait_for_function(f"() => document.querySelector('{state_selector}').value === '{state_value}'")
                    
                    logging.debug("Filling customer country")
                    turkish_country = get_turkish_country(row['Ship Country'])
                    country_selector = '[id="accountingCustomerPartyForm_party\\.postalAddress\\.country\\.name\\.value"]'
                    page.locator(country_selector).fill(turkish_country)
                    page.wait_for_selector(f"{country_selector}[value='{turkish_country}']", state="visible")
                    
                    # HANDLE DATE & CURRENCY
                    logging.debug("Setting invoice date")
                    # Invoice date: wait for the field, scroll into view, then click to open picker.
                    invoice_date_locator = page.get_by_label("Düzenleme Tarihi")
                    try:
                        invoice_date_locator.wait_for(state="visible", timeout=45000)
                    except Exception as e:
                        html_snippet = page.content()[:500]
                        logging.error("Invoice date field did not become visible. Page snippet:\n" + html_snippet)
                        raise e
                    invoice_date_locator.evaluate("el => el.scrollIntoView()")
                    invoice_date_locator.click()
                    
                    # Wait for the date picker panel to appear
                    page.wait_for_selector(".ant-picker-panel", state="visible", timeout=15000)
                    
                    # Extract day and remove leading zero if present (e.g., "09" becomes "9")
                    day = str(int(current_date.split('-')[1]))
                    
                    # Find the date cell that matches our day number
                    date_cells = page.locator(".ant-picker-cell-inner")
                    for i in range(date_cells.count()):
                        cell = date_cells.nth(i)
                        if cell.text_content().strip() == day:
                            cell.click()
                            break
                    
                    # Wait until the panel closes
                    page.wait_for_selector(".ant-picker-panel", state="hidden", timeout=15000)
                    
                    logging.debug("Switching currency from Türk Lirası to Amerikan Doları")
                    try:
                        # Click the currency dropdown using a more specific selector
                        currency_button = page.locator('.ant-select-selection-item').get_by_text('Türk Lirası')
                        currency_button.wait_for(state="visible", timeout=15000)
                        currency_button.evaluate("el => el.scrollIntoView()")
                        currency_button.click()
                        
                        # Fill the search input
                        currency_input = page.get_by_label("Para Birimi")
                        currency_input.wait_for(state="visible", timeout=15000)
                        currency_input.evaluate("el => el.scrollIntoView()")
                        currency_input.fill("amerikan doları")
                        
                        # Wait for dropdown options to appear
                        page.wait_for_selector(".ant-select-dropdown:visible", state="visible", timeout=15000)
                        
                        # Use a more specific selector for the USD option in the dropdown
                        usd_option = page.locator('.ant-select-item-option-content').get_by_text("Amerikan Doları")
                        usd_option.wait_for(state="visible", timeout=15000)
                        usd_option.evaluate("el => el.scrollIntoView()")
                        usd_option.click()
                        
                        # Wait for dropdown to close
                        page.wait_for_selector(".ant-select-dropdown", state="hidden", timeout=15000)
                        
                        # Verify the currency was actually changed using a specific selector
                        selected_currency = page.locator('.ant-select-selection-item').get_by_text("Amerikan Doları")
                        selected_currency.wait_for(state="visible", timeout=15000)
                        logging.debug("Successfully switched currency to Amerikan Doları")
                    except Exception as e:
                        logging.error(f"Failed to switch currency: {str(e)}")
                        # Take a screenshot of the failure state
                        page.screenshot(path="currency_switch_error.png")
                        raise e
                    
                    logging.debug("Filling exchange rate")
                    exchange_rate_input = page.locator('form').filter(has_text='Düzenleme TarihiDüzenleme').locator('input[type="text"]')
                    exchange_rate_str = str(row['Exchange_Rate'])
                    exchange_rate_input.fill(exchange_rate_str)
                    
                    
                    logging.debug("Selecting invoice type: switching from Kağıt to Elektronik")
                    page.get_by_text("Kağıt").evaluate("el => el.scrollIntoView()")
                    page.get_by_text("Kağıt").click()
            
                    page.get_by_text("Elektronik", exact=True).click()
                    
                    logging.debug("Adding order item")
                    add_item_button = page.get_by_role('button', name='Mal/Hizmet Ekle')
                    add_item_button.evaluate("el => el.scrollIntoView()")
                    add_item_button.click()
                    
                    page.locator('#rc_select_14').click()
                    
                    page.locator('#rc_select_14').fill(row_replacement)
                    
                    logging.debug("Filling order value")
                    order_value = str(row['Order Value']).replace(',', '').replace('$', '')
                    value_selector = ("td:nth-child(5) > .ant-row > .ant-col > "
                                      ".ant-form-item-control-input > .ant-form-item-control-input-content > .ant-input")
                    page.locator(value_selector).fill(order_value)
                    page.wait_for_timeout(1000) #################################################################
                    
                    if pd.notna(row['Discount Amount']) and float(str(row['Discount Amount']).replace('$', '').replace(',', '')) > 0:
                        discount_value = str(row['Discount Amount']).replace('$', '').replace(',', '')
                        discount_selector = "td:nth-child(7) > .ant-input"
                        logging.debug("Filling discount amount")
                        page.locator(discount_selector).fill(discount_value)
                        page.wait_for_function(f"() => document.querySelector('{discount_selector}').value === '{discount_value}'")
                    
                    logging.debug("Adding shipping item (if needed)")
                    shipping_value = str(row['Shipping']).replace('$', '').replace(',', '') if pd.notna(row['Shipping']) else '0'
                    if float(shipping_value) > 0:
                        add_item_button.click()
                        
                        page.locator('#rc_select_17').click()
                        
                        page.locator('#rc_select_17').fill('Kargo Bedeli')
                        
                        
                        shipping_value_selector = "td:nth-child(5) .ant-input"
                        page.wait_for_function(
                            """() => document.querySelectorAll("td:nth-child(5) .ant-input").length >= 2""",
                            timeout=15000
                        )
                        price_inputs = page.locator(shipping_value_selector).all()
                        if len(price_inputs) >= 2:
                            logging.debug("Filling shipping amount")
                            price_inputs[1].fill(shipping_value)
                            page.wait_for_timeout(1000) #################################################################

                            page.wait_for_function(f"() => document.querySelectorAll('{shipping_value_selector}')[1].value === '{shipping_value}'")
                        else:
                            logging.warning("Warning: Could not find second price input for shipping")
                    
                    logging.debug("Opening preview")
                    preview_button = page.get_by_role('button', name='Görüntüle')
                    preview_button.evaluate("el => el.scrollIntoView()")
                    page.wait_for_selector('button:has-text("Görüntüle")', state='visible', timeout=15000)
                    preview_button.click()
                    
                    logging.debug("Selecting first dropdown option")
                    first_dropdown = page.get_by_text('Seçiniz...').first
                    first_dropdown.wait_for(state="visible", timeout=15000)
                    first_dropdown.evaluate("el => el.scrollIntoView()")
                    first_dropdown.click()
                    first_option = page.get_by_text('- 351 - İstisna Olmayan Diğer').first
                    first_option.evaluate("el => el.scrollIntoView()")
                    first_option.click()
                    
                    if float(shipping_value) > 0:
                        logging.debug("Selecting second dropdown option for shipping")
                        second_dropdown = page.get_by_label('Fatura Bilgileri').get_by_text('Seçiniz...')
                        second_dropdown.wait_for(state="visible", timeout=15000)
                        second_dropdown.evaluate("el => el.scrollIntoView()")
                        second_dropdown.click()
                        second_option = page.get_by_text('- 351 - İstisna Olmayan Diğer').nth(2)
                        second_option.evaluate("el => el.scrollIntoView()")
                        second_option.click()
                    
                    logging.debug("Waiting for order completion indicator")
                    
                    logging.debug("Reopening preview for final screenshot")
                    preview_button.click()
                    page.wait_for_selector('.ant-modal-content', state='visible', timeout=15000)
                    preview_modal = page.locator('.ant-modal-content')
                    if preview_modal.is_visible():
                        # Use the run-specific directory
                        screenshot_path = os.path.join(run_screenshots_dir, f"preview_{row['Order ID']}.png")
                        preview_modal.screenshot(path=screenshot_path)
                        logging.debug(f"Preview screenshot saved: {screenshot_path}")
                    
                    logging.debug("Closing preview modal")
                    close_button = page.get_by_role('button', name='Kapat')
                    close_button.wait_for(state="visible", timeout=15000)
                    close_button.evaluate("el => el.scrollIntoView()")
                    close_button.click()
                    
                    logging.debug("Saving invoice as draft")
                    save_draft_button = page.get_by_role("button", name="Taslak Olarak Kaydet")
                    save_draft_button.wait_for(state="visible", timeout=15000)
                    save_draft_button.evaluate("el => el.scrollIntoView()")
                    save_draft_button.click()
                    page.wait_for_timeout(2000)
                    
                    logging.info(f"Successfully processed order {row['Order ID']}")
                    successful_orders += 1 # Increment counter on success
                    
                    # Wait for the form to be ready for the next order
                    page.wait_for_selector(customer_selector, state='visible', timeout=15000)
                
                except Exception as e:
                    logging.error(f"Error processing order {row['Order ID']}: {str(e)}")
                    try:
                        # Save error screenshot to the run-specific directory
                        error_screenshot_path = os.path.join(run_screenshots_dir, f"error_{row['Order ID']}.png")
                        page.screenshot(path=error_screenshot_path)
                        logging.debug(f"Error screenshot saved as {error_screenshot_path}")
                    except Exception as e2:
                        logging.error("Failed to take error screenshot: " + str(e2))
                    try:
                        page.reload()
                        page.wait_for_selector(customer_selector, state='visible', timeout=15000)
                    except Exception as e3:
                        logging.error("Failed to reload page: " + str(e3))
                    continue
                
        except Exception as e:
            logging.critical(f"An error occurred: {e}")
        finally:
            # Report based on the counter, not file system count
            logging.info(f"Processing finished. Successfully processed orders: {successful_orders} out of {len(df)}")
            logging.debug("Closing browser")
            browser.close()

if __name__ == '__main__':
    process_orders()
