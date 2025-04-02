import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

st.set_page_config(page_title="Stochastic Scanner (Final FIXED)", layout="wide")

def load_tickers(source):
    path = f"tickers/{source}.txt"
    if os.path.exists(path):
        with open(path, "r") as file:
            return [line.strip() for line in file.readlines()]
    return []

def calculate_stochastic(df, k=14, k_smooth=6, d_smooth=3):
    if len(df) < k + k_smooth + d_smooth:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    low_min = df["Low"].rolling(window=k).min()
    high_max = df["High"].rolling(window=k).max()
    percent_k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    percent_k_smooth = percent_k.rolling(window=k_smooth).mean()
    percent_d = percent_k_smooth.rolling(window=d_smooth).mean()
    return percent_k_smooth, percent_d

def scan_tickers(tickers):
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

            # Ensure at least one value exists
            if percent_k.empty or percent_d.empty:
                st.warning(f"{ticker} skipped — empty %K/%D.")
                continue

            if percent_k.isna().all() or percent_d.isna().all():
                st.warning(f"{ticker} skipped — NaNs in %K/%D.")
                continue

            # Safely extract last values
            try:
                k_now = percent_k.dropna().iloc[-1]
                d_now = percent_d.dropna().iloc[-1]
                k_now = float(k_now)
                d_now = float(d_now)
            except Exception as e:
                st.warning(f"{ticker} skipped — could not resolve %K/%D to floats. {e}")
                continue

            signal_type = "Bullish" if k_now > d_now else "Bearish"

            st.text(f"🧮 %K last 5: {percent_k.tail(5).round(2).to_list()}")
            st.text(f"🧮 %D last 5: {percent_d.tail(5).round(2).to_list()}")
            st.success(f"Signal: {signal_type} → %K: {round(k_now,2)}, %D: {round(d_now,2)}")

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
st.title("📊 Monthly Stochastic Scanner (Final FIXED)")
st.markdown("Scans selected tickers for stochastic setup. No filters. Diagnostic mode with full logging.")

sources = ["asx", "us_stocks", "nasdaq", "nyse", "s_p_500", "currencies"]
selected_sources = st.multiselect("Select Sources to Scan", sources)

if st.button("Run Scanner"):
    all_tickers = []
    for source in selected_sources:
        all_tickers.extend(load_tickers(source))

    st.write(f"🔍 Total tickers loaded: {len(all_tickers)}")
    results = scan_tickers(all_tickers)

    st.markdown("---")
    st.markdown("## ✅ Final Results Table")
    if not results.empty:
        st.dataframe(results)

        csv = results.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"stoch_signals_{datetime.now().date()}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No valid signals found.")
