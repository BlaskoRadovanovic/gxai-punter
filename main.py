import os
import requests
import json

def get_live_odds():
    # Uzimamo API ključ iz GitHub Secrets (objasniću ovo u sledećem koraku)
    api_key = os.environ.get('ODDS_API_KEY')
    if not api_key:
        print("Greška: ODDS_API_KEY nije postavljen!")
        return

    # Pratimo Englesku Premier Ligu kao primer
    sport_key = 'soccer_epl'
    markets = 'h2h' # 1X2 kvote
    regions = 'eu'

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}®ions={regions}&markets={markets}"

    print(f"Povlačim podatke sa: {url.replace(api_key, '***')}")

    try:
        response = requests.get(url)
        response.raise_for_status() # Proverava da li je zahtev bio uspešan (status 200)
        
        matches = response.json()
        print(f"Pronađeno {len(matches)} mečeva.")

        # Ispisujemo osnovne informacije o svakom meču
        for match in matches:
            home_team = match['home_team']
            away_team = match['away_team']
            
            # Uzimamo kvote od prvog dostupnog kladioničara
            bookmaker = match['bookmakers'][0]
            prices = bookmaker['markets'][0]['outcomes']
            
            odds_home = next((p['price'] for p in prices if p['name'] == home_team), 'N/A')
            odds_away = next((p['price'] for p in prices if p['name'] == away_team), 'N/A')
            odds_draw = next((p['price'] for p in prices if p['name'] == 'Draw'), 'N/A')

            print(f"\n  - Meč: {home_team} vs {away_team}")
            print(f"    Kvote: 1: {odds_home}, X: {odds_draw}, 2: {odds_away}")

    except requests.exceptions.RequestException as e:
        print(f"Greška pri komunikaciji sa API-jem: {e}")
    except json.JSONDecodeError:
        print("Greška: Nije primljen validan JSON odgovor od API-ja.")

if __name__ == "__main__":
    print("Pokrećem GXAI Punter v0.1 - Sakupljač Kvota")
    get_live_odds()
    print("\nSkripta završena.")
