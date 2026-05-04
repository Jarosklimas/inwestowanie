import pandas as pd
import pandas_ta as ta

tickers = ["pkn", "pzu", "kgh", "pko", "cdr", "lpp", "pep", "tsg"]  # Twoja lista GPW

results = []

for symbol in tickers:
    try:
        url = f"https://stooq.pl/q/d/l/?s={symbol}&i=d"
        df = pd.read_csv(url)
        if df.empty:
            continue
        df["RSI"] = ta.rsi(df["Zamkniecie"], length=14)
        last_rsi = df["RSI"].iloc[-1]
        if last_rsi < 35:
            results.append({"Ticker": symbol.upper(), "RSI": round(last_rsi, 2)})
    except Exception as e:
        print(f"Błąd dla {symbol}: {e}")

results_df = pd.DataFrame(results)
results_df.to_csv("data/gpw_rsi_below_35.csv", index=False)
print(results_df)
