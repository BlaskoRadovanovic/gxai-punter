import os
import requests
import json
import time
from groq import Groq

# --- KONFIGURACIJA ---
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# --- INICIJALIZACIJA KLIJENATA ---
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- MODUL 2: LLM ANALITIČAR ---
def analyze_news_with_llm(news_text: str):
    """Šalje vest LLM-u na analizu i vraća strukturirani JSON."""
    if not groq_client:
        print("UPOZORENJE: GROQ_API_KEY nije postavljen. Preskačem LLM analizu.")
        return None

    system_prompt = """
    Ti si vrhunski sportski analitičar. Tvoj zadatak je da pročitaš vest i prevedeš je u JSON.
    Fokusiraj se samo na informacije koje utiču na snagu tima za nadolazeći meč.
    JSON struktura mora imati sledeća polja:
    - "is_relevant": boolean (true ako je vest bitna za snagu tima, inače false).
    - "team": String (ime tima na koji se odnosi, ili "None").
    - "summary": String (tvoja kratka analiza od jedne rečenice).
    - "impact_score": Integer (ceo broj od -25 (veoma loše) do +25 (veoma dobro)).
    """
    
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
        analysis_json = json.loads(response.choices[0].message.content)
        return analysis_json
    except Exception as e:
        print(f"GREŠKA pri komunikaciji sa Groq API-jem: {e}")
        return None

# --- MODUL 1: SAKUPLJAČ VESTI (SIMULACIJA) ---
def get_latest_news_simulation():
    """U pravoj aplikaciji, ova funkcija bi koristila RSS. Ovde je simuliramo."""
    print("\n📰 Sakupljam najnovije vesti (simulacija)...")
    return [
        "Trener Man. Utd-a, Ten Hag, potvrdio je da je defanzivac Lisandro Martinez potpuno spreman za derbi.",
        "Procurila je informacija o žestokoj svađi između dva igrača Liverpoola u svlačionici nakon poslednjeg poraza.",
        "Marketing odeljenje Liverpoola je objavilo novi dizajn dresova za sledeću sezonu." # Primer nebitne vesti
    ]

# --- GLAVNI DEO ---
if __name__ == "__main__":
    print("Pokrećem GXAI Punter v0.2 - Analiza Vesti")

    power_scores = {
        "Manchester United": 100,
        "Liverpool": 105
    }
    print(f"\nPočetni Power Score-ovi: {power_scores}")

    news_items = get_latest_news_simulation()
    for item in news_items:
        analysis = analyze_news_with_llm(item)
        if analysis and analysis.get('is_relevant'):
            team = analysis.get('team')
            impact = analysis.get('impact_score', 0)
            
            if team in power_scores:
                print(f"   -> Relevantna vest za {team}. Impact: {impact}. Sažetak: {analysis.get('summary')}")
                power_scores[team] += impact
            else:
                 print(f"   -> Vest je relevantna, ali tim '{team}' nije u našoj trenutnoj analizi.")
        else:
            print(f"   -> Vest '{item[:60]}...' je ocenjena kao nebitna.")
        time.sleep(1)

    print("\n🏁 Ažurirani Power Score-ovi nakon analize vesti:")
    print(power_scores)
