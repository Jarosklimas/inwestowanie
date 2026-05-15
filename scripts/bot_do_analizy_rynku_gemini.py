import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import json
import os
import argparse
import requests
import time
import random

warnings.filterwarnings('ignore')

PLIK_PORTFELA = "scripts/invest_grupy.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8725724228:AAHj-xQtVV87YQyE7ZQfdCgGyM6ICCX2520").strip(' \'"')
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "7510513100").strip(' \'"')

domyslne_grupy = {"💼 MÓJ PORTFEL": ['PKO.WA', 'AAPL', 'EURUSD=X', 'GC=F']}

# ==========================================
# PROFILE I WAGI INTERWAŁÓW
# ==========================================
WAGI_PROFILI = {
    "scalping": {"30m": 15, "1h": 45, "4h": 30, "1d": 10},
    "swing":    {"1h": 10, "4h": 20, "1d": 40, "1wk": 30},
    "invest":   {"1h": 5,  "4h": 10, "1d": 35, "1wk": 50},
}

# Dodaliśmy "30m": "1mo" do pobierania danych (Yahoo zaciągnie 1 miesiąc historii dla 30m)
KONFIG_INTERWALOW = {"30m": "1mo", "1h": "3mo", "4h": "1y", "1d": "2y", "1wk": "10y"}

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

