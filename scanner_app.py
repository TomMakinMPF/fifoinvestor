import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

st.set_page_config(page_title="Stochastic Scanner (Debug Mode)", layout="wide")

# === Load tickers from selected source files ===
def load_tickers(source):
    path = f"tickers/{source}.txt"
    if os.path.exists(path):
        with open(path, "r") as file:
            return [line.strip() for line in file.readlines()]
    return []

# === Calculate stochastic oscillator ===
def calculate_stochastic(df, k=14, k_smooth=6, d_smooth=3):
    if len(df) < k + k_smooth + d_smooth:
        return pd.Series([np.nan]), pd.Series([np.nan])
    
    low_min = df["Low"].rolling(window=k).min()
    high_max = df["High"].rolling(window=k).max()
    percent_k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    percent_k_smooth = percent_k.rolling(window=k_smooth).mean()
    percent_d = percent_k_smooth.rolling(window=d_smooth).mean()
    return percent_k_smooth, percent_d

# === Scan tickers and classify Bullish/Bearish with debug ===
def scan_tickers(tickers, k_filter=None):
    results = []

    for ticker in tickers:
        try:
            st.markdown(f"---\n### 🧪 Ticker: `{ticker}`")
            df = yf.download(ticker, period="max", interval="1mo", progress=False)

            if df.empty:
                st.warning(f"{ticker} skipped — ❌ no data retrieved.")
                continue

            if len(df) < 50:
                st.warning(f"{ticker} skipped — ⚠️ only {len(df)} monthly candles.")
                continue

            st.text(f"✅ Retrieved {len(df)} rows.")
            st.dataframe(df.tail(5))

            percent_k, percent_d = calculate_stochastic(df)

            if percent_k.isna().all() or percent_d.isna().all():
                st.warning(f"{ticker} skipped — NaN in %K/%D values.")
                continue

            try:
                k_now = float(percent_k.iloc[-1])
                d_now = float(percent_d.iloc[-1])
            except:
                st.warning(f"{ticker} skipped — could not convert %K/%D to float.")
                continue

            signal_type = "Bullish" if k_now > d_now else "Bearish"

            st.text(f"🧮 %K last 5: {percent_k.tail(5).round(2).to_list()}")
            st.text(f"🧮 %D last 5: {percent_d.tail(5).round(2).to_list()}")
            st.success(f"Signal: {signal_type} → %K: {round(k_now,2)}, %D: {round(d_now,2)}")

            if k_filter is None or k_now < k_filter:
                results.append({
                    "Ticker": ticker,
                    "Signal": signal_type,
                    "%K": round(k_now, 2),
                    "%D": round(d_now, 2),
                    "Signal Date": df.index[-1].strftime("%Y-%m-%d")
                })

        except Exception as e:
            st.error(f"{ticker} ERROR: {str(e)}")
            continue

    return pd.DataFrame(results)

# === Streamlit UI ===
st.title("🔍 Stochastic Debug Scanner")
st.markdown("Scans each ticker with raw data, stochastic values, and Bullish/Bearish classification. Useful for debugging and signal verification.")

sources = ["asx", "us_stocks", "nasdaq", "nyse", "s_p_500", "currencies"]
selected_sources = st.multiselect("Select Sources to Scan", sources)

k_threshold = st.slider("Optional Filter: Only show signals where %K is below", 0, 100, 100)

if st.button("Run Diagnostic Scan"):
    all_tickers = []
    for source in selected_sources:
        all_tickers.extend(load_tickers(source))

    st.write(f"📦 Total tickers loaded: {len(all_tickers)}")
    results = scan_tickers(all_tickers, k_filter=k_threshold)

    st.markdown("---")
    st.markdown("## ✅ Final Results Table")
    if not results.empty:
        st.dataframe(results)

        csv = results.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"stoch_signals_debug_{datetime.now().date()}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No tickers matched the scan criteria.")
