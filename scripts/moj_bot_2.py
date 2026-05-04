import yfinance as yf
import pandas as pd

# 1. Tworzymy SŁOWNIK (dictionary) kategorii i spółek
portfel = {
    "🤖 Sztuczna Inteligencja i Big Tech": ['NVDA', 'MSFT', 'PLTR', 'GOOGL', 'META'],
    "🚗 Motoryzacja i Pojazdy Elektryczne (EV)": ['TSLA', 'RIVN', 'F', 'GM'],
    "🏥 Medycyna i BioTech": ['PFE', 'JNJ', 'NVO', 'UNH'],
    "💸 Finanse i Bankowość": ['JPM', 'V', 'MA'],
    "🇵🇱 Polska Giełda (GPW)": ['PKO.WA', 'PEO.WA', 'CDR.WA', 'XTB.WA', 'ALE.WA']
}

def analizuj_spolke_pro(ticker):
    try:
        # Pobieranie danych
        dane = yf.download(ticker, period="1y", interval="1d", progress=False)

        if dane.empty or len(dane) < 50:
            return f"[{ticker:<6}] Brak wystarczających danych do analizy"

        # --- Obliczenia ---
        # Średni wolumen i dzisiejszy
        dane['Średni_Wolumen_20'] = dane['Volume'].rolling(window=20).mean()
        dzisiejszy_wolumen = dane['Volume'].iloc[-1].item()
        sredni_wolumen = dane['Średni_Wolumen_20'].iloc[-1].item()
        skok_wolumenu = dzisiejszy_wolumen > (sredni_wolumen * 1.5)

        # Zmienność (ATR uproszczony do %)
        dane['Dzienny_Zasieg'] = (dane['High'] - dane['Low']) / dane['Close'] * 100
        atr_procentowy = dane['Dzienny_Zasieg'].rolling(window=14).mean().iloc[-1].item()

        # Trend (Średnia 50-dniowa)
        dane['SMA_50'] = dane['Close'].rolling(window=50).mean()
        ostatnia_cena = dane['Close'].iloc[-1].item()
        sma50 = dane['SMA_50'].iloc[-1].item()
        trend_wzrostowy = ostatnia_cena > sma50

        # --- Ocenianie statusu ---
        status = "⚪ Neutralnie (Brak silnych sygnałów)"
        if skok_wolumenu and trend_wzrostowy and atr_procentowy > 2.0:
            status = "🔥 GORĄCY RODZYNEK! (Kapitał wchodzi do spółki)"
        elif skok_wolumenu and not trend_wzrostowy:
            status = "⚠️ UWAGA (Możliwa wyprzedaż/panika)"
        elif trend_wzrostowy:
            status = "🟢 Spokojny wzrost"

        # Budowa pojedynczej linijki raportu
        raport = f"[{ticker:<6}] Cena: {ostatnia_cena:>7.2f} | Wolumen: {'Wyższy' if skok_wolumenu else 'Norma'} | Ruch/Zmienność: {atr_procentowy:>4.1f}% | {status}"
        return raport
        
    except Exception as e:
        return f"[{ticker:<6}] Wystąpił błąd podczas analizy"

# 2. Główna pętla programu generująca raport z podziałem
print("="*85)
print(" 📊 SKANER SEKTOROWY: W POSZUKIWANIU ZMIENNOŚCI I TRENDÓW")
print("="*85)

# Pętla przechodzi przez każdą kategorię (klucz) i listę spółek (wartość) w naszym słowniku
for nazwa_sektora, lista_spolek in portfel.items():
    print(f"\n{nazwa_sektora.upper()}")
    print("-" * 85)
    
    # Wewnętrzna pętla analizuje spółki tylko w danym sektorze
    for spolka in lista_spolek:
        wynik = analizuj_spolke_pro(spolka)
        if wynik:
            print(wynik)
            
print("\n" + "="*85)