import yfinance as yf
import pandas as pd
import pandas_ta as ta

ticker = "META"
df = yf.download(ticker, period="3y", interval="1d")

df["RSI"] = ta.rsi(df["Close"], length=14)
df["EMA200"] = ta.ema(df["Close"], length=200)

df = df.dropna().copy()

trades = []
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

    # ✅ WEJŚCIE – RSI WYCHODZI Z KOREKTY (CROSS)
    if not position:
        if rsi_prev < 35 and rsi >= 35 and close > ema200:
            position = True
            entry_price = close
            entry_date = df.index[i]

    # ✅ WYJŚCIE
    else:
        stop_loss = entry_price * 0.97  # -3%
        take_profit = entry_price * 1.04  # +4%

        if close <= stop_loss or close >= take_profit or rsi > 65:
            exit_price = close
            exit_date = df.index[i]

            profit = (exit_price - entry_price) / entry_price * 100

            trades.append({
                "Ticker": ticker,
                "Entry Date": entry_date,
                "Exit Date": exit_date,
                "Entry": round(entry_price, 2),
                "Exit": round(exit_price, 2),
                "Profit %": round(profit, 2)
            })

            position = False

results = pd.DataFrame(trades)

# ✅ ZABEZPIECZENIE
if results.empty:
    print("❌ Brak transakcji – zmień parametry lub ticker")
else:
    results.to_csv("data/backtest_USA.csv", index=False)

    print(results)
    print("\nLiczba transakcji:", len(results))
    print("Średni wynik %:", round(results["Profit %"].mean(), 2))
    print("Skuteczność %:", round((results["Profit %"] > 0).mean() * 100, 2))
