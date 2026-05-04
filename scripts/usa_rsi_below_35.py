import yfinance as yf
import pandas as pd
import pandas_ta as ta

tickers = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META"]

results = []

for t in tickers:
    df = yf.download(t, period="6mo", interval="1d")
    if df.empty:
        continue

    df["RSI"] = ta.rsi(df["Close"], length=14)
    df["EMA200"] = ta.ema(df["Close"], length=200)

    last = df.iloc[-1]

    if 30 < last["RSI"] < 40 and last["Close"] > last["EMA200"]:
        results.append({
            "Ticker": t,
            "RSI": round(last["RSI"], 2),
            "Close": round(last["Close"], 2)
        })

print(pd.DataFrame(results))
