import yfinance as yf
import pandas as pd

# Zdefiniuj spółki (dodaj .WA dla polskich)
spolki = ['AAPL', 'MSFT', 'TSLA', 'PKO.WA', 'CDR.WA', 'PEO.WA']

def analizuj_spolke(ticker):
    try:
        # Pobieramy dane z 2 lat, bo potrzebujemy 200 dni do średniej
        dane = yf.download(ticker, period="2y", interval="1d", progress=False)

        if dane.empty or len(dane) < 200:
            return f"{ticker:<10} | Błąd: Zbyt mało danych rynkowych"

        # 1. Średnie do Złotego Krzyża i Krzyża Śmierci (SMA 50 i SMA 200)
        dane['SMA_50'] = dane['Close'].rolling(window=50).mean()
        dane['SMA_200'] = dane['Close'].rolling(window=200).mean()

        # 2. Obliczanie RSI (14-dniowe)
        delta = dane['Close'].diff()
        zysk = delta.where(delta > 0, 0)
        strata = -delta.where(delta < 0, 0)
        srednia_zyskow = zysk.ewm(alpha=1/14, adjust=False).mean()
        srednia_strat = strata.ewm(alpha=1/14, adjust=False).mean()
        rs = srednia_zyskow / srednia_strat
        dane['RSI'] = 100 - (100 / (1 + rs))

        # 3. Obliczanie MACD (12 i 26 dni)
        ema_12 = dane['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = dane['Close'].ewm(span=26, adjust=False).mean()
        dane['MACD'] = ema_12 - ema_26
        dane['Signal_Line'] = dane['MACD'].ewm(span=9, adjust=False).mean() # Linia Sygnału

        # Wyciąganie najnowszych wartości z dzisiejszej sesji
        ostatnia_cena = dane['Close'].iloc[-1].item()
        rsi = dane['RSI'].iloc[-1].item()
        macd = dane['MACD'].iloc[-1].item()
        sygnal_macd = dane['Signal_Line'].iloc[-1].item()
        sma50 = dane['SMA_50'].iloc[-1].item()
        sma200 = dane['SMA_200'].iloc[-1].item()

        # Analiza Długoterminowa (Krzyże)
        stan_krzyza = "[Brak trendu]"
        if sma50 > sma200:
            stan_krzyza = "✨ Złoty Krzyż (Hossa)"
        elif sma50 < sma200:
            stan_krzyza = "☠️ Krzyż Śmierci (Bessa)"

        # Logika sygnałów (TWOJE ZAŁOŻENIA)
        decyzja = "⚪ CZEKAJ"
        
        # MACD rosnące oznacza, że MACD przebiło Linię Sygnału w górę
        macd_rosnie = macd > sygnal_macd 
        # MACD malejące oznacza, że MACD spadło poniżej Linii Sygnału
        macd_maleje = macd < sygnal_macd 

        if (30 <= rsi <= 50) and macd_rosnie:
            decyzja = "🟢 KUPUJ (Dobre RSI + MACD rośnie)"
        elif rsi >= 70 and macd_maleje:
            decyzja = "🔴 SPRZEDAJ/ZATRZYMAJ (Przegrzane RSI + MACD spada)"

        # Budowa czytelnego raportu
        raport = (
            f"Spółka: {ticker:<8} | Cena: {ostatnia_cena:>8.2f} \n"
            f"   Trend długoterminowy: {stan_krzyza} \n"
            f"   RSI:  {rsi:>5.1f} \n"
            f"   WYNIK: {decyzja}\n"
            f"   {'-'*50}"
        )
        return raport
        
    except Exception as e:
        return f"Spółka: {ticker:<8} | Błąd podczas obliczeń: {str(e)}\n   {'-'*50}"

# Uruchomienie Bota
print("="*55)
print(" 🚀 INTELIGENTNY SKANER GIEŁDOWY (RSI + MACD + SMA)")
print("="*55)

for spolka in spolki:
    wynik = analizuj_spolke(spolka)
    print(wynik)