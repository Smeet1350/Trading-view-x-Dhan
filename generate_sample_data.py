import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate 1 month of 1-minute NIFTY futures data
np.random.seed(42)

start_date = datetime(2025, 9, 12, 9, 15)
data = []

# Trading hours: 9:15 AM to 3:30 PM (375 minutes per day)
base_price = 25000
current_price = base_price

# Generate 20 trading days
for day in range(20):
    day_date = start_date + timedelta(days=day)
    
    # Skip weekends
    if day_date.weekday() >= 5:
        continue
    
    # Generate intraday data
    for minute in range(375):
        timestamp = day_date + timedelta(minutes=minute)
        
        # Random walk with trend
        change = np.random.normal(0, 3)  # Volatility
        current_price += change
        
        # Generate OHLC
        open_price = current_price
        high_price = open_price + abs(np.random.normal(0, 2))
        low_price = open_price - abs(np.random.normal(0, 2))
        close_price = open_price + np.random.normal(0, 1.5)
        volume = int(np.random.uniform(1000, 50000))
        
        data.append({
            'time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        
        current_price = close_price

df = pd.DataFrame(data)
df.to_csv('ohlcv.csv', index=False)
print(f"Generated {len(df)} candles of sample NIFTY futures data")
print(f"Date range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
print(f"Price range: {df['close'].min():.2f} to {df['close'].max():.2f}")


