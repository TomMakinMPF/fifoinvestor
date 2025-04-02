import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

st.set_page_config(page_title="Stochastic Scanner", layout="wide")

def load_tickers(source):
    path = f"tickers/{source}.txt"
    if os.path.exists(path):
        with open(path, "r") as file:
            return [line.strip() for line in file.readlines()]
    return []

def calculate_stochastic(df, k=14, k_smooth=6, d_smooth=3):
    low_min = df["Low"].rolling(window=k).min()
    high_max = df["High"].rolling(window=k).max()
    percent_k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    percent_k_smooth = percent_k.rolling(window=k_smooth).mean()
    percent_d = percent_k_smooth.rolling(window=d_smooth).mean()
    return percent_k_smooth, percent_d

def scan_tickers(tickers, k_filter=None):
    results = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="2y", interval="1mo", progress=False)
            if df.empty or len(df) < 5:
                continue
            percent_k, percent_d = calculate_stochastic(df)
            if percent_k.isna().any() or percent_d.isna().any():
                continue
            if percent_k.iloc[-2] < percent_d.iloc[-2] and percent_k.iloc[-1] > percent_d.iloc[-1]:
                if k_filter is None or percent_k.iloc[-1] < k_filter:
                    results.append({
                        "Ticker": ticker,
                        "%K": round(percent_k.iloc[-1], 2),
                        "%D": round(percent_d.iloc[-1], 2),
                        "Signal Date": df.index[-1].strftime("%Y-%m-%d")
                    })
        except Exception as e:
            continue
    return pd.DataFrame(results)

st.title("📈 Monthly Stochastic Bullish Crossover Scanner")

sources = ["asx", "us_stocks", "nasdaq", "nyse", "s_p_500", "currencies"]
selected_sources = st.multiselect("Select Sources to Scan", sources)

k_threshold = st.slider("Optional Filter: Only show signals where %K is below", 0, 100, 100)

if st.button("Run Scanner"):
    all_tickers = []
    for source in selected_sources:
        all_tickers.extend(load_tickers(source))
    st.write(f"Scanning {len(all_tickers)} tickers...")
    results = scan_tickers(all_tickers, k_filter=k_threshold)
    if not results.empty:
        st.success(f"Found {len(results)} signals")
        st.dataframe(results)
        csv = results.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, f"stoch_signals_{datetime.now().date()}.csv", "text/csv")
    else:
        st.warning("No bullish stochastic crossovers found.")
