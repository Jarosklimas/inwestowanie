import pandas as pd
import pandas_ta as ta

tickers = {
    "PKN": "pkn",
    "PKO": "pko",
    "PEO": "peo",
    "PZU": "pzu",
    "KGH": "kgh",
    "CDR": "cdr",
    "LPP": "lpp",
    "DNP": "dnp"
}

all_trades = []

for name, symbol in tickers.items():
    url = f"https://stooq.pl/q/d/l/?s={symbol}&i=d"
    df = pd.read_csv(url)

    if df.empty or len(df) < 250:
        continue

    df["RSI"] = ta.rsi(df["Zamkniecie"], 14)
    df["EMA200"] = ta.ema(df["Zamkniecie"], 200)
    df = df.dropna().copy()

    position = False
    entry_price = None
    entry_date = None

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        row = df.iloc[i]

        rsi_prev = float(prev["RSI"])
        rsi = float(row["RSI"])
        close = float(row["Zamkniecie"])
        ema200 = float(row["EMA200"])

        # WEJŚCIE
        if not position:
            if rsi_prev < 35 and rsi >= 35 and close > ema200:
                position = True
                entry_price = close
                entry_date = row["Data"]

        # WYJŚCIE
        else:
            stop_loss = entry_price * 0.97
            take_profit = entry_price * 1.04

            if close <= stop_loss or close >= take_profit or rsi > 65:
                exit_price = close
                exit_date = row["Data"]

                profit = (exit_price - entry_price) / entry_price * 100

                all_trades.append({
                    "Market": "GPW",
                    "Ticker": name,
                    "Entry Date": entry_date,
                    "Exit Date": exit_date,
                    "Entry": round(entry_price, 2),
                    "Exit": round(exit_price, 2),
                    "Profit %": round(profit, 2)
                })

                position = False

results = pd.DataFrame(all_trades)
results.to_csv("data/backtest_GPW_multi.csv", index=False)

print("GPW – liczba transakcji:", len(results))
if not results.empty:
    print("Średni wynik %:", round(results["Profit %"].mean(), 2))
    print("Skuteczność %:", round((results["Profit %"] > 0).mean() * 100, 2))
