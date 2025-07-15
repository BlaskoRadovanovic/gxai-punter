# ==============================================================================
#                 GXAI "Hermes" v1.0 - Autonomni Agent
# ==============================================================================
import os
import requests
import json
import time
import math
import numpy as np
from scipy.optimize import minimize
from groq import Groq

# --- 1. KONFIGURACIJA I INICIJALIZACIJA ---
def setup_clients_and_config():
    """Učitava konfiguraciju iz okruženja."""
    return {
        "odds_api_key": os.environ.get('ODDS_API_KEY'),
        "groq_api_key": os.environ.get('GROQ_API_KEY'),
        "value_threshold": 0.10, # Smanjujemo prag da dobijemo više kandidata
        "sport_key": 'soccer_epl',
        "markets": 'h2h',
        "regions": 'eu',
        "base_power_score": 100,
        "bankroll": 1000, # Fiktivni bankroll od 1000€
        "max_kelly_fraction": 0.1 # Maksimalno ulažemo 10% bankrolla odjednom
    }

def print_header(title):
    print("\n" + "═"*60)
    print(f"  {title.upper()}")
    print("═"*60)

# --- 2. MODUL ZA PRIKUPLJANJE PODATAKA ---
def get_live_odds(config):
    if not config["odds_api_key"]: 
        print("GREŠKA: ODDS_API_KEY nije podešen.")
        return []
    url = f"https://api.the-odds-api.com/v4/sports/{config['sport_key']}/odds/"
    params = {"apiKey": config["odds_api_key"], "regions": config["regions"], "markets": config["markets"]}
    print("INFO: Povlačim podatke o kvotama...")
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        print("INFO: Uspešno povučeni podaci o kvotama.")
        return response.json()
    except Exception as e:
        print(f"GREŠKA pri povlačenju kvota: {e}")
        return []

def get_latest_news_simulation():
    print("\n📰 Sakupljam najnovije vesti (simulacija)...")
    return [
        {"text": "Potvrđeno: Kapiten Man. Utd-a, Bruno Fernandes, propušta derbi.", "team": "Manchester United", "impact": -15},
        {"text": "Neverovatna atmosfera ispred hotela Liverpoola, navijači pevaju.", "team": "Liverpool", "impact": 10},
        {"text": "Trener Arsenala, Arteta, odmara ključne igrače pred evropsku utakmicu.", "team": "Arsenal", "impact": -8}
    ]

# --- 3. MODUL ZA AI ANALIZU ---
def analyze_news_with_llm(news_item, groq_client):
    """Simulira povratnu vrednost od LLM-a radi brzine i konzistentnosti testa."""
    print(f"🤖 Analiziram: '{news_item['text'][:30]}...' -> Impact: {news_item['impact']}")
    # U pravoj verziji, ovde bi bio poziv Groq API-ju
    return news_item

# --- 4. GLAVNI GXAI MOTOR ---
def calculate_power_scores(config, all_teams, news_items, groq_client):
    power_scores = {team: config["base_power_score"] for team in all_teams}
    for item in news_items:
        analysis = analyze_news_with_llm(item, groq_client) # Prosleđujemo klijenta
        if analysis:
            team = analysis.get('team')
            impact = analysis.get('impact', 0)
            if team in power_scores:
                power_scores[team] += impact
    return power_scores

# --- 5. "HERMES" PORTFOLIO MODUL ---
def find_value_opportunities(config, live_matches, power_scores):
    """Pronalazi sve opklade koje imaju pozitivan 'Value'."""
    opportunities = []
    for match in live_matches:
        try:
            home_team, away_team = match['home_team'], match['away_team']
            home_score = power_scores.get(home_team, config["base_power_score"])
            away_score = power_scores.get(away_team, config["base_power_score"])
            draw_score = (home_score + away_score) / 2
            
            exp_h, exp_d, exp_a = math.exp(home_score/100), math.exp(draw_score/100), math.exp(away_score/100)
            total_exp = exp_h + exp_d + exp_a
            probs = {'1': exp_h/total_exp, 'X': exp_d/total_exp, '2': exp_a/total_exp}
            
            bookmaker = match['bookmakers'][0]
            prices = {p['name']: p['price'] for p in bookmaker['markets'][0]['outcomes']}
            odds = {'1': prices.get(home_team), 'X': prices.get('Draw'), '2': prices.get(away_team)}

            for outcome, outcome_name in [('1', home_team), ('X', 'Draw'), ('2', away_team)]:
                if odds[outcome]:
                    value = (probs[outcome] * odds[outcome]) - 1
                    if value > config["value_threshold"]:
                        opportunities.append({
                            "match": f"{home_team} vs {away_team}",
                            "outcome_key": outcome,
                            "outcome_name": outcome_name,
                            "our_prob": probs[outcome],
                            "market_prob": 1 / odds[outcome],
                            "odds": odds[outcome],
                            "value": value
                        })
        except (IndexError, KeyError, TypeError):
            continue
    return opportunities

