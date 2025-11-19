from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import time
import re
import pandas as pd
import traceback

# Initialize Flask, explicitly defining static and template folders
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

# ... rest of your code ...

# Helper function to normalize column names by stripping excess whitespace
def normalize_column_name(col_name):
    """Removes all internal whitespace from a string for robust column matching."""
    # Note: Use str.replace to handle various whitespace characters effectively
    return col_name.strip().replace(" ", "")

# --- 1. CONFIGURATION ---
# Get the absolute path of the directory containing app.py
# DEFINED HERE FOR CONFIGURATION USE
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) 
EXCEL_FILE_NAME = 'INGRES DATABASE.xlsx'
EXCEL_FILE_PATH = os.path.join(BASE_DIR, EXCEL_FILE_NAME) # <-- CRITICAL FIX: Use absolute path

# Define the specific sheets containing the raw data to be analyzed.
DATA_SHEET_NAMES = ['2025', '2024', '2023', '2022', '2020'] 

# Define the RAW column names, and then create their normalized versions for use in code.
# IMPORTANT: These must EXACTLY match the header names in your Excel sheets.
COL_STATE_RAW = 'State'  # <-- RENAMED from COL_UNIT_RAW for clarity
COL_DISTRICT_RAW = 'District' # <-- NEW: Column name for District/Assessment Unit
COL_CATEGORY_RAW = 'Categorization (OE/Critical/Semicritical/Safe)'
COL_EXTRACTION_RAW = 'Annual Extractable Ground Water Resource (Ham)'
COL_PERCENTAGE_RAW = 'Percentage' 

COL_STATE_NORM = normalize_column_name(COL_STATE_RAW) # <-- RENAMED from COL_UNIT_NORM
COL_DISTRICT_NORM = normalize_column_name(COL_DISTRICT_RAW) # <-- NEW
COL_CATEGORY_NORM = normalize_column_name(COL_CATEGORY_RAW)
COL_EXTRACTION_NORM = normalize_column_name(COL_EXTRACTION_RAW)
COL_PERCENTAGE_NORM = normalize_column_name(COL_PERCENTAGE_RAW)

# --- 2. Load Data ---
ingres_data_dict = {}
data_loaded = False
LOADED_YEARS = []
YEAR_REGEX_PATTERN = r'\b(2025|2024|2023|2022|2020)\b'
DEFAULT_YEAR = '2025'

try:
    # Load ONLY the specified data sheets, ignoring any new summary/pivot table sheets
    # Now using the absolute EXCEL_FILE_PATH
    ingres_data_dict_raw = pd.read_excel(EXCEL_FILE_PATH, sheet_name=DATA_SHEET_NAMES)
    
    # Normalize column names in all loaded DataFrames for robustness
    for year, df in ingres_data_dict_raw.items():
        # Clean column names
        df.columns = [normalize_column_name(col) for col in df.columns]
        ingres_data_dict[str(year)] = df # Ensure years are stored as strings for matching

    data_loaded = True
    LOADED_YEARS = list(ingres_data_dict.keys())
    # Dynamically build the regex pattern for year extraction
    YEAR_REGEX_PATTERN = r'\b(' + '|'.join(LOADED_YEARS) + r')\b' 
    DEFAULT_YEAR = LOADED_YEARS[0] if LOADED_YEARS else '2025'
    
    print(f"Data Loaded Successfully. Data Sheets found: {LOADED_YEARS}")
except FileNotFoundError:
    # The printed message now shows the full path it failed to find
    print(f"FATAL ERROR: Excel file expected at '{EXCEL_FILE_PATH}' not found. Data processing will fail.")
except Exception as e:
    print(f"FATAL ERROR: Could not load data. Ensure required columns exist. Error: {e}")


# --- 3. Chatbot Logic Functions (No change here) ---
# A. Simple Methodology FAQs 
faq_responses = {
    "what is ingres": "INGRES is the India Ground Water Resource Estimation System, a GIS-based platform developed by CGWB and IIT Hyderabad for groundwater assessment.",
    "categorization definition": "Groundwater units are categorized based on the ratio of annual extraction to recharge (e.g., Safe, Critical, Over Exploited).",
    "annual extractable resource": "This refers to the total volume of groundwater (in Ham) estimated to be available for withdrawal in a given year.",
    "who developed ingres": "INGRES was developed by the Central Ground Water Board (CGWB) in collaboration with IIT Hyderabad."
}

