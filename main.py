import os
import requests
import json
import time
import math
from groq import Groq

# --- KONFIGURACIJA ---
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
VALUE_THRESHOLD = 0.15  # Signal se generiše ako je naša prednost > 15%
SPORT_KEY = 'soccer_epl' 
MARKETS = 'h2h'
REGIONS = 'eu'
BASE_POWER_SCORE = 100

# --- INICIJALIZACIJA KLIJENATA ---
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- MODUL 1: SAKUPLJAČ PODATAKA ---
def get_live_odds():
    if not ODDS_API_KEY:
        print("GREŠKA: ODDS_API_KEY nije postavljen.")
        return []
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds/?apiKey={ODDS_API_KEY}®ions={REGIONS}&markets={MARKETS}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"GREŠKA pri povlačenju kvota: {e}")
        return []

def get_latest_news_simulation():
    print("\n📰 Sakupljam najnovije vesti (simulacija)...")
    return [
        "Potvrđeno: Kapiten Man. Utd-a, Bruno Fernandes, propušta derbi zbog suspenzije.",
        "Trener Liverpoola, Klopp, izjavio je: 'Atmosfera nikad bolja, spremni smo 110%'.",
        "Procurila je informacija o žestokoj svađi između dva starija igrača Liverpoola u svlačionici."
    ]

# --- MODUL 2: LLM ANALITIČAR ---
def analyze_news_with_llm(news_text: str):
    if not groq_client:
        print("UPOZORENJE: GROQ_API_KEY nije podešen. Preskačem LLM analizu.")
        return None
    system_prompt = "Ti si sportski analitičar. Pročitaj vest i prevedi je u JSON sa poljima: 'is_relevant' (boolean), 'team' (string), 'summary' (string), 'impact_score' (integer od -25 do +25)."
    print(f"🤖 Šaljem LLM-u na analizu: '{news_text[:60]}...'")
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": news_text}]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"GREŠKA pri komunikaciji sa Groq API-jem: {e}")
        return None

# --- MODUL 3: GLAVNI GXAI MOTOR I ALPHA GENERATOR ---
def run_full_analysis():
    print_header("1. Inicijalizacija i Sakupljanje Podataka")
    live_matches = get_live_odds()
    if not live_matches:
        print("Nema mečeva za analizu. Izlazim.")
        return

    all_teams = {team for match in live_matches for team in [match['home_team'], match['away_team']]}
    power_scores = {team: BASE_POWER_SCORE for team in all_teams}
    print(f"Pratim {len(all_teams)} timova u ligi.")
    
    print_header("2. Analiza Vesti i Ažuriranje Power Score-ova")
    news_items = get_latest_news_simulation()
    for item in news_items:
        analysis = analyze_news_with_llm(item)
        if analysis and analysis.get('is_relevant'):
            team = analysis.get('team')
            impact = analysis.get('impact_score', 0)
            if team in power_scores:
                print(f"   -> Relevantna vest za {team}. Impact: {impact}. Sažetak: {analysis.get('summary')}")
                power_scores[team] += impact
        time.sleep(1)

    print("\n🏁 Finalni Power Score-ovi:")
    print(json.dumps(power_scores, indent=2))

    print_header("3. Alpha Generator - Traženje 'Value Bet' Anomalija")
    found_any_value_bet = False
    for match in live_matches:
        home_team = match['home_team']
        away_team = match['away_team']
        
        home_score = power_scores.get(home_team, BASE_POWER_SCORE)
        away_score = power_scores.get(away_team, BASE_POWER_SCORE)
        
        # Softmax za verovatnoće (samo sa dva ishoda za jednostavnost)
        total_score = home_score + away_score
        prob_home = home_score / total_score
        prob_away = away_score / total_score
        
        # Uzmi kvote
        try:
            bookmaker = match['bookmakers'][0]
            prices = bookmaker['markets'][0]['outcomes']
            odds_home = next((p['price'] for p in prices if p['name'] == home_team), None)
            odds_away = next((p['price'] for p in prices if p['name'] == away_team), None)
        except (IndexError, KeyError):
            continue # Preskoči meč ako nema kvota

        if not odds_home or not odds_away: continue

        # Provera "Value"
        value_home = (prob_home * odds_home) - 1
        value_away = (prob_away * odds_away) - 1

        print(f"\nAnaliziram meč: {home_team} vs {away_team}")
        print(f"  Naša P(1): {prob_home:.1%}, Kvota P(1): {1/odds_home:.1%} | Value: {value_home:.2f}")
        print(f"  Naša P(2): {prob_away:.1%}, Kvota P(2): {1/odds_away:.1%} | Value: {value_away:.2f}")

        if value_home > VALUE_THRESHOLD:
            found_any_value_bet = True
            print(f"  ✅ VALUE BET ALERT! Preporuka: Ulog na {home_team} (Kvota: {odds_home})")
        
        if value_away > VALUE_THRESHOLD:
            found_any_value_bet = True
            print(f"  ✅ VALUE BET ALERT! Preporuka: Ulog na {away_team} (Kvota: {odds_away})")

    if not found_any_value_bet:
        print("\nNema detektovanih 'Value Bet' anomalija u ovom ciklusu.")

def print_header(title):
    print("\n" + "═"*60)
    print(f"  {title.upper()}")
    print("═"*60)

# --- POKRETANJE ---
if __name__ == "__main__":
    run_full_analysis()
    print_header("Analiza završena")