def wyslij_telegram(wiadomosc, sciezka_do_pliku=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Brak kluczy Telegram.")
        return
    try:
        if sciezka_do_pliku and os.path.exists(sciezka_do_pliku):
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
            with open(sciezka_do_pliku, 'rb') as plik:
                r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": wiadomosc[:1024], "parse_mode": "HTML"}, files={'document': plik})
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            r = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": wiadomosc, "parse_mode": "HTML"})
    except Exception as e: print(f"❌ Błąd TG: {e}")

def ocena_ryzyka(atr_proc):
    if pd.isna(atr_proc) or atr_proc == 'Brak': return "⚪ Nieznane"
    if atr_proc < 1.5: return f"🟢 Niskie ({atr_proc}%)"
    elif atr_proc <= 4.0: return f"🟡 Średnie ({atr_proc}%)"
    elif atr_proc <= 8.0: return f"🔴 Wysokie ({atr_proc}%)"
    else: return f"💀 BARDZO WYSOKIE ({atr_proc}%)"

def ocena_rsi(rsi):
    if pd.isna(rsi): return "⚪ Brak"
    if rsi < 30: return f"🟢 Mocno wyprzedany ({rsi})"
    elif rsi < 40: return f"🟡 Wyprzedany ({rsi})"
    elif rsi > 75: return f"🔴 Mocno wykupiony ({rsi})"
    elif rsi > 60: return f"🟡 Lekko wykupiony ({rsi})"
    else: return f"⚪ Neutralny ({rsi})"

# ==========================================
# SILNIK WSKAŹNIKÓW MATEMATYCZNYCH
# ==========================================
def pobierz_dane_wskaznikow(ticker, interwal, zakres):
    try:
        dane = yf.download(ticker, period=zakres, interval=interwal, progress=False)
        if dane.empty or len(dane) < 35: return None
        if isinstance(dane.columns, pd.MultiIndex): dane.columns = dane.columns.get_level_values(0)

        c = dane['Close']
        h = dane['High']
        l = dane['Low']

        dane['SMA_50'] = c.rolling(50).mean()
        dane['SMA_200'] = c.rolling(200).mean()
        
        delta = c.diff()
        zysk = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
        strata = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        dane['RSI'] = 100 - (100 / (1 + zysk / strata.replace(0, np.nan)))
        
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        dane['MACD'] = ema12 - ema26
        dane['Signal'] = dane['MACD'].ewm(span=9, adjust=False).mean()

        sma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        dane['BB_Up'] = sma20 + 2 * std20
        dane['BB_Low'] = sma20 - 2 * std20

        l14, h14 = l.rolling(14).min(), h.rolling(14).max()
        dane['Stoch_K'] = 100 * ((c - l14) / (h14 - l14).replace(0, np.nan))
        tp = (h + l + c) / 3
        sma_tp = tp.rolling(20).mean()
        mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        dane['CCI'] = (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))

        hl = h - l
        hc = (h - c.shift(1)).abs()
        lc = (l - c.shift(1)).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        dane['ATR'] = tr.rolling(14).mean()

        cena = float(c.iloc[-1])
        atr = float(dane['ATR'].iloc[-1])
        rsi = float(dane['RSI'].iloc[-1])
        macd = float(dane['MACD'].iloc[-1])
        sygnal = float(dane['Signal'].iloc[-1])
        
        macd_trend = "📈 Wzrostowy" if macd > sygnal else "📉 Spadkowy"
        macd_crossover = "🔥 Świeży Bullish!" if (macd > sygnal and float(dane['MACD'].iloc[-2]) <= float(dane['Signal'].iloc[-2])) else ("💀 Świeży Bearish!" if (macd < sygnal and float(dane['MACD'].iloc[-2]) >= float(dane['Signal'].iloc[-2])) else "⚪ Trwający Trend")

        stan_krzyza = "⚪ Neutralny"
        if len(dane) >= 200:
            s50, s200 = float(dane['SMA_50'].iloc[-1]), float(dane['SMA_200'].iloc[-1])
            if not np.isnan(s200):
                if s50 > s200: stan_krzyza = "✨ Złoty Krzyż (Hossa)"
                elif s50 < s200: stan_krzyza = "☠️ Krzyż Śmierci (Bessa)"

        atr_proc = round((atr / cena) * 100, 2) if cena else 0.0

        lokalna_decyzja = "⚪ Czekaj"
        if macd > sygnal and rsi < 60: lokalna_decyzja = "🟢 KUPUJ"
        elif macd < sygnal and rsi > 40: lokalna_decyzja = "🔴 SPRZEDAJ"

        return {
            "Cena": round(cena, 4),
            "Lokalna_Decyzja": lokalna_decyzja,
            "Stan_Trendu": stan_krzyza,
            "MACD_Trend": macd_trend,
            "MACD_Crossover": macd_crossover,
            "Radar_RSI": ocena_rsi(round(rsi, 1)),
            "Radar_Ryzyka": ocena_ryzyka(atr_proc),
            "Stoch": round(float(dane['Stoch_K'].iloc[-1]), 1) if not np.isnan(float(dane['Stoch_K'].iloc[-1])) else "Brak",
            "CCI": round(float(dane['CCI'].iloc[-1]), 1) if not np.isnan(float(dane['CCI'].iloc[-1])) else "Brak",
            "Stop_Loss": round(cena - 2.0 * atr, 4),
            "Take_Profit_1": round(cena + 3.0 * atr, 4),
            "Take_Profit_2": round(cena + 5.0 * atr, 4),
            "Surowy_RSI": round(rsi, 1),
            "Surowy_ATR%": atr_proc
        }
    except Exception as e:
        return None