def get_faq_response(query):
    query_lower = query.lower()
    for keyword, response in faq_responses.items():
        if keyword in query_lower:
            return response
    return None

# B. Data Lookup Function (No change here)
# B. Data Lookup Function (UPDATED FOR DISTRICT SUPPORT)
def get_data_lookup_response(query):
    query_lower = query.lower()
    
    # --- i. Extract Year from Query ---
    year_match = re.search(YEAR_REGEX_PATTERN, query)
    target_year = year_match.group(0) if year_match else DEFAULT_YEAR
    
    if target_year not in ingres_data_dict:
        available_years = ', '.join(LOADED_YEARS)
        return f"I found the year {target_year} in your query, but I only have data for: {available_years}. Please try another year."

    target_df = ingres_data_dict[target_year]
    
    # --- ii. Determine Query Type (District or State) ---
    
    unit_name = None
    search_column_norm = None
    is_state_query = False
    
    # A. Check for District/Unit Match First (Prioritize specific units over broad states)
    if COL_DISTRICT_NORM in target_df.columns:
        # Dynamically get all unique district names from the current year's data
        all_districts = target_df[COL_DISTRICT_NORM].astype(str).str.strip().unique()
        
        # Find the longest matching district name in the query for better precision
        unit_name = next((d for d in sorted(all_districts, key=len, reverse=True) if d.lower() in query_lower), None)
        
        if unit_name:
            search_column_norm = COL_DISTRICT_NORM
            is_state_query = False # It's a district/unit lookup
            
    # B. Check for State Match (Fallback to existing state logic)
    if not unit_name:
        # Use the hardcoded list of known state names
        known_states = ["ANDAMAN AND NICOBAR ISLANDS" , "ANDHRA PRADESH" , "ARUNACHAL PRADESH" , "ASSAM" , "BIHAR" , "CHANDIGARH" , "CHHATTISGARH" , "DADRA AND NAGAR HAVELI" , "DAMAN AND DIU", "DELHI", "GOA", "GUJARAT" , "HARYANA" , "HIMACHAL PRADESH", "JAMMU AND KASHMIR" , "JHARKHAND" , "KARNATAKA" , "KERALA" , "LADAKH", "LAKSHDWEEP" , "MADHYA PRADESH", "MAHARASHTRA" , "MANIPUR", " MEGHALAYA " , "MIZORAM", "NAGALAND", "ODISHA" , "PUDUCHERRY" , "PUNJAB" ,"RAJASTHAN" , "SIKKIM", "TAMILNADU", "TELANGANA" , "TRIPURA" , "UTTAR PRADESH" , "UTTARAKHAND" , "WEST BENGAL", 'UP', 'MP', 'AP', 'TS' 
        ]
        
        # Find the longest matching state name
        unit_name = next((state for state in sorted(known_states, key=len, reverse=True) if state.lower() in query_lower), None)
        
        if unit_name:
            search_column_norm = COL_STATE_NORM
            is_state_query = True # It's a state lookup


    if not unit_name:
        # If neither State nor District is found, return the fallback message
        if "extraction" in query_lower or "percentage" in query_lower or "data" in query_lower:
            return "I can answer data queries, but please specify an **Indian State or District** and optionally a **Year**."
        
        # Final fallback
        return "I can only provide data on State or District-level groundwater categorization and general INGRES terminology. Please specify an Indian State or District."

    
    # --- iii. Perform the Lookup and AGGREGATION ---
    
    # 1. Filter the entire DataFrame for the State or District
    # Using a regex word boundary (\b) ensures precise matching for units like 'UP' or 'Mon'
    unit_data = target_df[target_df[search_column_norm].astype(str).str.contains(r'\b'+re.escape(unit_name)+r'\b', case=False, na=False, regex=True)]
    
    if unit_data.empty:
        return f"I could not find the unit '{unit_name.title()}' in the {target_year} sheet. Please check the spelling."

    # 2. Find Parent State (CRITICAL STEP for District lookups)
    parent_state = ""
    # Only execute if a District/Unit was queried AND the State column exists
    if not is_state_query and COL_STATE_NORM in target_df.columns:
        # Find the state name associated with the first row of the district data
        # Using .iloc[0] is safe since all rows in unit_data belong to the same district/unit, 
        # which in turn belongs to the same state.
        parent_state_raw = unit_data[COL_STATE_NORM].iloc[0]
        parent_state = f" (in {parent_state_raw.title()})"
        
    
    # 3. Extraction Calculation
    extraction_series = unit_data.get(COL_EXTRACTION_NORM)
    
    if extraction_series is None:
        total_extraction_str = f"Extraction Column Not Found (Expected: {COL_EXTRACTION_RAW})"
    else:
        numeric_extraction = pd.to_numeric(extraction_series, errors='coerce')
        total_extraction = numeric_extraction.sum()
        
        if total_extraction == 0 and numeric_extraction.isnull().all():
            total_extraction_str = "Data unavailable or zero"
        else:
            total_extraction_str = f"{total_extraction:,.2f}"
            
    # 4. Percentage Calculation
    percentage_series = unit_data.get(COL_PERCENTAGE_NORM)
    
    if percentage_series is None:
        avg_percentage_str = f"Percentage Column Not Found (Expected: {COL_PERCENTAGE_RAW})"
    else:
        numeric_percentage = pd.to_numeric(percentage_series, errors='coerce')
        # We average the percentage column for all units in the state/district
        avg_percentage = numeric_percentage.mean() 
        
        if pd.isna(avg_percentage):
            avg_percentage_str = "Data unavailable"
        else:
            # Format the percentage clearly 
            avg_percentage_str = f"{avg_percentage * 100:.2f}%"
            
    # 5. Determine overall status 
    statuses = unit_data.get(COL_CATEGORY_NORM).dropna().astype(str).unique()
    severity_order = ['Over Exploited', 'Critical', 'Semi Critical', 'Safe'] 
    
    overall_status = next((s for s in severity_order if any(s.lower() in status.lower() for status in statuses)), 'Mixed/Uncategorized')
    
    # --- iv. Format the Response ---
    
    # Determine the response title based on whether it's a State or District query
    unit_type = "District/Unit Summary" if not is_state_query else "State Summary"
    
    response = (
        f"**INGRES {unit_type} for {unit_name.title()}{parent_state} ({target_year}):**\n"
        f"• **Most Severe Groundwater Status:** {overall_status}\n"
        f"• **Average Extraction Percentage:** {avg_percentage_str}\n"
        f"• **TOTAL Annual Extractable Resource (Ham):** {total_extraction_str}\n"
        f"(Aggregated from {len(unit_data)} assessment units.)"
    )
    return response

