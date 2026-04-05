"""
ReserveShift Tracker
A real-time dashboard to monitor global reserve shifts and the Dollar Dependency Index (DDI).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json
from datetime import datetime, timedelta
import time
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="ReserveShift Tracker",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Helper Functions for Data Fetching ---

@st.cache_data(ttl=86400)  # Cache data for 1 day
def fetch_gold_data():
    """
    Fetches central bank gold purchase data from the World Gold Council.
    Data Source: World Gold Council
    """
    # URL for the latest World Gold Council data in CSV format
    url = "https://www.gold.org/download/file/7860/gold_reserves_by_country_csv"
    
    try:
        df = pd.read_csv(url, skiprows=2)  # Skip the header rows
        # Clean and rename columns for our use
        df = df[['Country', 'Gold Tonnes']]
        df.columns = ['Country', 'Gold Tonnes']
        df['Gold Tonnes'] = pd.to_numeric(df['Gold Tonnes'], errors='coerce')
        df = df.dropna()
        # Calculate monthly change (mock for demonstration, in a real scenario you'd compare with historical data)
        df['Monthly Change'] = df['Gold Tonnes'].pct_change().fillna(0) * 100
        return df
    except Exception as e:
        st.error(f"Error fetching gold data: {e}")
        # Return mock data as fallback
        return pd.DataFrame({
            'Country': ['USA', 'Germany', 'Italy', 'France', 'Russia', 'China', 'India'],
            'Gold Tonnes': [8133.5, 3355.1, 2451.8, 2436.9, 2298.5, 1948.3, 653.6],
            'Monthly Change': [0, -0.1, 0, 0, 0.5, 0.2, 0]
        })

@st.cache_data(ttl=86400)
def fetch_reserve_data():
    """
    Fetches currency composition of official foreign exchange reserves (COFER) from the IMF.
    Data Source: IMF Data Portal
    """
    # URL for the IMF COFER dataset in JSON format
    url = "http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/COFER/AR.A....?startPeriod=2020&endPeriod=2025"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Parse the JSON response to extract currency shares
        # This is a simplified parser; the actual IMF JSON structure is more complex
        records = []
        for obs in data.get('CompactData', {}).get('DataSet', {}).get('Series', []):
            currency = obs.get('@CURRENCY')
            for val in obs.get('Obs', []):
                time_period = val.get('@TIME_PERIOD')
                value = val.get('@OBS_VALUE')
                if currency and time_period and value:
                    records.append({
                        'Date': time_period,
                        'Currency': currency,
                        'Share': float(value)
                    })
        
        df = pd.DataFrame(records)
        if df.empty:
            raise ValueError("No data found")
        
        # Pivot to have currencies as columns
        df_pivot = df.pivot(index='Date', columns='Currency', values='Share').reset_index()
        return df_pivot
    except Exception as e:
        st.error(f"Error fetching reserve data: {e}. Using fallback data.")
        # Return mock data as fallback
        dates = pd.date_range(start='2020-01-01', periods=20, freq='QE')
        data = {
            'Date': dates,
            'USD': [61.0 + i * -0.1 for i in range(20)],
            'CNY': [2.0 + i * 0.05 for i in range(20)],
            'INR': [0.1 + i * 0.01 for i in range(20)],
            'AED': [0.05 + i * 0.005 for i in range(20)],
        }
        return pd.DataFrame(data)

@st.cache_data(ttl=86400)
def fetch_mbdcb_data():
    """
    Fetches mCBDC pilot announcements data from a CSV file.
    Data Source: Manually curated CSV (or can be extended to scrape news).
    """
    # For production, this could be a CSV file uploaded by the admin or a link to a shared spreadsheet.
    # Here we are creating a sample dataset based on recent news.
    data = {
        'Date': ['2025-12-02', '2025-11-20', '2025-10-10', '2025-09-19', '2026-03-18'],
        'Country': ['UAE, China', 'UAE', 'China, Hong Kong, Thailand, UAE', 'Saudi Arabia', 'Multiple (BIS)'],
        'Project': ['mBridge', 'mBridge', 'm-CBDCBridge', 'mBridge', 'mBridge'],
        'Stage': ['Transaction', 'Transaction', 'Pilot', 'Joined', 'Live Testing']
    }
    return pd.DataFrame(data)

@st.cache_data(ttl=43200)  # Update twice a day
def fetch_sanctions_data():
    """
    Fetches US sanctions frequency data from OFAC.
    Data Source: Office of Foreign Assets Control (OFAC)
    """
    # URL for the OFAC SDN list (CSV format)
    url = "https://www.treasury.gov/ofac/downloads/sdn.csv"
    
    try:
        df = pd.read_csv(url, encoding='latin1')
        # Convert the 'Entry Date' column to datetime
        df['Entry Date'] = pd.to_datetime(df['entry_date'], errors='coerce')
        df['Year'] = df['Entry Date'].dt.year
        
        # Group by year to get the count of sanctions
        sanctions_by_year = df.groupby('Year').size().reset_index(name='Count')
        return sanctions_by_year
    except Exception as e:
        st.error(f"Error fetching sanctions data: {e}. Using fallback data.")
        # Return mock data as fallback
        return pd.DataFrame({
            'Year': [2020, 2021, 2022, 2023, 2024, 2025],
            'Count': [850, 900, 1200, 1500, 1800, 2100]
        })

@st.cache_data(ttl=3600)  # Update hourly
def fetch_exchange_rates():
    """
    Fetches current exchange rates for DDI calculation.
    Data Source: A free currency API (e.g., exchangerate-api.com)
    """
    # Note: You need to get a free API key from https://app.exchangerate-api.com/sign-up
    api_key = "YOUR_FREE_API_KEY"  # Replace with your actual API key
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        rates = data.get('conversion_rates', {})
        return {
            'CNY': rates.get('CNY', 7.25),
            'INR': rates.get('INR', 83.5),
            'AED': rates.get('AED', 3.67)
        }
    except Exception as e:
        st.error(f"Error fetching exchange rates: {e}. Using fallback data.")
        return {'CNY': 7.25, 'INR': 83.5, 'AED': 3.67}

def calculate_ddi(reserve_share, gold_change, sanctions_score, mbdcb_active):
    """
    Calculate the Dollar Dependency Index (DDI) for a country.
    
    Parameters:
    - reserve_share: Percentage of USD in reserves (0-100)
    - gold_change: Monthly change in gold holdings (percentage)
    - sanctions_score: Number of US sanctions against the country (normalized)
    - mbdcb_active: Boolean indicating if the country is active in mCBDC
    
    Returns:
    - DDI score (0-100)
    """
    # Reserve Factor (0-50)
    reserve_factor = (reserve_share / 100) * 50
    
    # Gold Factor (0-25): Positive change (buying) reduces dependency
    if gold_change > 0:
        gold_factor = max(0, 25 - (gold_change / 2))
    else:
        gold_factor = min(25, 25 + abs(gold_change))
    
    # Sanctions Factor (0-15): Normalize sanctions score (assuming max 2000)
    max_sanctions = 2000
    sanctions_factor = min(15, (sanctions_score / max_sanctions) * 15)
    
    # mCBDC Factor (0-10): Active development reduces dependency
    if mbdcb_active:
        mbdcb_factor = 0
    else:
        mbdcb_factor = 10
    
    ddi = reserve_factor + gold_factor + sanctions_factor + mbdcb_factor
    return min(100, max(0, ddi))

# --- Dashboard UI ---

st.title("💱 ReserveShift Tracker")
st.markdown("**Real-time monitoring of global reserve shifts, de-dollarization trends, and the Dollar Dependency Index (DDI).**")

# Sidebar for user inputs and alerts
with st.sidebar:
    st.header("⚙️ Dashboard Controls")
    
    # Country selector for DDI
    st.subheader("Dollar Dependency Index (DDI)")
    country = st.selectbox("Select Country", ["USA", "China", "India", "UAE"])
    
    # Alert system setup
    st.subheader("🔔 Pro Alerts")
    st.info("Upgrade to Pro to receive email alerts when DDI changes significantly.")
    email = st.text_input("Email for Alerts (Pro)")
    threshold = st.slider("Alert Threshold (DDI change %)", 1, 20, 5)
    
    if st.button("Simulate Pro Alert (Demo)"):
        st.success(f"Demo alert sent to {email} for {country} with threshold {threshold}%!")

# Main dashboard area with tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Gold Reserves", "💱 Reserve Currencies", "🏦 mCBDC Pilots", "⚖️ US Sanctions", "📊 DDI Dashboard"])

with tab1:
    st.header("Central Bank Gold Purchases")
    gold_df = fetch_gold_data()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Top Gold Holder", gold_df.iloc[0]['Country'], f"{gold_df.iloc[0]['Gold Tonnes']:.1f} tonnes")
    with col2:
        avg_change = gold_df['Monthly Change'].mean()
        st.metric("Average Monthly Change", f"{avg_change:.2f}%", "Gold demand trend")
    
    fig = px.bar(gold_df, x='Country', y='Gold Tonnes', color='Monthly Change',
                 title="Gold Reserves by Country",
                 labels={'Gold Tonnes': 'Tonnes', 'Monthly Change': '% Change'},
                 color_continuous_scale='Viridis')
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("Data Source: World Gold Council")

with tab2:
    st.header("Currency Composition of Foreign Exchange Reserves")
    reserve_df = fetch_reserve_data()
    
    # Line chart for currency shares over time
    fig = px.line(reserve_df, x='Date', y=['USD', 'CNY', 'INR', 'AED'],
                  title="Reserve Currency Shares Over Time",
                  labels={'value': 'Share (%)', 'Date': 'Quarter'},
                  markers=True)
    st.plotly_chart(fig, use_container_width=True)
    
    # Latest values
    latest = reserve_df.iloc[-1]
    st.subheader("Latest Reserve Shares")
    cols = st.columns(4)
    for i, currency in enumerate(['USD', 'CNY', 'INR', 'AED']):
        with cols[i]:
            st.metric(currency, f"{latest[currency]:.2f}%")
    
    st.caption("Data Source: IMF COFER Database")

with tab3:
    st.header("mCBDC Pilot Announcements")
    mbdcb_df = fetch_mbdcb_data()
    
    st.dataframe(mbdcb_df, use_container_width=True)
    
    st.subheader("Cross-border CBDC Projects")
    st.markdown("""
    - **mBridge**: A multi-CBDC platform involving China, Hong Kong, Thailand, UAE, and Saudi Arabia.
    - **Digital Dirham**: UAE's CBDC, which completed its first cross-border transaction with China in late 2025.
    - **Saudi Arabia**: Joined the mBridge project in late 2025.
    - **BIS**: The Bank for International Settlements facilitated a $22 million cross-border transaction pilot in early 2026.
    """)
    st.caption("Data Source: Public announcements and news reports (manually curated)")

with tab4:
    st.header("US Sanctions Frequency Over Time")
    sanctions_df = fetch_sanctions_data()
    
    fig = px.line(sanctions_df, x='Year', y='Count', 
                  title="Number of OFAC Sanctions Listings by Year",
                  labels={'Count': 'Number of Sanctions', 'Year': 'Year'},
                  markers=True)
    fig.update_layout(xaxis=dict(tickmode='linear', tick0=2020, dtick=1))
    st.plotly_chart(fig, use_container_width=True)
    
    # Latest year
    latest_year = sanctions_df.iloc[-1]['Year']
    latest_count = sanctions_df.iloc[-1]['Count']
    st.metric(f"Sanctions in {latest_year}", latest_count, f"vs {sanctions_df.iloc[-2]['Count']} previous year")
    
    st.caption("Data Source: OFAC SDN List")

with tab5:
    st.header("Dollar Dependency Index (DDI) Dashboard")
    
    # Fetch necessary data for DDI calculation
    gold_df = fetch_gold_data()
    reserve_df = fetch_reserve_data()
    sanctions_df = fetch_sanctions_data()
    
    # Get data for the selected country
    country_data = gold_df[gold_df['Country'] == country]
    if country_data.empty:
        st.error(f"No gold data found for {country}. Using fallback.")
        gold_change = 0
        gold_tonnes = 0
    else:
        gold_change = country_data.iloc[0]['Monthly Change']
        gold_tonnes = country_data.iloc[0]['Gold Tonnes']
    
    # Get reserve share for the country (simplified mapping)
    # In a real scenario, you'd need a mapping from country to currency share
    reserve_share_map = {
        'USA': 100,  # USA's own reserves are in USD
        'China': reserve_df.iloc[-1]['CNY'] if 'CNY' in reserve_df.columns else 2.5,
        'India': reserve_df.iloc[-1]['INR'] if 'INR' in reserve_df.columns else 0.2,
        'UAE': reserve_df.iloc[-1]['AED'] if 'AED' in reserve_df.columns else 0.1
    }
    reserve_share = reserve_share_map.get(country, 10)
    
    # Get sanctions score (mock data)
    sanctions_score_map = {
        'USA': 0,
        'China': 500,
        'India': 50,
        'UAE': 20
    }
    sanctions_score = sanctions_score_map.get(country, 0)
    
    # Check mCBDC activity
    mbdcb_active_map = {
        'USA': False,
        'China': True,
        'India': False,
        'UAE': True
    }
    mbdcb_active = mbdcb_active_map.get(country, False)
    
    # Calculate DDI
    ddi = calculate_ddi(reserve_share, gold_change, sanctions_score, mbdcb_active)
    
    # Display DDI score prominently
    st.metric(f"Dollar Dependency Index (DDI) for {country}", f"{ddi:.1f}/100")
    
    # Breakdown of DDI components
    st.subheader("DDI Calculation Breakdown")
    components = {
        "Reserve Factor (0-50)": (reserve_share / 100) * 50,
        "Gold Factor (0-25)": calculate_ddi(reserve_share, gold_change, sanctions_score, mbdcb_active) - ((reserve_share / 100) * 50) - (min(15, (sanctions_score / 2000) * 15)) - (10 if not mbdcb_active else 0),
        "Sanctions Factor (0-15)": min(15, (sanctions_score / 2000) * 15),
        "mCBDC Factor (0-10)": 10 if not mbdcb_active else 0,
    }
    components_df = pd.DataFrame(list(components.items()), columns=['Component', 'Score'])
    st.dataframe(components_df, use_container_width=True)
    
    # Historical DDI (mock data)
    st.subheader("Historical DDI Trend")
    dates = pd.date_range(start='2020-01-01', periods=12, freq='Q')
    ddi_history = [ddi - i * 2 for i in range(12)][::-1]
    hist_df = pd.DataFrame({'Date': dates, 'DDI': ddi_history})
    fig = px.line(hist_df, x='Date', y='DDI', title=f"DDI for {country} Over Time")
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("DDI combines reserve share, gold trends, sanctions, and mCBDC activity. Higher score = higher dollar dependency.")

# Footer
st.markdown("---")
st.markdown("**ReserveShift Tracker** | Data updates daily | Pro version includes email alerts and API access")
