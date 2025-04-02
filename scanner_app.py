import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

st.set_page_config(page_title="Monthly Stochastic Close Scanner", layout="wide")

# === Load tickers from source file ===
def load_tickers(source):
    path = f"tickers/{source}.txt"
    if os.path.exists(path):
        with open(path, "r") as file:
            return [line.strip() for line in file if line.strip()]
    return []

# === Calculate %K and %D ===
def calculate_stochastic(df, k=14, k_smooth=6, d_smooth=3):
    if len(df) < k + k_smooth + d_smooth:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    low_min = df["Low"].rolling(window=k).min()
    high_max = df["High"].rolling(window=k).max()
    percent_k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    percent_k_smooth = percent_k.rolling(window=k_smooth).mean()
    percent_d = percent_k_smooth.rolling(window=d_smooth).mean()

    return percent_k_smooth.squeeze(), percent_d.squeeze()

# === Scanner logic ===
def scan_tickers(tickers):
    results = []

    for ticker in tickers:
        try:
            if not ticker.strip():
                continue

            st.markdown(f"---\n### 🧪 Ticker: `{ticker}`")
            df = yf.download(ticker, period="max", interval="1mo", progress=False)

            if df.empty or len(df) < 50:
                st.warning(f"{ticker} skipped — insufficient data.")
                continue

            # Get last row (last completed candle)
            last_row = df.iloc[-1]
            last_date = df.index[-1].strftime("%Y-%m-%d")
            open_, high, low, close = map(float, last_row[["Open", "High", "Low", "Close"]])

            # Stochastic
            percent_k, percent_d = calculate_stochastic(df)

            if percent_k.empty or percent_d.empty:
                st.warning(f"{ticker} skipped — stochastic data empty.")
                continue

            try:
                k_now = float(percent_k.dropna().values[-1])
                d_now = float(percent_d.dropna().values[-1])
            except:
                st.warning(f"{ticker} skipped — %K/%D could not be resolved.")
                continue

            signal_type = "Bullish" if k_now > d_now else "Bearish"

            # Get security name
            try:
                name = yf.Ticker(ticker).info.get("shortName", "N/A")
            except:
                name = "N/A"

            st.success(f"{ticker} → {signal_type} | Close: {close} | %K: {round(k_now,2)} | %D: {round(d_now,2)}")

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

        except Exception as e:
            st.error(f"{ticker} ERROR: {str(e)}")
            continue

    return pd.DataFrame(results)

# === UI ===
st.title("📆 Monthly Stochastic Close Scanner")
st.markdown("Run this scanner **after month-end** to view latest stochastic signals and candle data.")

sources = ["asx", "us_stocks", "nasdaq", "nyse", "s_p_500", "currencies"]
selected_sources = st.multiselect("Select Sources to Scan", sources)

if st.button("Run Scanner"):
    all_tickers = []
    for source in selected_sources:
        all_tickers.extend(load_tickers(source))

    st.write(f"📦 Scanning {len(all_tickers)} tickers...")
    results = scan_tickers(all_tickers)

    st.markdown("---")
    st.markdown("## ✅ Final Results")

    if not results.empty:
        st.dataframe(results)

        csv = results.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name=f"monthly_stochastic_signals_{datetime.now().date()}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No signals generated.")
