import pandas as pd
import pandas_ta as ta

url = "https://stooq.pl/q/d/l/?s=pkn&i=d"
df = pd.read_csv(url)

df["RSI"] = ta.rsi(df["Zamkniecie"], 14)
df["EMA200"] = ta.ema(df["Zamkniecie"], 200)

trades = []
position = False

for i in range(200, len(df)):
    row = df.iloc[i]

    if not position:
        if row["RSI"] > 35 and row["Zamkniecie"] > row["EMA200"]:
            entry_price = row["Zamkniecie"]
            entry_date = row["Data"]
            position = True

    else:
        stop_loss = entry_price * 0.97
        if row["RSI"] > 60 or row["Zamkniecie"] < stop_loss:
            exit_price = row["Zamkniecie"]
            exit_date = row["Data"]

            profit = (exit_price - entry_price) / entry_price * 100

            trades.append({
                "Spółka": "PKN",
                "Wejście": entry_date,
                "Wyjście": exit_date,
                "Zysk %": round(profit, 2)
            })

            position = False

results = pd.DataFrame(trades)
results.to_csv("backtest_GPW.csv", index=False)

print(results)
print("Średni wynik:", results["Zysk %"].mean())
