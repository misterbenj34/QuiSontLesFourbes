import requests
import json
import os
from datetime import datetime
from collections import defaultdict

BASE_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records"
DATA_FILE = "gas_prices.json"
MAPPING_URL = "https://raw.githubusercontent.com/Aohzan/hass-prixcarburant/master/custom_components/prix_carburant/stations_name.json"

EXCLUDED_STATIONS = {"75016026", "75001003", "94290003", "77860002", "75017019"}

def collect():
    stats = defaultdict(lambda: {"gazole": [], "sp95": []})
    
    # Récupération du mapping communautaire
    print("Récupération du dictionnaire des marques...")
    try:
        mapping_req = requests.get(MAPPING_URL)
        stations_mapping = mapping_req.json()
    except Exception as e:
        print(f"Erreur lors de la récupération du mapping: {e}")
        stations_mapping = {}
        
    offset = 0
    limit = 100
    
    while True:
        params = {
            "where": 'code_region="11"',
            "limit": limit,
            "offset": offset
        }
        response = requests.get(BASE_URL, params=params)
        
        if response.status_code != 200:
            print(f"Erreur API: {response.status_code}")
            break
            
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            break
            
        for record in results:
            station_id = str(record.get("id"))
            if station_id in EXCLUDED_STATIONS:
                continue
                
            gazole = record.get("gazole_prix")
            sp95 = record.get("sp95_prix")
            
            dist = "Autre"
            
            # Priorité 1 : Le mapping GitHub
            if station_id in stations_mapping:
                dist = stations_mapping[station_id].get("brand") or "Autre"
                
            # Priorité 2 : Fallback sur l'adresse (ancienne méthode) si toujours "Autre"
            if dist == "Autre":
                name = record.get("adresse") or ""
                name = name.lower()
                brands = ["total", "carrefour", "leclerc", "auchan", "intermarche", "intermarché", "shell", "bp", "esso", "systeme u", "système u", "casino", "agip", "avia"]
                for b in brands:
                    if b in name:
                        dist = b.capitalize().replace("é", "e").replace("è", "e")
                        break
                        
            # Normalisation et regroupement
            if "Total" in dist or dist in ["Elf", "Elan"]:
                dist = "Total"
            elif "Intermarch" in dist or dist == "Intermarche":
                dist = "Intermarché"
            elif "Carrefour" in dist:
                dist = "Carrefour"
            elif "Esso" in dist:
                dist = "Esso"
            elif dist.upper() in ["BP", "BP EXPRESS", "BP"]:
                dist = "BP"
            elif dist in ["Systeme U", "Système U"]:
                dist = "Système U"
            elif dist in ["Costco Wholesale", "Bi1", "AUTOGRILL", "Netto", "Oil France", "G20", "Simply Market", "Atac", "Monoprix", "Indépendant sans enseigne", "Agip", "Casino"]:
                dist = "Autre"
            
            if gazole is not None: stats[dist]["gazole"].append(gazole)
            if sp95 is not None: stats[dist]["sp95"].append(sp95)
            
        offset += limit
        
    summary = {
        "region": "Île-de-France",
        "brands": {}
    }
    for dist, prices in stats.items():
        summary["brands"][dist] = {
            "gazole_moy": round(sum(prices["gazole"])/len(prices["gazole"]), 3) if prices["gazole"] else None,
            "sp95_moy": round(sum(prices["sp95"])/len(prices["sp95"]), 3) if prices["sp95"] else None,
            "stations_count": max(len(prices["gazole"]), len(prices["sp95"])),
            "date": datetime.now().isoformat()
        }
        
    history = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                history = json.load(f)
            except:
                history = {}
        
    history[datetime.now().strftime("%Y-%m-%d")] = summary
    with open(DATA_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"Collecte terminée. {sum(s['stations_count'] for s in summary['brands'].values())} stations analysées.")

if __name__ == "__main__":
    collect()
