import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

st.set_page_config(page_title="FIFO Investor Scanner", layout="wide")

# === Load tickers from text files ===
def load_tickers(source):
    path = f"tickers/{source}.txt"
    if os.path.exists(path):
        with open(path, "r") as file:
            return [line.strip() for line in file if line.strip()]
    return []

# === TradingView-style stochastic (14, 6, 3)
def calculate_stochastic(df, k=14, k_smooth=6, d_smooth=3):
    if len(df) < k + k_smooth + d_smooth:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    lowest_low = df["Low"].rolling(window=k).min()
    highest_high = df["High"].rolling(window=k).max()

    raw_k = 100 * (df["Close"] - lowest_low) / (highest_high - lowest_low)
    percent_k = raw_k.rolling(window=k_smooth).mean()
    percent_d = percent_k.rolling(window=d_smooth).mean()

    return percent_k.squeeze(), percent_d.squeeze()

# === Signal label logic
def get_signal(k_val, d_val):
    return "📈 Bullish" if k_val > d_val else "📉 Bearish"

# === Scanner logic
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

            # Filter penny stocks
            if source == "asx" and close < 0.50:
                continue
            if source in ["us_stocks", "nasdaq", "nyse", "s_p_500"] and close < 1.00:
                continue

            percent_k, percent_d = calculate_stochastic(df)
            if percent_k.empty or percent_d.empty or len(percent_k.dropna()) < 2:
                continue

            k_now = float(percent_k.dropna().values[-1])
            d_now = float(percent_d.dropna().values[-1])
            k_prev = float(percent_k.dropna().values[-2])
            d_prev = float(percent_d.dropna().values[-2])

            current_signal = get_signal(k_now, d_now)
            previous_signal = get_signal(k_prev, d_prev)
            buy = "Yes" if previous_signal.endswith("Bearish") and current_signal.endswith("Bullish") else ""

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
                "Signal": current_signal,
                "Buy": buy
            })

        except:
            continue

    return pd.DataFrame(results)

# === Row styling
def highlight_rows(row):
    if row["Buy"] == "Yes":
        return ["background-color: gold"] * len(row)
    elif "Bullish" in row["Signal"]:
        return ["background-color: rgba(0,255,0,0.15)"] * len(row)
    elif "Bearish" in row["Signal"]:
        return ["background-color: rgba(255,0,0,0.15)"] * len(row)
    else:
        return [""] * len(row)

# === UI
st.title("📊 FIFO Investor Scanner")
st.markdown("Run after the monthly close to identify directional opportunities across selected market groups.")

sources = ["asx", "us_stocks", "nasdaq", "nyse", "s_p_500", "currencies"]
selected_sources = st.multiselect("Select Market Groups to Scan", sources)

if st.button("Run Scanner"):
    ticker_map = []
    for source in selected_sources:
        tickers = load_tickers(source)
        ticker_map.extend([(ticker, source) for ticker in tickers])

    st.write(f"📦 Scanning {len(ticker_map)} instruments...")

    results = scan_tickers(ticker_map)

    st.markdown("## ✅ Scanner Results")

    if not results.empty:
        csv = results.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name=f"fifo_scan_{datetime.now().date()}.csv",
            mime="text/csv"
        )

        styled = results.style.apply(highlight_rows, axis=1)
        st.dataframe(styled, use_container_width=True)
    else:
        st.warning("⚠️ No valid results to display.")
        empty_df = pd.DataFrame(columns=["Ticker", "Name", "Date", "Open", "High", "Low", "Close", "%K", "%D", "Signal", "Buy"])
        st.dataframe(empty_df, use_container_width=True)