# --- 4. Initialize Flask App and CORS ---

# The BASE_DIR definition was moved up to the configuration section (Section 1)

# Initialize Flask, explicitly setting the template and static folder paths
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# Explicitly enable CORS for all domains to allow the static frontend to connect
CORS(app, resources={r"/*": {"origins": "*"}}) 

# --- 5. Define the main Chat Endpoint (No change here) ---
@app.route('/chat', methods=['POST'])
def chat():
    # Simulate a small delay for better UX
    time.sleep(0.5) 
    
    if not data_loaded:
        # This should only happen if the file was missing on startup
        return jsonify({"response": "Error: INGRES data failed to load on the server. Check if 'INGRES DATABASE.xlsx' exists and is committed."}), 500

    try:
        # 1. Parse incoming JSON body
        # Note: Your frontend sends {'message': userMessage}, so we look for 'message'.
        if not request.json or 'message' not in request.json:
            # Check for invalid request format
            return jsonify({"response": "Invalid request format. Please send JSON with a 'message' key."}), 400
            
        user_query = request.json.get('message', '')
        
        # 2. Check for simple FAQs first
        response_text = get_faq_response(user_query)
        
        if response_text:
            return jsonify({"response": response_text})
        
        # 3. If no FAQ match, perform data lookup
        response_text = get_data_lookup_response(user_query)

        return jsonify({"response": response_text})

    # 🚨 CATCH ALL EXCEPTIONS TO RETURN THE PYTHON ERROR 🚨
    except Exception as e:
        user_query = request.json.get('message', 'N/A')
        error_trace = traceback.format_exc()
        # Log the error on the server
        print(f"FATAL API ERROR (Query: {user_query}): {error_trace}")
        
        # Return the error message to the frontend for debugging
        return jsonify({
            "response": f"FATAL BACKEND ERROR: A critical Python error occurred. Details: {e}",
            "details": error_trace
        }), 500


# --- 6. Define the Home Route (UPDATED TO SERVE FRONTEND) ---
@app.route('/', methods=['GET'])
def home():
    # Render the index.html file from the 'templates' folder
    return render_template('index.html')


# --- 7. Run the Server ---
if __name__ == '__main__':
    print("Starting Flask server for JIVA...")
    # Use the port provided by the hosting environment, default to 5000 locally
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
