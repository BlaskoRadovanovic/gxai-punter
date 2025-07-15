# ==============================================================================
#                 GXAI "Quantum Edge" v1.0 - Finalna Verzija
# ==============================================================================
import os
import requests
import json
import time
import math  # Uvoz MATH biblioteke
from groq import Groq

# --- 1. KONFIGURACIJA I INICIJALIZACIJA ---
def setup_clients_and_config():
    """Učitava konfiguraciju iz okruženja."""
    config = {
        "odds_api_key": os.environ.get('ODDS_API_KEY'),
        "groq_api_key": os.environ.get('GROQ_API_KEY'),
        "value_threshold": 0.15,
        "sport_key": 'soccer_epl',
        "markets": 'h2h',
        "regions": 'eu',
        "base_power_score": 100
    }
    
    # Inicijalizacija Groq klijenta
    groq_client = Groq(api_key=config["groq_api_key"]) if config["groq_api_key"] else None
    
    return config, groq_client

# --- 2. MODUL ZA PRIKUPLJANJE PODATAKA ---
def get_live_odds(config):
    """Povlači najnovije kvote sa The Odds API."""
    if not config["odds_api_key"]:
        print("GREŠKA: ODDS_API_KEY nije postavljen.")
        return []
    
    url = f"https://api.the-odds-api.com/v4/sports/{config['sport_key']}/odds/"
    params = {
        "apiKey": config["odds_api_key"],
        "regions": config["regions"],
        "markets": config["markets"]
    }

    print("INFO: Povlačim podatke o kvotama sa The Odds API...")
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        print("INFO: Uspešno povučeni podaci o kvotama.")
        return response.json()
    except Exception as e:
        print(f"GREŠKA pri povlačenju kvota: {e}")
        return []

def get_latest_news_simulation():
    """Simulira sakupljanje najnovijih vesti."""
    print("\n📰 Sakupljam najnovije vesti (simulacija)...")
    return [
        "Potvrđeno: Kapiten Man. Utd-a, Bruno Fernandes, propušta derbi zbog suspenzije.",
        "Procurila je informacija o žestokoj svađi između dva starija igrača Liverpoola u svlačionici.",
        "Marketing odeljenje Arsenala je objavilo sponzorski ugovor." # Nebitna vest
    ]

# --- 3. MODUL ZA AI ANALIZU ---
def analyze_news_with_llm(news_text, groq_client):
    """Šalje vest LLM-u na analizu."""
    if not groq_client:
        print("UPOZORENJE: GROQ_API_KEY nije podešen. Preskačem LLM analizu.")
        return None
        
    system_prompt = "Ti si sportski analitičar. Pročitaj vest i prevedi je u JSON. Fokusiraj se samo na informacije koje utiču na snagu tima. JSON struktura mora imati polja: 'is_relevant' (boolean), 'team' (string, tačno ime tima), 'summary' (string, kratka analiza), 'impact_score' (integer od -25 do +25)."
    
    print(f"🤖 Šaljem LLM-u na analizu: '{news_text[:60]}...'")
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": news_text}
            ]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"GREŠKA pri komunikaciji sa Groq API-jem: {e}")
        return None

# --- 4. GLAVNI GXAI MOTOR ---
def run_full_analysis():
    """Glavna funkcija koja orkestrira ceo proces."""
    config, groq_client = setup_clients_and_config()
    
    print_header("1. INICIJALIZACIJA I SAKUPLJANJE PODATAKA")
    live_matches = get_live_odds(config)
    if not live_matches:
        print("Nema mečeva za analizu. Izlazim.")
        return

    all_teams = {team for match in live_matches for team in [match['home_team'], match['away_team']]}
    power_scores = {team: config["base_power_score"] for team in all_teams}
    print(f"Pratim {len(all_teams)} timova u ligi.")
    
    print_header("2. ANALIZA VESTI I AŽURIRANJE POWER SCORE-OVA")
    news_items = get_latest_news_simulation()
    for item in news_items:
        analysis = analyze_news_with_llm(item, groq_client)
        if analysis and analysis.get('is_relevant'):
            team = analysis.get('team')
            impact = analysis.get('impact_score', 0)
            if team in power_scores:
                print(f"   -> Relevantna vest za '{team}'. Impact: {impact}. Sažetak: {analysis.get('summary')}")
                power_scores[team] += impact
        time.sleep(1)

    print("\n🏁 Finalni Power Score-ovi:")
    print(json.dumps(power_scores, indent=2, sort_keys=True))

    print_header("3. ALPHA GENERATOR - TRAŽENJE 'VALUE BET' ANOMALIJA")
    found_any_value_bet = False
    for match in live_matches:
        try:
            home_team = match['home_team']
            away_team = match['away_team']
            
            home_score = power_scores.get(home_team, config["base_power_score"])
            away_score = power_scores.get(away_team, config["base_power_score"])
            draw_score = (home_score + away_score) / 2
            
            exp_h = math.exp(home_score / 100)
            exp_d = math.exp(draw_score / 100)
            exp_a = math.exp(away_score / 100)
            total_exp = exp_h + exp_d + exp_a
            
            prob_home = exp_h / total_exp
            prob_draw = exp_d / total_exp
            prob_away = exp_a / total_exp
            
            bookmaker = match['bookmakers'][0]
            prices = bookmaker['markets'][0]['outcomes']
            odds = {p['name']: p['price'] for p in prices}
            odds_home = odds.get(home_team)
            odds_away = odds.get(away_team)
            odds_draw = odds.get('Draw')

            if not all([odds_home, odds_away, odds_draw]): continue

            value_home = (prob_home * odds_home) - 1
            value_draw = (prob_draw * odds_draw) - 1
            value_away = (prob_away * odds_away) - 1

            print(f"\nAnaliziram meč: {home_team} vs {away_team}")
            print(f"  Naša P(1): {prob_home:.1%}, Kvota P(1): {1/odds_home:.1%} | Value: {value_home:.2f}")
            print(f"  Naša P(X): {prob_draw:.1%}, Kvota P(X): {1/odds_draw:.1%} | Value: {value_draw:.2f}")
            print(f"  Naša P(2): {prob_away:.1%}, Kvota P(2): {1/odds_away:.1%} | Value: {value_away:.2f}")

            if value_home > config["value_threshold"]:
                found_any_value_bet = True
                print(f"  ✅ VALUE BET ALERT! Preporuka: Ulog na {home_team} (Kvota: {odds_home})")
            if value_draw > config["value_threshold"]:
                found_any_value_bet = True
                print(f"  ✅ VALUE BET ALERT! Preporuka: Ulog na Nerešeno (Kvota: {odds_draw})")
            if value_away > config["value_threshold"]:
                found_any_value_bet = True
                print(f"  ✅ VALUE BET ALERT! Preporuka: Ulog na {away_team} (Kvota: {odds_away})")

        except (IndexError, KeyError, TypeError) as e:
            print(f"INFO: Preskačem meč zbog nekompletnih podataka o kvotama. Greška: {e}")

    if not found_any_value_bet:
        print("\nNema detektovanih 'Value Bet' anomalija u ovom ciklusu.")

def print_header(title):
    print("\n" + "═"*60)
    print(f"  {title.upper()}")
    print("═"*60)

# --- GLAVNI POKRETAČ ---
if __name__ == "__main__":
    try:
        run_full_analysis()
    except Exception as e:
        print(f"\nFATALNA GREŠKA: Došlo je do prekida izvršavanja skripte. Greška: {e}")
    finally:
        print_header("Analiza završena")
