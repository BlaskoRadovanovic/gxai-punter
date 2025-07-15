import os
import requests
import json
import time
from groq import Groq

# --- KONFIGURACIJA ---
# API ključevi se učitavaju iz GitHub Secrets
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Hiperparametri sistema
VALUE_THRESHOLD = 0.15
# Promenjena imena promenljivih da se izbegne greška
TARGET_SPORT = 'soccer_epl'
TARGET_MARKETS = 'h2h'
TARGET_REGIONS = 'eu' # Eksplicitno napisan string
BASE_POWER_SCORE = 100

# --- INICIJALIZACIJA KLIJENATA ---
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- MODUL 1: SAKUPLJAČ PODATAKA ---
def get_live_odds():
    if not ODDS_API_KEY:
        print("GREŠKA: ODDS_API_KEY nije postavljen.")
        return []
    
    # Pažljivo konstruisan URL sa novim imenima promenljivih
    # Ovo je najvažnija ispravka
    url = f"https://api.the-odds-api.com/v4/sports/{TARGET_SPORT}/odds/"
    api_params = {
        'apiKey': ODDS_API_KEY,
        'regions': TARGET_REGIONS,
        'markets': TARGET_MARKETS
    }
    
    print(f"INFO: Povlačim podatke sa The Odds API...")
    
    try:
        response = requests.get(url, params=api_params)
        response.raise_for_status()
        print("INFO: Uspešno povučeni podaci sa The Odds API.")
        return response.json()
    except Exception as e:
        print(f"GREŠKA pri povlačenju kvota: {e}")
        return []

# Ostatak koda ostaje isti kao u našoj Sesiji 3
# ... (sve funkcije od get_latest_news_simulation do kraja) ...

def get_latest_news_simulation():
    print("\n📰 Sakupljam najnovije vesti (simulacija)...")
    return [
        "Potvrđeno: Kapiten Man. Utd-a, Bruno Fernandes, propušta derbi zbog suspenzije.",
        "Trener Liverpoola, Klopp, izjavio je: 'Atmosfera nikad bolja, spremni smo 110%'.",
        "Procurila je informacija o žestokoj svađi između dva starija igrača Liverpoola u svlačionici."
    ]

def analyze_news_with_llm(news_text: str):
    if not groq_client:
        print("UPOZORENJE: GROQ_API_KEY nije podešen. Preskačem LLM analizu.")
        return None
    system_prompt = "Ti si sportski analitičar. Pročitaj vest i prevedi je u JSON. Fokusiraj se na informacije koje utiču na snagu tima. JSON struktura: 'is_relevant' (boolean), 'team' (string), 'summary' (string), 'impact_score' (integer od -25 do +25)."
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
    print(json.dumps(power_scores, indent=2, sort_keys=True))

    print_header("3. Alpha Generator - Traženje 'Value Bet' Anomalija")
    found_any_value_bet = False
    for match in live_matches:
        home_team = match['home_team']
        away_team = match['away_team']
        
        home_score = power_scores.get(home_team, BASE_POWER_SCORE)
        away_score = power_scores.get(away_team, BASE_POWER_SCORE)
        draw_score = (home_score + away_score) / 2
        
        exp_h = math.exp(home_score / 100)
        exp_d = math.exp(draw_score / 100)
        exp_a = math.exp(away_score / 100)
        total_exp = exp_h + exp_d + exp_a
        
        prob_home = exp_h / total_exp
        prob_draw = exp_d / total_exp
        prob_away = exp_a / total_exp
        
        try:
            bookmaker = match['bookmakers'][0]
            prices = bookmaker['markets'][0]['outcomes']
            odds = {p['name']: p['price'] for p in prices}
            odds_home = odds.get(home_team)
            odds_away = odds.get(away_team)
            odds_draw = odds.get('Draw')
        except (IndexError, KeyError):
            continue

        if not all([odds_home, odds_away, odds_draw]): continue

        value_home = (prob_home * odds_home) - 1
        value_draw = (prob_draw * odds_draw) - 1
        value_away = (prob_away * odds_away) - 1

        print(f"\nAnaliziram meč: {home_team} vs {away_team}")
        print(f"  Naša P(1): {prob_home:.1%}, Kvota P(1): {1/odds_home:.1%} | Value: {value_home:.2f}")
        print(f"  Naša P(X): {prob_draw:.1%}, Kvota P(X): {1/odds_draw:.1%} | Value: {value_draw:.2f}")
        print(f"  Naša P(2): {prob_away:.1%}, Kvota P(2): {1/odds_away:.1%} | Value: {value_away:.2f}")

        if value_home > VALUE_THRESHOLD:
            found_any_value_bet = True
            print(f"  ✅ VALUE BET ALERT! Preporuka: Ulog na {home_team} (Kvota: {odds_home})")
        
        if value_draw > VALUE_THRESHOLD:
            found_any_value_bet = True
            print(f"  ✅ VALUE BET ALERT! Preporuka: Ulog na Nerešeno (Kvota: {odds_draw})")

        if value_away > VALUE_THRESHOLD:
            found_any_value_bet = True
            print(f"  ✅ VALUE BET ALERT! Preporuka: Ulog na {away_team} (Kvota: {odds_away})")

    if not found_any_value_bet:
        print("\nNema detektovanih 'Value Bet' anomalija u ovom ciklusu.")

def print_header(title):
    print("\n" + "═"*60)
    print(f"  {title.upper()}")
    print("═"*60)

if __name__ == "__main__":
    run_full_analysis()
    print_header("Analiza završena")
