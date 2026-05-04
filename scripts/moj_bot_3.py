import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
import json
import os
import argparse

warnings.filterwarnings('ignore')

# ==========================================
# 1. OBSŁUGA "PAMIĘCI" BOTA
# ==========================================
PLIK_PORTFELA = "moje_grupy.json"

domyslne_grupy = {
    "💼 MÓJ PORTFEL": ['PKO.WA', 'AAPL','AMD','KGH.WA','PKN','GOOGL','NESTE','12DA'],
    "🤖 Big Tech & AI": ['MSFT', 'NVDA'],
    "🏦 Finanse i GPW": ['PEO.WA', 'XTB.WA'],
    #"🛢️ Surowce (Złoto, Srebro, Ropa)": ['GLD', 'SLV', 'XOM'], 
    #"🪙 Kryptowaluty": ['BTC-USD', 'ETH-USD']
}

def zaladuj_portfel():
    if not os.path.exists(PLIK_PORTFELA):
        zapisz_portfel(domyslne_grupy)
        return domyslne_grupy
    with open(PLIK_PORTFELA, 'r', encoding='utf-8') as f:
        return json.load(f)

def zapisz_portfel(grupy):
    with open(PLIK_PORTFELA, 'w', encoding='utf-8') as f:
        json.dump(grupy, f, indent=4, ensure_ascii=False)

# ==========================================
# 2. SILNIK ANALITYCZNY
# ==========================================
konfiguracja_interwalow = {
    "1h": "3mo",   
    "4h": "1y",    
    "1d": "2y",    
    "1wk": "10y"   
}

