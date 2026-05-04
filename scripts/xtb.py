import json
import ssl
import os
from websocket import create_connection
from dotenv import load_dotenv

# Wczytujemy dane z pliku .env
load_dotenv()

class XTBClient:
    def __init__(self):
        self.user_id = os.getenv("XTB_USER_ID")
        self.password = os.getenv("XTB_PASSWORD")
        self.mode = os.getenv("XTB_MODE", "demo")
        
        # Oficjalne punkty wejścia xAPI (2026)
        if self.mode == 'real':
            self.url = "wss://ws.xtb.com:5112" # Spróbuj też: "wss://ws.xtb.com:5112"
        else:
            self.url = "wss://ws.xtb.com:5124" # Spróbuj też: "wss://ws.xtb.com:5124"

    def login(self):
        if not self.user_id or not self.password:
            return {"status": False, "errorCode": "Brak danych w pliku .env"}
            
        try:
            # XTB wymaga czasem konkretnego nagłówka lub portu
            self.ws = create_connection(self.url, timeout=10, sslopt={"cert_reqs": ssl.CERT_NONE})
            
            login_data = {
                "command": "login",
                "arguments": {
                    "userId": self.user_id,
                    "password": self.password,
                    "appName": "python_bot"
                }
            }
            return self._send_command(login_data)
        except Exception as e:
            return {"status": False, "errorCode": str(e)}

    def _send_command(self, dict_data):
        self.ws.send(json.dumps(dict_data))
        return json.loads(self.ws.recv())

# --- URUCHOMIENIE ---
client = XTBClient()
print(f"Próba bezpiecznego logowania (tryb: {client.mode})...")
response = client.login()

if response.get('status'):
    print("✅ Sukces! Jesteś połączony bezpiecznie.")
else:
    # Jeśli nadal masz 404, spróbuj zamienić url na: "wss://ws.xtb.com:443/demo"
    print(f"❌ Błąd: {response.get('errorCode')}")