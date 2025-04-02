import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

st.set_page_config(page_title="Monthly Stochastic Scanner", layout="wide")

# === Load tickers from text files ===
def load_tickers(source):
    path = f"tickers/{source}.txt"
    if os.path.exists(path):
        with open(path, "r") as file:
            return [line.strip() for line in file if line.strip()]
    return []

# === Calculate stochastic oscillator ===
def calculate_stochastic(df, k=14, k_smooth=6, d_smooth=3):
    if len(df) < k + k_smooth + d_smooth:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    low_min = df["Low"].rolling(window=k).min()
    high_max = df["High"].rolling(window=k).max()
    percent_k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    percent_k_smooth = percent_k.rolling(window=k_smooth).mean()
    percent_d = percent_k_smooth.rolling(window=d_smooth).mean()
    return percent_k_smooth.squeeze(), percent_d.squeeze()

# === Main scanning logic (clean output) ===
def scan_tickers(ticker_map):
    results = []

    for ticker, source in ticker_map:
        try:
            if not ticker.strip():
                continue

            df = yf.download(ticker, period="max", interval="1mo", progress=False)
            if df.empty or len(df) < 50:
                continue

            last_row = df.iloc[-1]
            last_date = df.index[-1].strftime("%Y-%m-%d")
            open_, high, low, close = map(float, last_row[["Open", "High", "Low", "Close"]])

            # === Price filters by exchange ===
            if source == "asx" and close < 0.50:
                continue
            if source in ["us_stocks", "nasdaq", "nyse", "s_p_500"] and close < 1.00:
                continue

            percent_k, percent_d = calculate_stochastic(df)
            if percent_k.empty or percent_d.empty:
                continue

            try:
                k_now = float(percent_k.dropna().values[-1])
                d_now = float(percent_d.dropna().values[-1])
            except:
                continue

            signal_type = "Bullish" if k_now > d_now else "Bearish"

            try:
                name = yf.Ticker(ticker).info.get("shortName", "N/A")
            except:
                name = "N/A"

            results.append({
                "Ticker": ticker,
                "Name": name,
                "Date": last_date,
                "Open": round(open_, 2),
                "High": round(high, 2),
                "Low": round(low, 2),
                "Close": round(close, 2),
                "%K": round(k_now, 2),
                "%D": round(d_now, 2),
                "Signal": signal_type
            })

        except:
            continue

    return pd.DataFrame(results)

# === Streamlit UI ===
st.title("📊 Monthly Stochastic Close Scanner")
st.markdown("Scans for stochastic crossovers using the latest monthly candle. Applies price filters and outputs clean CSV-ready results.")

sources = ["asx", "us_stocks", "nasdaq", "nyse", "s_p_500", "currencies"]
selected_sources = st.multiselect("Select Sources to Scan", sources)

if st.button("Run Scanner"):
    ticker_map = []
    for source in selected_sources:
        tickers = load_tickers(source)
        ticker_map.extend([(ticker, source) for ticker in tickers])

    st.write(f"📦 Scanning {len(ticker_map)} tickers...")

    results = scan_tickers(ticker_map)

    st.markdown("## ✅ Scan Results")

    if not results.empty:
        csv = results.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Full Results CSV",
            data=csv,
            file_name=f"monthly_stoch_signals_{datetime.now().date()}.csv",
            mime="text/csv"
        )

        st.dataframe(results, use_container_width=True)
    else:
        st.warning("⚠️ No valid results to display.")
        empty_df = pd.DataFrame(columns=["Ticker", "Name", "Date", "Open", "High", "Low", "Close", "%K", "%D", "Signal"])
        st.dataframe(empty_df, use_container_width=True)
