import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
import json
import os
import argparse
import requests

warnings.filterwarnings('ignore')

PLIK_PORTFELA = "moje_grupy.json"
# Klucze Telegram zaciągane z bezpiecznego środowiska (GitHub Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip(' \'"')
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip(' \'"')

# --- DODAJ TE DWIE LINIJKI DO TESTÓW ---
print(f"🔍 DEBUG KLUczy: Token załadowany: {'TAK' if TELEGRAM_TOKEN else 'NIE'}")
print(f"🔍 DEBUG KLUczy: Chat ID załadowany: {'TAK' if TELEGRAM_CHAT_ID else 'NIE'}")
# --------------------------------------

domyslne_grupy = {"💼 MÓJ PORTFEL": ['PKO.WA', 'AAPL']}

def zaladuj_portfel():
    if not os.path.exists(PLIK_PORTFELA):
        with open(PLIK_PORTFELA, 'w', encoding='utf-8') as f:
            json.dump(domyslne_grupy, f, indent=4, ensure_ascii=False)
        return domyslne_grupy
    with open(PLIK_PORTFELA, 'r', encoding='utf-8') as f:
        return json.load(f)

def zapisz_portfel(grupy):
    with open(PLIK_PORTFELA, 'w', encoding='utf-8') as f:
        json.dump(grupy, f, indent=4, ensure_ascii=False)