# ==========================================
# DYNAMICZNY SYSTEM OCENY (ZALEŻNY OD PROFILU)
# ==========================================
def oblicz_confidence_i_decyzje(dane_spolki, wagi_profilu, glowny_interwal):
    # Upewniamy się, że mamy dane głównego interwału
    if not isinstance(dane_spolki, dict) or glowny_interwal not in dane_spolki:
        return 0, "⚪ IGNORUJ (Brak Danych)", []

    score_total = 0
    max_waga = sum(wagi_profilu.values())
    powody = []

    for interwal, waga in wagi_profilu.items():
        if interwal in dane_spolki:
            d = dane_spolki[interwal]
            punkty_lokalne = 50 
            
            if "Wzrostowy" in d["MACD_Trend"]: punkty_lokalne += 15
            else: punkty_lokalne -= 15
            
            if d["Surowy_RSI"] < 40: punkty_lokalne += 15
            elif d["Surowy_RSI"] > 70: punkty_lokalne -= 15
            
            if "Złoty Krzyż" in d["Stan_Trendu"]: punkty_lokalne += 20
            elif "Krzyż Śmierci" in d["Stan_Trendu"]: punkty_lokalne -= 20
            
            punkty_lokalne = max(0, min(100, punkty_lokalne))
            score_total += (punkty_lokalne * (waga / max_waga))

    confidence = int(score_total)

    # --- NOWOŚĆ: DYNAMICZNE KOTWICZENIE ---
    # Bonusy są teraz przyznawane na podstawie GŁÓWNEGO interwału z Twojego profilu!
    dg = dane_spolki[glowny_interwal]
    
    if "Wyprzedany" in dg["Radar_RSI"]:
        powody.append(f"🟢 Szansa z RSI ({glowny_interwal.upper()}): {dg['Radar_RSI']}")
    if "Wzrostowy" in dg["MACD_Trend"]:
        powody.append(f"📈 Trend MACD ({glowny_interwal.upper()}) idzie w górę")

    # --- NOWOŚĆ: VETO I KARY ---
    # 1. SCALPING VETO: Nie kupujemy na spadającym mikro-trendzie!
    if glowny_interwal == "1h":
        if "Spadkowy" in dg["MACD_Trend"]:
            confidence = max(0, confidence - 25)
            powody.append("⚠️ SCALPING VETO: Trend MACD 1H jest spadkowy!")
        # Jeśli 4H też krwawi, uciekamy.
        if "Bearish" in dane_spolki.get("4h", {}).get("MACD_Crossover", ""):
            confidence = max(0, confidence - 20)
            powody.append("⚠️ SCALPING VETO: 4H ma sygnał spadkowy!")

    # 2. INVEST/SWING VETO: Szacunek dla trendu wyższego rzędu
    dwk = dane_spolki.get("1wk", {})
    if "Krzyż Śmierci" in dwk.get("Stan_Trendu", "") and glowny_interwal != "1h":
        confidence = max(0, confidence - 30)
        powody.append("⚠️ OSTRZEŻENIE: Główny trend (1wk) jest spadkowy!")

    # DECYZJA OSTATECZNA
    if confidence >= 80: decyzja = f"🔥 ALL-IN KUPUJ (Conf: {confidence}/100)"
    elif confidence >= 65: decyzja = f"🟢 KUPUJ (Conf: {confidence}/100)"
    elif confidence >= 55: decyzja = f"🟡 SPEKULACJA (Conf: {confidence}/100)"
    elif confidence <= 25: decyzja = f"🚨 UCIEKAJ (Conf: {confidence}/100)"
    elif confidence <= 40: decyzja = f"🔴 SPRZEDAJ (Conf: {confidence}/100)"
    else: decyzja = f"⚪ CZEKAJ (Conf: {confidence}/100)"

    return confidence, decyzja, powody

