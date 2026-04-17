import pandas as pd
import numpy as np

def check_csv(file_path):
    print(f"Checking file: {file_path}")
    try:
        # The file has a 3-line header structure
        # Line 1: Header (Price/Close/High/Low/Open/Volume)
        # Line 2: Ticker (0050.TW repeated)
        # Line 3: Date, , , , ,
        
        # Read with multi-index headers
        df_raw = pd.read_csv(file_path, header=[0, 1, 2], index_col=0)
        
        print("\n--- Basic Info ---")
        print(f"Shape: {df_raw.shape}")
        print(f"Index range: {df_raw.index.min()} to {df_raw.index.max()}")
        
        # Check for missing values
        missing = df_raw.isnull().sum().sum()
        print(f"Total missing values: {missing}")
        
        # Flatten columns
        # Index 0 is 'Ticker'
        # Index 1 is the price type (Close, High, Low, Open, Volume)
        # Index 2 is usually empty or '0050.TW'
        # Wait, looking at the previous output:
        # Columns: [('Close', '0050.TW', 'Unnamed: 1_level_2'), ...]
        # This is interesting. Level 0 is Close, Level 1 is Ticker, Level 2 is level name.
        
        df = df_raw.copy()
        df.columns = [col[0] for col in df.columns] # Take 'Close', 'High', etc.
        
        print("\n--- Price Stats ---")
        print(df[['Open', 'High', 'Low', 'Close']].agg(['min', 'max', 'mean']))

        print("\n--- Data Integrity Checks ---")
        # High should be >= all others
        high_err = df[~((df['High'] >= df['Open'] - 1e-4) & (df['High'] >= df['Close'] - 1e-4) & (df['High'] >= df['Low'] - 1e-4))]
        if not high_err.empty:
            print(f"High price errors found at {len(high_err)} rows.")
        else:
            print("High price consistency: OK")
            
        # Low should be <= all others
        low_err = df[~((df['Low'] <= df['Open'] + 1e-4) & (df['Low'] <= df['Close'] + 1e-4) & (df['Low'] <= df['High'] + 1e-4))]
        if not low_err.empty:
            print(f"Low price errors found at {len(low_err)} rows.")
        else:
            print("Low price consistency: OK")
            
        # Volume should be >= 0
        vol_err = df[df['Volume'] < 0]
        if not vol_err.empty:
            print(f"Negative volume found: {len(vol_err)} rows.")
        else:
            print("Volume consistency: OK")

        # Date gaps
        df.index = pd.to_datetime(df.index)
        # Check for gaps longer than 5 days
        gaps = df.index.to_series().diff().dt.days
        big_gaps = gaps[gaps > 6] # Taiwan has Chinese New Year where markets close for ~7 days
        if not big_gaps.empty:
            print(f"\nPotential long gaps in trading ( > 6 days ):")
            print(big_gaps)
        else:
            print("\nNo unusually long time gaps found ( max gap: {} days ).".format(gaps.max()))

    except Exception as e:
        import traceback
        print(f"Error checking file: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    check_csv(r'c:\Users\ben12\Downloads\Antigravity 專用資料夾\ETF0050_買進策略回測\0050_20250705_20260415.csv')
