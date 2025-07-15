import os
import requests
import json
import time

# --- KONFIGURACIJA ---
# API ključevi se učitavaju iz GitHub Secrets
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Hiperparametri sistema
VALUE_THRESHOLD = 0.15
SPORT_KEY = 'soccer_epl'
MARKETS = 'h2h'
REGIONS = 'eu'
BASE_POWER_SCORE = 100

# --- INICIJALIZACIJA KLIJENATA ---
# U pravoj aplikaciji, Groq klijent bi bio inicijalizovan ovde
# groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- MODUL 1: SAKUPLJAČ PODATAKA ---

def get_live_odds():
    """Povlači najnovije kvote sa The Odds API."""
    if not ODDS_API_KEY:
        print("GRESKA: ODDS_API_KEY nije postavljen u GitHub Secrets.")
        return []
    
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds/?apiKey={ODDS_API_KEY}ions={REGIONS}&markets={MARKETS}"
    print(f"INFO: Povlacim podatke sa The Odds API...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        print("INFO: Uspesno povuceni podaci sa The Odds API.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"GRESKA pri komunikaciji sa API-jem: {e}")
        return []

def get_latest_news_simulation():
    """Simulacija sakupljanja vesti."""
    print("INFO: Sakupljam najnovije vesti (simulacija)...")
    return [] # Za sada ostavljamo prazno da testiramo samo kvote

# --- OSTATAK KODA (za sada nije bitan za test) ---
# ... Ostatak funkcija (analyze_news_with_llm, run_full_analysis) bi išao ovde ...

# --- POKRETANJE ---
if __name__ == "__main__":
    print("Pokrecem GXAI Punter v0.1.1 - Test Konektivnosti")
    
    live_matches = get_live_odds()
    
    if live_matches:
        print(f"\nUSPEH! Pronadjeno {len(live_matches)} meceva.")
        # Ispisujemo prvi meč kao dokaz
        first_match = live_matches[0]
        home = first_match['home_team']
        away = first_match['away_team']
        print(f"Primer meca: {home} vs {away}")
    else:
        print("\nNEUSPEH. Nema preuzetih meceva. Proverite greske iznad.")
        
    print("\nSkripta zavrsena.")