# ==========================================
# GŁÓWNA PĘTLA I GENEROWANIE EXCELA
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--profil', type=str, default="swing", choices=["scalping", "swing", "invest"], help="Profil ważenia interwałów")
    args = parser.parse_args()

    # USTALENIE GŁÓWNEGO INTERWAŁU W ZALEŻNOŚCI OD PROFILU
    glowny_interwal_dla_profilu = {"scalping": "1h", "swing": "1d", "invest": "1wk"}[args.profil]

    moje_grupy = zaladuj_portfel()
    wagi = WAGI_PROFILI[args.profil]
    print(f"🚀 Uruchamiam QUANT bota | Profil: {args.profil.upper()} | Baza analizy: {glowny_interwal_dla_profilu.upper()}")

    wyniki_wszystkie = {} 
    for nazwa_grupy, lista_spolek in moje_grupy.items():
        for spolka in lista_spolek:
            wyniki_wszystkie[spolka] = {"Grupa": nazwa_grupy, "Dane": {}}
            for interwal, zakres in KONFIG_INTERWALOW.items():
                wynik = pobierz_dane_wskaznikow(spolka, interwal, zakres)
                if wynik: wyniki_wszystkie[spolka]["Dane"][interwal] = wynik
                time.sleep(random.uniform(0.6, 1.2)) 

    # 1. Tworzenie Głównej Zakładki Podsumowania
    lista_podsumowania = []
    wiadomosc_telegram = f"<b>🤖 QUANT RADAR PRO | Profil: {args.profil.upper()}</b>\n"
    wiadomosc_telegram += f"<i>Kotwica analizy i TP/SL wyliczone z wykresu {glowny_interwal_dla_profilu.upper()}</i>\n\n"
    
    for spolka, info in wyniki_wszystkie.items():
        conf, decyzja, powody = oblicz_confidence_i_decyzje(info["Dane"], wagi, glowny_interwal_dla_profilu)
        
        # POBIERANIE DANYCH GŁÓWNYCH ZALEŻNIE OD PROFILU
        # Zabezpieczenie: jeśli z jakiegoś powodu nie ma głównego interwału, bierzemy 1d
        dg = info["Dane"].get(glowny_interwal_dla_profilu, info["Dane"].get('1d', {}))
        
        if not dg: continue # Pomijamy spółki z krytycznym brakiem danych
        
        kolumna_interw = glowny_interwal_dla_profilu.upper()
        lista_podsumowania.append({
            "Grupa": info["Grupa"],
            "Symbol": spolka,
            "Cena": dg.get("Cena", "Brak"),
            "REKOMENDACJA": decyzja,
            "Confidence Score": conf,
            f"Stop_Loss ({kolumna_interw})": dg.get("Stop_Loss", "-"),
            f"TP 1 ({kolumna_interw})": dg.get("Take_Profit_1", "-"),
            f"TP 2 ({kolumna_interw})": dg.get("Take_Profit_2", "-"),
            f"Trend ({kolumna_interw})": dg.get("Stan_Trendu", "-"),
            f"MACD Trend ({kolumna_interw})": dg.get("MACD_Trend", "-"),
            f"RSI Radar ({kolumna_interw})": dg.get("Radar_RSI", "-"),
            f"Ryzyko ({kolumna_interw})": dg.get("Radar_Ryzyka", "-")
        })

        if conf >= 65 or conf <= 35: 
            wiadomosc_telegram += f"[{spolka}] <b>{dg.get('Cena')}</b>\n👉 {decyzja}\n"
            for p in powody: wiadomosc_telegram += f"  {p}\n"
            if conf >= 65:
                wiadomosc_telegram += f"🛡️ SL: {dg.get('Stop_Loss')} | TP1: {dg.get('Take_Profit_1')} | {dg.get('Radar_Ryzyka')}\n"
            wiadomosc_telegram += "\n"

    df_podsumowanie = pd.DataFrame(lista_podsumowania).sort_values(by="Confidence Score", ascending=False)

    # 2. Tworzenie Zakładek Szczegółowych i Zapis z Auto-szerokością
    data_raportu = datetime.now().strftime('%Y-%m-%d_%H-%M')
    nazwa_pliku = f"Raport_{args.profil}_{data_raportu}.xlsx"
    
    with pd.ExcelWriter(nazwa_pliku, engine='openpyxl') as writer:
        df_podsumowanie.to_excel(writer, sheet_name="🌟 PODSUMOWANIE", index=False)
        
        for interwal in KONFIG_INTERWALOW.keys():
            dane_zakladki = []
            for spolka, info in wyniki_wszystkie.items():
                if interwal in info["Dane"]:
                    wiersz = {"Grupa": info["Grupa"], "Symbol": spolka}
                    wiersz.update(info["Dane"][interwal])
                    dane_zakladki.append(wiersz)
            if dane_zakladki:
                pd.DataFrame(dane_zakladki).to_excel(writer, sheet_name=f"Szczegóły_{interwal}", index=False)
        
        for nazwa_arkusza in writer.sheets:
            arkusz = writer.sheets[nazwa_arkusza]
            for col in arkusz.columns:
                max_length = 0
                kolumna_literowa = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                dopasowana_szerokosc = min((max_length + 3), 50)
                arkusz.column_dimensions[kolumna_literowa].width = dopasowana_szerokosc

    wyslij_telegram(wiadomosc_telegram, nazwa_pliku)
