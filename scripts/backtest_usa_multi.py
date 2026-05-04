import yfinance as yf
import pandas as pd
import pandas_ta as ta

tickers = [
    "AAPL", "MSFT", "NVDA", "AMD", "META",
    "TSLA", "GOOGL", "AMZN"
]

all_trades = []

for ticker in tickers:
    df = yf.download(ticker, period="3y", interval="1d", progress=False)

    if df.empty or len(df) < 250:
        continue

    df["RSI"] = ta.rsi(df["Close"], 14)
    df["EMA200"] = ta.ema(df["Close"], 200)
    df = df.dropna().copy()

    position = False
    entry_price = None
    entry_date = None

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        row = df.iloc[i]

        rsi_prev = float(prev["RSI"])
        rsi = float(row["RSI"])
        close = float(row["Close"])
        ema200 = float(row["EMA200"])

        # WEJŚCIE
        if not position:
            if rsi_prev < 35 and rsi >= 35 and close > ema200:
                position = True
                entry_price = close
                entry_date = df.index[i]

        # WYJŚCIE
        else:
            stop_loss = entry_price * 0.97
            take_profit = entry_price * 1.04

            if close <= stop_loss or close >= take_profit or rsi > 65:
                exit_price = close
                exit_date = df.index[i]

                profit = (exit_price - entry_price) / entry_price * 100

                all_trades.append({
                    "Market": "USA",
                    "Ticker": ticker,
                    "Entry Date": entry_date,
                    "Exit Date": exit_date,
                    "Entry": round(entry_price, 2),
                    "Exit": round(exit_price, 2),
                    "Profit %": round(profit, 2)
                })

                position = False

results = pd.DataFrame(all_trades)
results.to_csv("data/backtest_USA_multi.csv", index=False)

print("USA – liczba transakcji:", len(results))
if not results.empty:
    print("Średni wynik %:", round(results["Profit %"].mean(), 2))
    print("Skuteczność %:", round((results["Profit %"] > 0).mean() * 100, 2))
