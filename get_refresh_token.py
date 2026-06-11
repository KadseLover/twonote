#!/usr/bin/env python3
"""
Einmaliger Script um den Google Drive OAuth2 Refresh Token zu bekommen.
Verwendung: python3 get_refresh_token.py
"""

import json
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

REDIRECT_URI = "http://localhost:8888"
SCOPE = "https://www.googleapis.com/auth/drive"


def main():
    print("=== TwoNote – Google Drive OAuth2 Setup ===\n")

    if len(sys.argv) == 3:
        client_id = sys.argv[1]
        client_secret = sys.argv[2]
    else:
        client_id = input("Google Client ID: ").strip()
        client_secret = input("Google Client Secret: ").strip()

    auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        f"?response_type=code"
        f"&client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={urllib.parse.quote(SCOPE)}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    print("Browser öffnet sich zur Autorisierung...")
    print(f"Falls er sich nicht öffnet, öffne manuell:\n{auth_url}\n")
    webbrowser.open(auth_url)

    auth_code = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            qs = parse_qs(urlparse(self.path).query)
            auth_code = qs.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<h2>Autorisierung erfolgreich!</h2>"
                b"<p>Du kannst dieses Fenster schlie&szlig;en.</p>"
            )

        def log_message(self, *args):
            pass

    print("Warte auf Autorisierung (Port 8888)...")
    server = HTTPServer(("localhost", 8888), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("Fehler: Kein Auth-Code erhalten.")
        sys.exit(1)

    data = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Token-Austausch fehlgeschlagen: {e.read().decode()}")
        sys.exit(1)

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("Kein Refresh Token erhalten.")
        print("Stelle sicher dass du im Google-Account unter")
        print("myaccount.google.com/permissions den App-Zugriff widerrufst")
        print("und den Script erneut ausführst.")
        sys.exit(1)

    print("\n" + "=" * 55)
    print("Folgendes in die .env eintragen:")
    print("=" * 55)
    print(f"GOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    print("=" * 55)


if __name__ == "__main__":
    main()
