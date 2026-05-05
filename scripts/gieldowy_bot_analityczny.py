import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
import json
import os
import argparse
import requests

warnings.filterwarnings('ignore')

PLIK_PORTFELA = "invest_grupy.json"

# Bezpieczne pobieranie kluczy
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip(' \'"')
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip(' \'"')

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

# --- ULEPSZONA FUNKCJA: WYSYŁANIE PLIKÓW ---
def wyslij_telegram(wiadomosc, sciezka_do_pliku=None):
    """Wysyła wiadomość tekstową oraz opcjonalnie załącznik plikowy"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Brak kluczy Telegram. Wiadomość pokazana tylko w konsoli.")
        return
        
    try:
        if sciezka_do_pliku and os.path.exists(sciezka_do_pliku):
            # Tryb wysyłania DOKUMENTU (Pliku Excel)
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
            with open(sciezka_do_pliku, 'rb') as plik:
                files = {'document': plik}
                payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": wiadomosc, "parse_mode": "HTML"}
                r = requests.post(url, data=payload, files=files)
        else:
            # Tryb wysyłania SAMEJ WIADOMOŚCI
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": wiadomosc, "parse_mode": "HTML"}
            r = requests.post(url, data=payload)

        if r.status_code != 200:
            print(f"❌ Odrzucono przez Telegram! Kod: {r.status_code} | Powód: {r.text}")
        else:
            print("✅ Raport wysłany na Telegram z sukcesem!")
            
    except Exception as e:
        print(f"❌ Krytyczny błąd połączenia z Telegramem: {e}")

# ==========================================
# GŁÓWNY SILNIK ANALITYCZNY
# ==========================================
konfiguracja_interwalow = {"1h": "3mo", "4h": "1y", "1d": "2y", "1wk": "10y"}

def pobierz_dane_wskaznikow(ticker, interwal, zakres):
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

        dane['High-Low'] = dane['High'] - dane['Low']
        dane['High-PrevClose'] = abs(dane['High'] - dane['Close'].shift(1))
        dane['Low-PrevClose'] = abs(dane['Low'] - dane['Close'].shift(1))
        dane['TrueRange'] = dane[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
        dane['ATR'] = dane['TrueRange'].rolling(window=14).mean()

        ostatnia_cena = round(dane['Close'].iloc[-1].item(), 2)
        rsi = round(dane['RSI'].iloc[-1].item(), 1)
        macd = dane['MACD'].iloc[-1].item()
        sygnal_macd = dane['Signal_Line'].iloc[-1].item()
        atr = dane['ATR'].iloc[-1].item()
        
        stop_loss = round(ostatnia_cena - (1.5 * atr), 2)
        
        stan_krzyza = "Brak trendu"
        if dane['SMA_50'].iloc[-1].item() > dane['SMA_200'].iloc[-1].item(): stan_krzyza = "✨ Złoty Krzyż"
        elif dane['SMA_50'].iloc[-1].item() < dane['SMA_200'].iloc[-1].item(): stan_krzyza = "☠️ Krzyż Śmierci"

        decyzja = "⚪ Czekaj"
        if (30 <= rsi <= 50) and (macd > sygnal_macd): decyzja = "🟢 KUPUJ"
        elif rsi >= 70 and (macd < sygnal_macd): decyzja = "🔴 SPRZEDAJ"

        return {"Cena": ostatnia_cena, "Trend": stan_krzyza, "RSI": rsi, "Decyzja": decyzja, "Stop_Loss": stop_loss}
    except Exception: return None

def generuj_ostateczna_decyzje(dane_spolki):
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

    if args.usun_grupe:
        if args.usun_grupe in moje_grupy:
            del moje_grupy[args.usun_grupe]
            zapisz_portfel(moje_grupy)
        exit()
    if args.dodaj:
        symbol, grupa = args.dodaj.upper(), args.grupa
        if grupa not in moje_grupy: moje_grupy[grupa] = []
        if symbol not in moje_grupy[grupa]:
            moje_grupy[grupa].append(symbol)
            zapisz_portfel(moje_grupy)
        exit()
    if args.usun:
        symbol, grupa = args.usun.upper(), args.grupa
        if grupa in moje_grupy and symbol in moje_grupy[grupa]:
            moje_grupy[grupa].remove(symbol)
            zapisz_portfel(moje_grupy)
        exit()

    # --- ZBIERANIE DANYCH ---
    wyniki_wszystkie = {} 
    for nazwa_grupy, lista_spolek in moje_grupy.items():
        for spolka in lista_spolek:
            if spolka not in wyniki_wszystkie:
                wyniki_wszystkie[spolka] = {"Grupa": nazwa_grupy, "Dane": {}}
            for interwal, zakres in konfiguracja_interwalow.items():
                wynik = pobierz_dane_wskaznikow(spolka, interwal, zakres)
                if wynik: wyniki_wszystkie[spolka]["Dane"][interwal] = wynik

    # --- TWORZENIE PLIKU EXCEL ---
    data_raportu = datetime.now().strftime('%Y-%m-%d_%H-%M')
    nazwa_pliku = f"Raport_Gieldowy_{data_raportu}.xlsx"
    lista_podsumowania = []
    
    # Tworzymy listę do głównej zakładki
    for spolka, info in wyniki_wszystkie.items():
        decyzja = generuj_ostateczna_decyzje(info["Dane"])
        cena = info["Dane"].get('1d', {}).get('Cena', 'Brak')
        sl = info["Dane"].get('1d', {}).get('Stop_Loss', 'Brak')
        
        lista_podsumowania.append({
            "Grupa": info["Grupa"],
            "Symbol": spolka,
            "Cena": cena,
            "REKOMENDACJA": decyzja,
            "Stop Loss (1d)": sl,
            "Trend Główny (1wk)": info["Dane"].get('1wk', {}).get('Trend', '-'),
            "RSI Dzienny (1d)": info["Dane"].get('1d', {}).get('RSI', '-')
        })

    with pd.ExcelWriter(nazwa_pliku, engine='openpyxl') as writer:
        pd.DataFrame(lista_podsumowania).to_excel(writer, sheet_name="🌟 PODSUMOWANIE", index=False)
        for interwal in konfiguracja_interwalow.keys():
            dane_zakladki = []
            for spolka, info in wyniki_wszystkie.items():
                if interwal in info["Dane"]:
                    wiersz = {"Grupa": info["Grupa"], "Symbol": spolka}
                    wiersz.update(info["Dane"][interwal])
                    dane_zakladki.append(wiersz)
            if dane_zakladki:
                pd.DataFrame(dane_zakladki).to_excel(writer, sheet_name=f"Szczegóły_{interwal}", index=False)

    # --- BUDOWANIE WIADOMOŚCI TELEGRAM ---
    wiadomosc_telegram = "<b>🤖 TWÓJ RAPORT GIEŁDOWY:</b>\n\n"
    znaleziono_sygnaly = False

    for spolka, info in wyniki_wszystkie.items():
        decyzja = generuj_ostateczna_decyzje(info["Dane"])
        cena = info["Dane"].get('1d', {}).get('Cena', 'Brak')
        sugerowany_sl = info["Dane"].get('1d', {}).get('Stop_Loss', 'Brak')
        
        if "🔥" in decyzja or "🟢" in decyzja or "🚨" in decyzja or "🔴" in decyzja:
            wiadomosc_telegram += f"[{spolka}] Cena: <b>{cena}</b>\n👉 {decyzja}\n"
            if "KUPUJ" in decyzja:
                wiadomosc_telegram += f"🛡️ SL: {sugerowany_sl}\n"
            wiadomosc_telegram += "\n"
            znaleziono_sygnaly = True

    # Niezależnie od sygnałów, ZAWSZE wysyłamy plik na Telegram
    if not znaleziono_sygnaly:
        wiadomosc_telegram += "⚪ <b>Rynek stabilny.</b> Brak nowych mocnych sygnałów (wszystko w statusie Czekaj/Ignoruj).\n\n"
        
    wiadomosc_telegram += "📊 <i>Pełna analiza wszystkich wskaźników znajduje się w załączonym pliku Excel.</i>"

    # WYSYŁKA
    wyslij_telegram(wiadomosc_telegram, sciezka_do_pliku=nazwa_pliku)