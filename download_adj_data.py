import yfinance as yf
import pandas as pd
import sys

print("Downloading 0050.TW historical data...")
# auto_adjust=True by default in latest yfinance, so OHLC is already fully adjusted for splits/dividends!
df = yf.download("0050.TW", period="max", progress=False)

if df.empty:
    print("Download failed!")
    sys.exit(1)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)

df = df.dropna()

df_out = df[['Close', 'High', 'Low', 'Open', 'Volume']].copy()
df_out = df_out.round(4)
df_out.reset_index(inplace=True)
df_out['Date'] = df_out['Date'].dt.strftime('%Y-%m-%d')

# Sanitize anomalies (e.g. Yahoo Finance sometimes returns 0.0 for Open)
for col in ['Open', 'High', 'Low']:
    df_out.loc[df_out[col] == 0.0, col] = df_out['Close']

# Reorder columns

df_out = df_out[['Date', 'Close', 'High', 'Low', 'Open', 'Volume']]

file_path = "0050_historical_adj.csv"
df_out.to_csv(file_path, index=False)

print(f"Data saved successfully to {file_path}. Total rows: {len(df_out)}")