def optimize_portfolio(opportunities):
    """Markowitz-ova Optimizacija Portfolija."""
    if not opportunities: return None, None
    num_assets = len(opportunities)
    returns = np.array([opp['value'] for opp in opportunities])
    # Uprošćena pretpostavka: kovarijansa je nula između različitih mečeva
    cov_matrix = np.diag([p * (1 - p) for p in [opp['our_prob'] for opp in opportunities]])
    def objective(weights):
        return - (np.sum(returns * weights) / np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0, 1) for _ in range(num_assets))
    initial_weights = num_assets * [1. / num_assets,]
    result = minimize(objective, initial_weights, method='SLSQP', bounds=bounds, constraints=constraints)
    if result.success: return result.x, opportunities
    return None, None

def allocate_capital(config, optimal_weights, opportunities):
    """Koristi Kelly Kriterijum da odredi ukupan ulog."""
    if optimal_weights is None or not any(w > 0.001 for w in optimal_weights): return None
    portfolio_value = sum(opp['value'] * w for opp, w in zip(opportunities, optimal_weights))
    if portfolio_value <= 0: return None
    # Računanje prosečne kvote portfolija je kompleksno, koristimo aproksimaciju
    portfolio_odds_approx = 1 / sum((1/opp['odds']) * w for opp, w in zip(opportunities, optimal_weights) if w > 0.001)
    if portfolio_odds_approx <= 1: return None
    kelly_fraction = portfolio_value / (portfolio_odds_approx - 1)
    final_fraction = min(kelly_fraction, config["max_kelly_fraction"])
    return {
        "total_stake_fraction": final_fraction,
        "total_stake_amount": config["bankroll"] * final_fraction,
        "individual_stakes": {opps['match'] + " - " + opps['outcome_name']: w * (config["bankroll"] * final_fraction) for w, opps in zip(optimal_weights, opportunities)}
    }

# --- 6. GLAVNI POKRETAČ ---
def run_hermes_analysis():
    config, groq_client = setup_clients_and_config()
    print_header("1. Prikupljanje i Analiza Podataka")
    live_matches = get_live_odds(config)
    if not live_matches: return
    
    all_teams = {team for match in live_matches for team in [match['home_team'], match['away_team']]}
    news_items = get_latest_news_simulation()
    power_scores = calculate_power_scores(config, all_teams, news_items, groq_client)
    print("\n🏁 Finalni Power Score-ovi:", {k:v for k,v in power_scores.items() if v != 100})

    print_header("2. Pronalaženje 'Value' Prilika")
    opportunities = find_value_opportunities(config, live_matches, power_scores)
    if not opportunities:
        print("Nema pronađenih 'Value Bet' prilika.")
        return
    for opp in opportunities:
        print(f"  - Pronađena prilika: {opp['match']} -> ishod '{opp['outcome_name']}' (Value: {opp['value']:.2f})")

    print_header("3. Optimizacija Portfolija (Markowitz)")
    optimal_weights, opps = optimize_portfolio(opportunities)
    if optimal_weights is None:
        print("Optimizacija nije uspela.")
        return
    print("Optimalna raspodela uloga (težine):")
    for w, opp in zip(optimal_weights, opps):
        if w > 0.01:
            print(f"  - {w*100:5.1f}% na: {opp['match']} - Ishod '{opp['outcome_name']}'")

    print_header("4. Alokacija Kapitala (Kelly) i Finalna Preporuka")
    stake_recommendation = allocate_capital(config, optimal_weights, opps)
    if stake_recommendation:
        print(f"PREPORUKA: Uložiti ukupno {stake_recommendation['total_stake_amount']:.2f} € ({stake_recommendation['total_stake_fraction']:.1%}) vašeg bankrolla od {config['bankroll']}€.")
        print("Raspodela uloga:")
        for bet_name, amount in stake_recommendation['individual_stakes'].items():
            if amount > 0.1: # Prikazujemo samo uloge veće od 10 centi
                print(f"  - {amount:.2f} € na: {bet_name}")
    else:
        print("Nema preporuke za ulaganje nakon optimizacije.")

if __name__ == "__main__":
    try:
        run_hermes_analysis()
    except Exception as e:
        print(f"\nFATALNA GREŠKA: Došlo je do prekida izvršavanja skripte. Greška: {e}")
    finally:
        print_header("Analiza završena")
