import yfinance as yf
import pandas as pd
import os

def download_0050():
    ticker = "0050.TW"
    start = "2025-07-05"
    end = "2026-04-15"
    filename = "0050_20250705_20260415.csv"

    print(f"Downloading data for {ticker} from {start} to {end}...")

    # Using Ticker.history() which is more reliable for 'Adjusted' close.
    # By default it's auto_adjust=True.
    t = yf.Ticker(ticker)
    df = t.history(start=start, end=end)
    
    if df.empty:
        print("No data found, trying download()...")
        df = yf.download(ticker, start=start, end=end)
        if isinstance(df.columns, pd.MultiIndex):
            # Flatten it
            df.columns = df.columns.get_level_values(0)
    
    # If using history() with auto_adjust=True, 'Close' is already adjusted.
    # The user wants "Adj Close" column specifically.
    if "Adj Close" not in df.columns:
        if "Close" in df.columns:
            print("Mapping Close to Adj Close (assuming it's adjusted).")
            df["Adj Close"] = df["Close"]
        else:
            print("Warning: Neither Close nor Adj Close found.")

    # Sort columns to put Adj Close in a visible spot
    cols = df.columns.tolist()
    if "Adj Close" in cols:
        # Move it around Close
        idx = cols.index("Close") if "Close" in cols else 0
        cols.insert(idx + 1, cols.pop(cols.index("Adj Close")))
        df = df[cols]

    df.to_csv(filename)
    print(f"Successfully saved data to {filename}")
    print("Columns:", df.columns.tolist())

if __name__ == "__main__":
    download_0050()