def pobierz_dane_wskaznikow(ticker, interwal, zakres):
    try:
        dane = yf.download(ticker, period=zakres, interval=interwal, progress=False)
        if dane.empty or len(dane) < 200:
            return None

        dane['SMA_50'] = dane['Close'].rolling(window=50).mean()
        dane['SMA_200'] = dane['Close'].rolling(window=200).mean()

        delta = dane['Close'].diff()
        zysk = delta.where(delta > 0, 0)
        strata = -delta.where(delta < 0, 0)
        srednia_zyskow = zysk.ewm(alpha=1/14, adjust=False).mean()
        srednia_strat = strata.ewm(alpha=1/14, adjust=False).mean()
        rs = srednia_zyskow / srednia_strat
        dane['RSI'] = 100 - (100 / (1 + rs))

        ema_12 = dane['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = dane['Close'].ewm(span=26, adjust=False).mean()
        dane['MACD'] = ema_12 - ema_26
        dane['Signal_Line'] = dane['MACD'].ewm(span=9, adjust=False).mean()

        ostatnia_cena = round(dane['Close'].iloc[-1].item(), 2)
        rsi = round(dane['RSI'].iloc[-1].item(), 1)
        macd = dane['MACD'].iloc[-1].item()
        sygnal_macd = dane['Signal_Line'].iloc[-1].item()
        sma50 = dane['SMA_50'].iloc[-1].item()
        sma200 = dane['SMA_200'].iloc[-1].item()

        stan_krzyza = "Brak trendu"
        if sma50 > sma200: stan_krzyza = "✨ Złoty Krzyż"
        elif sma50 < sma200: stan_krzyza = "☠️ Krzyż Śmierci"

        macd_rosnie = macd > sygnal_macd 
        macd_maleje = macd < sygnal_macd 

        decyzja = "⚪ Czekaj"
        if (30 <= rsi <= 50) and macd_rosnie: decyzja = "🟢 KUPUJ"
        elif rsi >= 70 and macd_maleje: decyzja = "🔴 SPRZEDAJ"

        return {"Cena": ostatnia_cena, "Trend": stan_krzyza, "RSI": rsi, "Decyzja": decyzja}
    except Exception:
        return None

# ==========================================
# 3. GŁÓWNY MODUŁ PODSUMOWANIA (TWÓJ ALGORYTM DECYZYJNY)
# ==========================================
#generuj_ostateczna_decyzje(dane_spolki):
#"""Bierze dane ze wszystkich 4 interwałów i wyciąga jeden wniosek."""
#
## Zabezpieczenie na wypadek braku danych dla jakiegoś interwału
#if not all(k in dane_spolki for k in ['1h', '4h', '1d', '1wk']):
#    return "⚠️ Błąd danych (zbyt mało historii na ocenę)"
#
#trend_dlugi = dane_spolki['1wk']['Trend']
#decyzja_1d = dane_spolki['1d']['Decyzja']
#decyzja_4h = dane_spolki['4h']['Decyzja']
#decyzja_1h = dane_spolki['1h']['Decyzja']
#
#hossa = "Złoty Krzyż" in trend_dlugi
#bessa = "Krzyż Śmierci" in trend_dlugi
#
#sygnal_kupna_krotki = "KUPUJ" in decyzja_1h or "KUPUJ" in decyzja_4h
#sygnal_sprzedazy_krotki = "SPRZEDAJ" in decyzja_1h or "SPRZEDAJ" in decyzja_4h
#
## Logika wielookresowa
#if hossa and sygnal_kupna_krotki:
#    return "🔥 PERFEKCYJNE WEJŚCIE (Długi trend wspiera krótki sygnał kupna)"
#elif bessa and sygnal_sprzedazy_krotki:
#    return "🚨 SILNE SPADKI (Uciekaj / Sprzedawaj krótko)"
#elif sygnal_kupna_krotki:
#    return "🟢 KUPUJ (Sygnał krótkoterminowy, ale bez wsparcia wielkiego trendu)"
#elif sygnal_sprzedazy_krotki:
#    return "🔴 SPRZEDAJ (Realizuj zyski, słabnące momentum)"
#elif hossa and "Czekaj" in decyzja_1h and "Czekaj" in decyzja_4h:
#    return "⚪ CZEKAJ (Dobry trend, ale brak momentu do wejścia)"
#else:
#    return "⚪ IGNORUJ (Brak klarownej sytuacji na wykresach)"

# ==========================================
# 3. GŁÓWNY MODUŁ PODSUMOWANIA (ZAKTUALIZOWANY Z 1D)
# ==========================================
def generuj_ostateczna_decyzje(dane_spolki):
    """Bierze dane ze wszystkich 4 interwałów i wyciąga jeden wniosek."""
    
    if not all(k in dane_spolki for k in ['1h', '4h', '1d', '1wk']):
        return "⚠️ Błąd danych (zbyt mało historii na ocenę)"

    # Pobieranie trendów długoterminowych
    trend_1wk = dane_spolki['1wk']['Trend']
    trend_1d = dane_spolki['1d']['Trend']

    # Pobieranie sygnałów RSI+MACD
    sygnal_1d = dane_spolki['1d']['Decyzja']
    sygnal_4h = dane_spolki['4h']['Decyzja']
    sygnal_1h = dane_spolki['1h']['Decyzja']

    # --- TŁUMACZENIE SYTUACJI NA RYNKU ---
    silna_hossa = "Złoty Krzyż" in trend_1wk or "Złoty Krzyż" in trend_1d
    silna_bessa = "Krzyż Śmierci" in trend_1wk or "Krzyż Śmierci" in trend_1d
    
    kupno_krotkie = "KUPUJ" in sygnal_1h or "KUPUJ" in sygnal_4h
    kupno_dzienne = "KUPUJ" in sygnal_1d
    
    sprzedaz_krotka = "SPRZEDAJ" in sygnal_1h or "SPRZEDAJ" in sygnal_4h
    sprzedaz_dzienna = "SPRZEDAJ" in sygnal_1d

    # --- NOWA, POTĘŻNA LOGIKA WIELOOKRESOWA ---
    if silna_hossa and kupno_dzienne and kupno_krotkie:
        return "🔥 ALL-IN KUPUJ (Hossa + Dzienny wzrost + Idealny moment 1h/4h)"
        
    elif silna_hossa and kupno_dzienne:
        return "🟢 KUPUJ (Silny trend główny i rosnąca świeca dzienna)"
        
    elif silna_bessa and (sprzedaz_dzienna or sprzedaz_krotka):
        return "🚨 UCIEKAJ / SPRZEDAJ (Bessa + Sygnały sprzedaży)"
        
    elif kupno_dzienne and kupno_krotkie:
        return "🟡 SPEKULACYJNE KUPNO (Krótkie i dzienne rosną, ale wciąż brak długiej hossy)"
        
    elif sprzedaz_dzienna:
        return "🔴 SPRZEDAJ (Dzienny trend się odwraca na spadkowy - realizuj zyski)"
        
    elif silna_hossa and ("Czekaj" in sygnal_1d):
        return "⚪ OBSERWUJ (Spółka w świetnej hossie, czekamy na ochłodzenie RSI)"
        
    else:
        return "⚪ IGNORUJ (Szum rynkowy, brak zgodności wskaźników)"
# ==========================================
# 4. OBSŁUGA KONSOLI I EKSPORT
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dodaj', type=str)
    parser.add_argument('--usun', type=str)
    args = parser.parse_args()

    moje_grupy = zaladuj_portfel()
    KLUCZ_PORTFELA = "💼 MÓJ PORTFEL"

    if args.dodaj:
        symbol = args.dodaj.upper()
        if symbol not in moje_grupy[KLUCZ_PORTFELA]:
            moje_grupy[KLUCZ_PORTFELA].append(symbol)
            zapisz_portfel(moje_grupy)
            print(f"✅ Dodano {symbol} do portfela.")
        exit()

    if args.usun:
        symbol = args.usun.upper()
        if symbol in moje_grupy[KLUCZ_PORTFELA]:
            moje_grupy[KLUCZ_PORTFELA].remove(symbol)
            zapisz_portfel(moje_grupy)
            print(f"🗑️ Usunięto {symbol} z portfela.")
        exit()

    print("="*70)
    print(" 🚀 TRWA ZBIERANIE DANYCH Z RYNKU (Może to potrwać kilkanaście sekund)...")
    print("="*70)

    # Zbieranie wszystkich danych do jednego słownika
    wyniki_wszystkie = {} 
    
    for nazwa_grupy, lista_spolek in moje_grupy.items():
        for spolka in lista_spolek:
            if spolka not in wyniki_wszystkie:
                wyniki_wszystkie[spolka] = {"Grupa": nazwa_grupy, "Dane": {}}
            
            for interwal, zakres in konfiguracja_interwalow.items():
                wynik = pobierz_dane_wskaznikow(spolka, interwal, zakres)
                if wynik:
                    wyniki_wszystkie[spolka]["Dane"][interwal] = wynik

    # Generowanie Podsumowania
    lista_podsumowania = []
    lista_rekomendacji_akcji = [] # Do wyświetlenia na ekranie
    
    for spolka, info in wyniki_wszystkie.items():
        grupa = info["Grupa"]
        dane_interwalow = info["Dane"]
        
        ostateczna_decyzja = generuj_ostateczna_decyzje(dane_interwalow)
        ostatnia_cena = dane_interwalow.get('1d', {}).get('Cena', 'Brak')
        
        lista_podsumowania.append({
            "Grupa": grupa,
            "Symbol": spolka,
            "Aktualna Cena": ostatnia_cena,
            "REKOMENDACJA BOTA": ostateczna_decyzja,
            "Trend Długi (1wk)": dane_interwalow.get('1wk', {}).get('Trend', '-'),
            "Sygnał Krótki (1h)": dane_interwalow.get('1h', {}).get('Decyzja', '-')
        })

        # Zbieramy tylko gorące sygnały do pokazania w terminalu
        if "🔥" in ostateczna_decyzja or "🟢" in ostateczna_decyzja or "🚨" in ostateczna_decyzja or "🔴" in ostateczna_decyzja:
            lista_rekomendacji_akcji.append(f"[{spolka:<6}] Cena: {ostatnia_cena:>7} -> {ostateczna_decyzja}")

    # Zapis do Excela
    data_raportu = datetime.now().strftime('%Y-%m-%d_%H-%M')
    nazwa_pliku = f"Raport_{data_raportu}.xlsx"

    with pd.ExcelWriter(nazwa_pliku, engine='openpyxl') as writer:
        # 1. Zakładka GŁÓWNA - PODSUMOWANIE
        df_podsumowanie = pd.DataFrame(lista_podsumowania)
        df_podsumowanie.to_excel(writer, sheet_name="🌟 PODSUMOWANIE", index=False)
        
        # 2. Zakładki szczegółowe (jak było wcześniej) dla każdego interwału
        for interwal in konfiguracja_interwalow.keys():
            dane_zakladki = []
            for spolka, info in wyniki_wszystkie.items():
                if interwal in info["Dane"]:
                    wiersz = {"Grupa": info["Grupa"], "Symbol": spolka}
                    wiersz.update(info["Dane"][interwal])
                    dane_zakladki.append(wiersz)
            if dane_zakladki:
                pd.DataFrame(dane_zakladki).to_excel(writer, sheet_name=f"Szczegóły_{interwal}", index=False)

    # Wyświetlanie samych konkretów dla Ciebie na ekranie:
    print("\n🎯 AKCJE WYMAGAJĄCE TWOJEJ UWAGI (Główne Sygnały):")
    print("-" * 70)
    if not lista_rekomendacji_akcji:
        print("Brak mocnych sygnałów kupna/sprzedaży. Rynek jest dziś spokojny.")
    else:
        for alert in lista_rekomendacji_akcji:
            print(alert)
    print("-" * 70)
    print(f"Pełne dane i szczegóły interwałów zapisane w pliku: {nazwa_pliku}\n")