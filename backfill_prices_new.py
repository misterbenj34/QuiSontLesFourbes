import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
import json
import os
import requests

XML_FILE = "/home/openclaw/.openclaw/workspace/PrixCarburants_annuel_2026.xml"
DATA_FILE = "/home/openclaw/.openclaw/workspace/QuiSontLesFourbes/gas_prices.json"
MAPPING_URL = "https://raw.githubusercontent.com/Aohzan/hass-prixcarburant/master/custom_components/prix_carburant/stations_name.json"

# Stations with erratic/abnormally high regular prices skewing the "Autre" category
EXCLUDED_STATIONS = {"75016026", "75001003", "94290003", "77860002", "75017019"}

def normalize_brand(dist):
    if "Total" in dist or dist in ["Elf", "Elan"]:
        return "Total"
    elif "Intermarch" in dist or dist == "Intermarche":
        return "Intermarché"
    elif "Carrefour" in dist:
        return "Carrefour"
    elif "Esso" in dist:
        return "Esso"
    elif dist.upper() in ["BP", "BP EXPRESS"]:
        return "BP"
    elif dist in ["Systeme U", "Système U"]:
        return "Système U"
    elif dist in ["Auchan", "Leclerc", "Shell", "Avia"]:
        return dist
    else:
        return "Autre"

def process_history():
    print("Récupération du dictionnaire des marques...")
    try:
        mapping_req = requests.get(MAPPING_URL)
        stations_mapping = mapping_req.json()
    except Exception as e:
        print(f"Erreur lors de la récupération du mapping: {e}")
        stations_mapping = {}

    print("Parsing XML... This may take a moment.")
    
    # Structure: stats[date][dist] = {"gazole": [], "sp95": []}
    stats_by_date = defaultdict(lambda: defaultdict(lambda: {"gazole": [], "sp95": []}))
    
    context = ET.iterparse(XML_FILE, events=("start", "end"))
    
    current_pdv_id = None
    current_dist = "Autre"
    in_idf = False
    current_name = ""
    
    for event, elem in context:
        if event == "start" and elem.tag == "pdv":
            cp = elem.get("cp", "")
            in_idf = cp.startswith(("75", "77", "78", "91", "92", "93", "94", "95"))
            current_pdv_id = elem.get("id", "")
            current_dist = "Autre"
            current_name = ""
            
        elif event == "end" and elem.tag == "adresse" and in_idf:
            current_name = (elem.text or "").lower()
                    
        elif event == "end" and elem.tag == "prix" and in_idf:
            if current_pdv_id in EXCLUDED_STATIONS:
                continue
                
            # We process price and brand logic here because we now have the address if needed
            # Priority 1: GitHub mapping
            if current_pdv_id in stations_mapping:
                dist = stations_mapping[current_pdv_id].get("brand") or "Autre"
            else:
                dist = "Autre"
                brands = ["total", "carrefour", "leclerc", "auchan", "intermarche", "intermarché", "shell", "bp", "esso", "systeme u", "système u", "casino", "agip", "avia"]
                for b in brands:
                    if b in current_name:
                        dist = b.capitalize().replace("é", "e").replace("è", "e")
                        break
            
            dist = normalize_brand(dist)
            
            maj = elem.get("maj", "")
            nom = elem.get("nom", "")
            valeur = elem.get("valeur", "")
            
            if maj and valeur and (nom == "Gazole" or nom == "SP95"):
                date_str = maj.split("T")[0]
                try:
                    val_float = float(valeur)
                    if nom == "Gazole":
                        stats_by_date[date_str][dist]["gazole"].append(val_float)
                    elif nom == "SP95":
                        stats_by_date[date_str][dist]["sp95"].append(val_float)
                except ValueError:
                    pass
                    
        elif event == "end" and elem.tag == "pdv":
            # Free memory
            elem.clear()

    print("Computing averages...")
    
    # We will override the history completely to ensure consistency from Jan 1st
    history = {}
    
    for date_str, dists in sorted(stats_by_date.items()):
        summary = {
            "region": "Île-de-France",
            "brands": {}
        }
        for dist, prices in dists.items():
            g_list = prices["gazole"]
            s_list = prices["sp95"]
            summary["brands"][dist] = {
                "gazole_moy": round(sum(g_list)/len(g_list), 3) if g_list else None,
                "sp95_moy": round(sum(s_list)/len(s_list), 3) if s_list else None,
                "stations_count": max(len(g_list), len(s_list)),
                "date": date_str
            }
        history[date_str] = summary

    # Rewrite json
    with open(DATA_FILE, 'w') as f:
        json.dump(history, f, indent=2)
        
    print(f"Done. Processed {len(stats_by_date)} days.")

if __name__ == "__main__":
    process_history()