def wyslij_telegram(wiadomosc):
    """Funkcja wysyłająca powiadomienie na Twój telefon"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Brak kluczy Telegram. Wiadomość pokazana tylko w konsoli.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": wiadomosc, "parse_mode": "HTML"}
   try:
        r = requests.post(url, data=payload)
        # Zmuszamy bota do powiedzenia nam prawdy o statusie wysyłki!
        if r.status_code != 200:
            print(f"❌ Odrzucono przez Telegram! Kod: {r.status_code} | Powód: {r.text}")
        else:
            print("✅ Wiadomość Telegram wysłana do Ciebie z pełnym sukcesem!")
    except Exception as e:
        print(f"❌ Krytyczny błąd połączenia z Telegramem: {e}")

konfiguracja_interwalow = {"1h": "3mo", "4h": "1y", "1d": "2y", "1wk": "10y"}

def pobierz_dane_wskaznikow(ticker, interwal, zakres):
    # (Tutaj znajduje się cała matematyka RSI/MACD/Krzyże z poprzedniego kodu)
    try:
        dane = yf.download(ticker, period=zakres, interval=interwal, progress=False)
        if dane.empty or len(dane) < 200: return None

        dane['SMA_50'] = dane['Close'].rolling(window=50).mean()
        dane['SMA_200'] = dane['Close'].rolling(window=200).mean()
        delta = dane['Close'].diff()
        rs = (delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()) / (-delta.where(delta < 0, 0).ewm(alpha=1/14, adjust=False).mean())
        dane['RSI'] = 100 - (100 / (1 + rs))
        dane['MACD'] = dane['Close'].ewm(span=12, adjust=False).mean() - dane['Close'].ewm(span=26, adjust=False).mean()
        dane['Signal_Line'] = dane['MACD'].ewm(span=9, adjust=False).mean()

        ostatnia_cena = round(dane['Close'].iloc[-1].item(), 2)
        rsi = round(dane['RSI'].iloc[-1].item(), 1)
        macd = dane['MACD'].iloc[-1].item()
        sygnal_macd = dane['Signal_Line'].iloc[-1].item()
        
        stan_krzyza = "Brak trendu"
        if dane['SMA_50'].iloc[-1].item() > dane['SMA_200'].iloc[-1].item(): stan_krzyza = "✨ Złoty Krzyż"
        elif dane['SMA_50'].iloc[-1].item() < dane['SMA_200'].iloc[-1].item(): stan_krzyza = "☠️ Krzyż Śmierci"

        decyzja = "⚪ Czekaj"
        if (30 <= rsi <= 50) and (macd > sygnal_macd): decyzja = "🟢 KUPUJ"
        elif rsi >= 70 and (macd < sygnal_macd): decyzja = "🔴 SPRZEDAJ"

        return {"Cena": ostatnia_cena, "Trend": stan_krzyza, "RSI": rsi, "Decyzja": decyzja}
    except Exception: return None

def generuj_ostateczna_decyzje(dane_spolki):
    # (Logika Multi-Timeframe z 1D włączonym do decyzji)
    if not all(k in dane_spolki for k in ['1h', '4h', '1d', '1wk']): return "⚠️ Błąd danych"
    hossa = "Złoty Krzyż" in dane_spolki['1wk']['Trend'] or "Złoty Krzyż" in dane_spolki['1d']['Trend']
    bessa = "Krzyż Śmierci" in dane_spolki['1wk']['Trend'] or "Krzyż Śmierci" in dane_spolki['1d']['Trend']
    kupno_krotkie = "KUPUJ" in dane_spolki['1h']['Decyzja'] or "KUPUJ" in dane_spolki['4h']['Decyzja']
    kupno_dzienne = "KUPUJ" in dane_spolki['1d']['Decyzja']
    sprzedaz_krotka = "SPRZEDAJ" in dane_spolki['1h']['Decyzja'] or "SPRZEDAJ" in dane_spolki['4h']['Decyzja']
    sprzedaz_dzienna = "SPRZEDAJ" in dane_spolki['1d']['Decyzja']

    if hossa and kupno_dzienne and kupno_krotkie: return "🔥 ALL-IN KUPUJ"
    elif hossa and kupno_dzienne: return "🟢 KUPUJ (Mocny trend Dzienny)"
    elif bessa and (sprzedaz_dzienna or sprzedaz_krotka): return "🚨 UCIEKAJ / SPRZEDAJ"
    elif kupno_dzienne and kupno_krotkie: return "🟡 SPEKULACYJNE KUPNO"
    elif sprzedaz_dzienna: return "🔴 SPRZEDAJ (Realizuj zyski)"
    elif hossa and ("Czekaj" in dane_spolki['1d']['Decyzja']): return "⚪ OBSERWUJ"
    else: return "⚪ IGNORUJ"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dodaj', type=str, help="Symbol do dodania")
    parser.add_argument('--usun', type=str, help="Symbol do usunięcia")
    parser.add_argument('--usun_grupe', type=str, help="Cała grupa do usunięcia")
    parser.add_argument('--grupa', type=str, default="💼 MÓJ PORTFEL", help="Nazwa grupy")
    args = parser.parse_args()

    moje_grupy = zaladuj_portfel()

    # --- ZARZĄDZANIE PORTFELEM ---
    if args.usun_grupe:
        if args.usun_grupe in moje_grupy:
            del moje_grupy[args.usun_grupe]
            zapisz_portfel(moje_grupy)
            print(f"🗑️ Usunięto całą grupę: {args.usun_grupe}")
        exit()

    if args.dodaj:
        symbol, grupa = args.dodaj.upper(), args.grupa
        if grupa not in moje_grupy: moje_grupy[grupa] = []
        if symbol not in moje_grupy[grupa]:
            moje_grupy[grupa].append(symbol)
            zapisz_portfel(moje_grupy)
            print(f"✅ Dodano {symbol} do: {grupa}")
        exit()

    if args.usun:
        symbol, grupa = args.usun.upper(), args.grupa
        if grupa in moje_grupy and symbol in moje_grupy[grupa]:
            moje_grupy[grupa].remove(symbol)
            zapisz_portfel(moje_grupy)
            print(f"🗑️ Usunięto {symbol} z: {grupa}")
        exit()

    # --- ANALIZA GŁÓWNA ---
    wyniki_wszystkie = {} 
    for nazwa_grupy, lista_spolek in moje_grupy.items():
        for spolka in lista_spolek:
            if spolka not in wyniki_wszystkie:
                wyniki_wszystkie[spolka] = {"Dane": {}}
            for interwal, zakres in konfiguracja_interwalow.items():
                wynik = pobierz_dane_wskaznikow(spolka, interwal, zakres)
                if wynik: wyniki_wszystkie[spolka]["Dane"][interwal] = wynik

    # --- GENEROWANIE RAPORTU ---
    wiadomosc_telegram = "<b>🤖 RAPORT GIEŁDOWY:</b>\n\n"
    znaleziono_sygnaly = False

    for spolka, info in wyniki_wszystkie.items():
        decyzja = generuj_ostateczna_decyzje(info["Dane"])
        cena = info["Dane"].get('1d', {}).get('Cena', 'Brak')
        
        if "🔥" in decyzja or "🟢" in decyzja or "🚨" in decyzja or "🔴" in decyzja:
            wiadomosc_telegram += f"[{spolka}] {cena}\n👉 {decyzja}\n\n"
            znaleziono_sygnaly = True

    if znaleziono_sygnaly:
        wyslij_telegram(wiadomosc_telegram)
        print("✅ Analiza zakończona. Raport wysłany na Telegram!")
    else:
        print("⚪ Rynek stabilny, brak mocnych sygnałów.")
        wyslij_telegram("Test GitHuba: Rynek stabilny, bot działa, ale brak mocnych sygnałów dzisiaj.")
