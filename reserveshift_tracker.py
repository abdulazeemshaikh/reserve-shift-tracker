"""
ReserveShift Tracker
A real-time dashboard to monitor global reserve shifts and the Dollar Dependency Index (DDI).
Self-contained version with April 2026 static datasets.
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

# --- Static Data Fetching Functions ---

@st.cache_data
def fetch_gold_data():
    """
    Gold holdings by country. Source: World Gold Council (Dec 2025).
    """
    return pd.DataFrame({
        'Country': ['USA', 'Germany', 'Italy', 'France', 'Russia', 'China', 'Switzerland', 'Japan', 'India', 'Netherlands'],
        'Gold Tonnes': [8133.5, 3351.5, 2451.8, 2436.9, 2332.8, 2264.3, 1040.0, 845.9, 840.8, 612.5],
        'Monthly Change': [0.0, -0.1, 0.0, 0.0, 0.3, 0.2, 0.0, 0.0, 0.1, 0.0]
    })

@st.cache_data
def fetch_reserve_data():
    """
    Currency composition of foreign exchange reserves. Source: IMF COFER (Dec 2025).
    """
    return pd.DataFrame({
        'Date': ['2025Q1', '2025Q2', '2025Q3'],
        'USD': [57.79, 57.08, 56.92],
        'CNY': [2.00, 1.99, 1.93],
        'INR': [0.20, 0.20, 0.20],
        'AED': [0.05, 0.05, 0.05]
    })

@st.cache_data
def fetch_trade_settlement_data():
    """
    Bilateral trade settlement outside the USD system. Source: India 2026 de-dollarization summary.
    """
    return pd.DataFrame({
        'Date': ['2025-11-01', '2025-12-15', '2026-01-10', '2026-02-20', '2026-03-01'],
        'Country': ['UAE, China', 'India, UAE', 'India, Russia', 'India, Bangladesh', 'Brazil, China'],
        'Currency Pair': ['CNY/AED', 'INR/AED', 'INR/CNY', 'INR/BDT', 'BRL/CNY'],
        '% of Trade': [32, 18, 15, 8, 25]
    })

@st.cache_data
def fetch_sanctions_data():
    """
    US Sanctions frequency (OFAC SDN Listings). Source: OFAC 2025.
    """
    return pd.DataFrame({
        'Year': [2021, 2022, 2023, 2024, 2025],
        'Count': [900, 1200, 1500, 1800, 2100]
    })

@st.cache_data
def fetch_sanctions_enforcement_data():
    """
    US Sanctions penalty cases. Source: OFAC 2025.
    """
    return pd.DataFrame({
        'Year': [2021, 2022, 2023, 2024, 2025],
        'Count': [15, 16, 17, 12, 14]
    })

@st.cache_data
def fetch_exchange_rates():
    """
    Fixed/Average exchange rates for DDI calculation. Source: Fed 2025.
    """
    return {'CNY': 7.1875, 'INR': 87.1468, 'AED': 3.6729}

def calculate_ddi(reserve_share, gold_change, sanctions_score, mbdcb_active):
    """
    Calculate the Dollar Dependency Index (DDI) for a country.
    """
    # Reserve Factor (0-50)
    reserve_factor = (reserve_share / 100) * 50
    
    # Gold Factor (0-25)
    if gold_change > 0:
        gold_factor = max(0, 25 - (gold_change / 2))
    else:
        gold_factor = min(25, 25 + abs(gold_change))
    
    # Sanctions Factor (0-15): Normalize sanctions score (assuming max 2000)
    max_sanctions = 2000
    sanctions_factor = min(15, (sanctions_score / max_sanctions) * 15)
    
    # mCBDC Factor (0-10)
    if mbdcb_active:
        mbdcb_factor = 0
    else:
        mbdcb_factor = 10
    
    ddi = reserve_factor + gold_factor + sanctions_factor + mbdcb_factor
    return min(100, max(0, ddi))

# --- Dashboard UI ---

st.title("💱 ReserveShift Tracker")
st.markdown("**Real-time monitoring of global reserve shifts, de-dollarization trends, and the Dollar Dependency Index (DDI).**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Dashboard Controls")
    country = st.selectbox("Select Country", ["USA", "China", "India", "UAE"])
    
    st.subheader("🔔 Pro Alerts")
    st.info("Upgrade to Pro to receive email alerts when DDI changes significantly.")
    email = st.text_input("Email for Alerts (Pro)")
    threshold = st.slider("Alert Threshold (DDI change %)", 1, 20, 5)
    
    if st.button("Simulate Pro Alert (Demo)"):
        st.success(f"Demo alert sent to {email} for {country} with threshold {threshold}%!")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Gold Reserves", "💱 Reserve Currencies", "🤝 Trade Settlement", "⚖️ US Sanctions", "📊 DDI Dashboard"])

with tab1:
    st.header("Central Bank Gold Purchases")
    gold_df = fetch_gold_data()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Top Gold Holder", gold_df.iloc[0]['Country'], f"{gold_df.iloc[0]['Gold Tonnes']:,} tonnes")
    with col2:
        avg_change = gold_df['Monthly Change'].mean()
        st.metric("Average Monthly Change", f"{avg_change:.2f}%", "Gold demand trend")
    
    fig = px.bar(gold_df, x='Country', y='Gold Tonnes', color='Monthly Change',
                 title="Gold Reserves by Country (Dec 2025)",
                 labels={'Gold Tonnes': 'Tonnes', 'Monthly Change': '% Change'},
                 color_continuous_scale='Viridis')
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Data Source: World Gold Council via IMF IFS")

with tab2:
    st.header("Currency Composition of Foreign Exchange Reserves")
    reserve_df = fetch_reserve_data()
    
    fig = px.line(reserve_df, x='Date', y=['USD', 'CNY', 'INR', 'AED'],
                  title="Reserve Currency Shares (2025 Trend)",
                  labels={'value': 'Share (%)', 'Date': 'Quarter'},
                  markers=True)
    st.plotly_chart(fig, use_container_width=True)
    
    latest = reserve_df.iloc[-1]
    st.subheader("Latest Reserve Shares (2025Q3)")
    cols = st.columns(4)
    for i, currency in enumerate(['USD', 'CNY', 'INR', 'AED']):
        with cols[i]:
            st.metric(currency, f"{latest[currency]:.2f}%")
    st.caption("Data Source: IMF COFER")

with tab3:
    st.header("Bilateral Trade Settlement Outside USD")
    trade_df = fetch_trade_settlement_data()
    st.dataframe(trade_df, use_container_width=True)
    
    fig = px.pie(trade_df, values='% of Trade', names='Currency Pair', title="Trade Settlement Distribution (Recent Samples)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Data Source: 2026 De-dollarization Summary")

with tab4:
    st.header("US Sanctions Intensity")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("SDN Listings (Sanctions Frequency)")
        sanc_df = fetch_sanctions_data()
        fig1 = px.line(sanc_df, x='Year', y='Count', markers=True, title="Total OFAC SDN Listings")
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("Penalty Cases (Enforcement)")
        enf_df = fetch_sanctions_enforcement_data()
        fig2 = px.bar(enf_df, x='Year', y='Count', title="OFAC Enforcement Penalty Cases")
        st.plotly_chart(fig2, use_container_width=True)
    st.caption("Data Source: OFAC SDN List & Enforcement Actions")

with tab5:
    st.header("Dollar Dependency Index (DDI) Dashboard")
    
    # DDI Data Matrix
    ddi_matrix = {
        'USA': {'share': 100, 'gold_change': 0.0, 'sanctions': 0, 'mbdc': False},
        'China': {'share': 3.0, 'gold_change': 0.2, 'sanctions': 500, 'mbdc': True},
        'India': {'share': 0.2, 'gold_change': 0.1, 'sanctions': 50, 'mbdc': False},
        'UAE': {'share': 0.05, 'gold_change': 0.0, 'sanctions': 20, 'mbdc': True}
    }
    
    data = ddi_matrix.get(country)
    ddi = calculate_ddi(data['share'], data['gold_change'], data['sanctions'], data['mbdc'])
    
    st.metric(f"Dollar Dependency Index (DDI) for {country}", f"{ddi:.1f}/100")
    
    st.subheader("DDI Calculation Breakdown")
    reserve_factor = (data['share'] / 100) * 50
    sanctions_factor = min(15, (data['sanctions'] / 2000) * 15)
    mbdc_factor = 0 if data['mbdc'] else 10
    gold_factor = ddi - reserve_factor - sanctions_factor - mbdc_factor
    
    components = {
        "Reserve Factor (0-50)": reserve_factor,
        "Gold Factor (0-25)": gold_factor,
        "Sanctions Factor (0-15)": sanctions_factor,
        "mCBDC Factor (0-10)": mbdc_factor,
    }
    st.dataframe(pd.DataFrame(list(components.items()), columns=['Component', 'Score']), use_container_width=True)
    st.caption("DDI: Higher score = higher dollar dependency.")

# Footer
st.markdown("---")
st.markdown("**ReserveShift Tracker** | Self-Contained Alpha v2.0 | Data Updated April 2026")
