# ReserveShift Tracker 💱

A complete, production-ready **ReserveShift Tracker** dashboard designed to monitor global reserve shifts and calculate the **Dollar Dependency Index (DDI)** scoring model.

## 📊 Dashboard Architecture & Data Strategy

The dashboard is built as a single, robust Python application using the following stack:

*   **Frontend & Framework**: `Streamlit` for the interactive web interface.
*   **Data Processing**: `pandas` for all data manipulation and analysis.
*   **Visualizations**: `plotly` for creating interactive, high-quality charts.
*   **Data Sources**:
    *   **Gold Purchases**: `World Gold Council` via the `pandas` library.
    *   **Reserve Currencies (USD, CNY, INR, AED)**: `IMF COFER` data, fetched using the `IMF` API via `pandas`.
    *   **mCBDC Pilot Announcements**: Manually tracked via a curated dataset reflecting recent news and central bank announcements.
    *   **US Sanctions Frequency**: `OFAC` data, parsed from their website using `pandas`.
    *   **Exchange Rates**: Fetched from a currency API for DDI calculations.

## 🧠 Dollar Dependency Index (DDI) Scoring Model

The DDI is a composite score (0-100) that quantifies a country's reliance on the US dollar. A **higher score** indicates **higher dependency**.

**DDI = GoldFactor + ReserveFactor + SanctionFactor + mCBDCFactor**

*   **GoldFactor (0-25 pts)**: Higher dependency if a country is selling gold. Lower if buying.
*   **ReserveFactor (0-50 pts)**: Based on the % of USD in a country's reserves.
*   **SanctionFactor (0-15 pts)**: Higher dependency for countries with more US sanctions.
*   **mCBDCFactor (0-10 pts)**: Lower dependency for countries actively developing mCBDCs.

## 🚀 How to Run the Dashboard

Follow these steps to get the dashboard up and running on your local machine:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/abdulazeemshaikh/reserve-shift-tracker.git
    cd reserve-shift-tracker
    ```

2.  **Install Dependencies**:
    Ensure you have Python installed, then run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the App**:
    In the terminal, run the following command:
    ```bash
    streamlit run reserveshift_tracker.py
    ```

Streamlit will start a local web server and automatically open the dashboard in your default web browser.

## 💡 Monetization & Pro Features

The dashboard includes a framework for a Pro tier, primarily through a **real-time alerting system**:
*   **Pro Alerts**: Users can subscribe to receive notifications when the DDI for a selected country changes significantly.
*   **Implementation**: This can be extended by integrating a database (like SQLite/Firebase) and a background scheduler to monitor DDI fluctuations and trigger emails via SendGrid or SMTP.

---
**ReserveShift Tracker** | Developed for monitoring de-dollarization trends.
