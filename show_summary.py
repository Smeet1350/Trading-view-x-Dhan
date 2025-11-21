import pandas as pd

df = pd.read_csv('grid_results.csv')

print('\n' + '='*70)
print('BACKTEST SUMMARY STATISTICS - ALL 256 COMBINATIONS')
print('='*70)
print(f'\nTotal Combinations Tested: {len(df)}')
print(f'\nProfitable Combinations: {(df["net_pnl"] > 0).sum()} ({(df["net_pnl"] > 0).sum()/len(df)*100:.1f}%)')
print(f'Loss-making Combinations: {(df["net_pnl"] < 0).sum()} ({(df["net_pnl"] < 0).sum()/len(df)*100:.1f}%)')

print(f'\n--- Net PnL Statistics ---')
print(f'Best Net PnL: {df["net_pnl"].max():.2f} points')
print(f'Worst Net PnL: {df["net_pnl"].min():.2f} points')
print(f'Average Net PnL: {df["net_pnl"].mean():.2f} points')
print(f'Median Net PnL: {df["net_pnl"].median():.2f} points')

print(f'\n--- Performance Metrics ---')
print(f'Average Win Rate: {df["win_rate"].mean():.2f}%')
print(f'Best Win Rate: {df["win_rate"].max():.2f}%')
print(f'Average Profit Factor: {df["profit_factor"].mean():.2f}')
print(f'Best Profit Factor: {df["profit_factor"].max():.2f}')

print(f'\n--- Trading Activity ---')
print(f'Average Trades per Combo: {df["total_trades"].mean():.0f}')
print(f'Max Trades: {df["total_trades"].max():.0f}')
print(f'Min Trades: {df["total_trades"].min():.0f}')

print(f'\n--- Risk Metrics ---')
print(f'Average Max Drawdown: {df["max_drawdown"].mean():.2f} points')
print(f'Best (Lowest) Max Drawdown: {df["max_drawdown"].min():.2f} points')
print(f'Worst Max Drawdown: {df["max_drawdown"].max():.2f} points')

print('\n' + '='*70)
print('TOP 5 BY DIFFERENT METRICS')
print('='*70)

print('\n--- Top 5 by Net PnL ---')
print(df.nlargest(5, 'net_pnl')[['length', 'len_mult', 'net_pnl', 'win_rate', 'profit_factor', 'total_trades']].to_string(index=False))

print('\n--- Top 5 by Win Rate ---')
print(df.nlargest(5, 'win_rate')[['length', 'len_mult', 'win_rate', 'net_pnl', 'profit_factor', 'total_trades']].to_string(index=False))

print('\n--- Top 5 by Profit Factor ---')
print(df.nlargest(5, 'profit_factor')[['length', 'len_mult', 'profit_factor', 'net_pnl', 'win_rate', 'total_trades']].to_string(index=False))

print('\n' + '='*70)


