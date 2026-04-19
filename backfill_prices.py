import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
import json
import os

XML_FILE = "/home/openclaw/.openclaw/workspace/PrixCarburants_annuel_2026.xml"
DATA_FILE = "/home/openclaw/.openclaw/workspace/QuiSontLesFourbes/data.json"

def process_history():
    print("Parsing XML... This may take a moment.")
    
    # Structure: stats[date][dist] = {"gazole": [], "sp95": []}
    stats_by_date = defaultdict(lambda: defaultdict(lambda: {"gazole": [], "sp95": []}))
    
    # On lit le fichier ligne par ligne car il est gros
    context = ET.iterparse(XML_FILE, events=("start", "end"))
    
    current_pdv = None
    current_dist = "Autre"
    in_idf = False
    
    for event, elem in context:
        if event == "start" and elem.tag == "pdv":
            cp = elem.get("cp", "")
            # Filtre Ile-de-France (CP commence par 75, 77, 78, 91, 92, 93, 94, 95)
            in_idf = cp.startswith(("75", "77", "78", "91", "92", "93", "94", "95"))
            current_pdv = elem
            current_dist = "Autre"
            
        elif event == "end" and elem.tag == "adresse" and in_idf:
            name = (elem.text or "").lower()
            brands = ["total", "carrefour", "leclerc", "auchan", "intermarche", "intermarché", "shell", "bp", "esso", "systeme u", "système u", "casino", "agip", "avia"]
            for b in brands:
                if b in name:
                    current_dist = b.capitalize().replace("é", "e").replace("è", "e")
                    if current_dist == "Intermarche": current_dist = "Intermarche"
                    if current_dist == "Systeme u": current_dist = "Systeme U"
                    break
                    
        elif event == "end" and elem.tag == "prix" and in_idf:
            # ex: maj="2026-01-02T00:39:00"
            maj = elem.get("maj", "")
            nom = elem.get("nom", "")
            valeur = elem.get("valeur", "")
            
            if maj and valeur and (nom == "Gazole" or nom == "SP95"):
                date_str = maj.split("T")[0]
                try:
                    val_float = float(valeur)
                    if nom == "Gazole":
                        stats_by_date[date_str][current_dist]["gazole"].append(val_float)
                    elif nom == "SP95":
                        stats_by_date[date_str][current_dist]["sp95"].append(val_float)
                except ValueError:
                    pass
                    
        elif event == "end" and elem.tag == "pdv":
            # Free memory
            elem.clear()

    print("Computing averages...")
    
    history = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                history = json.load(f)
            except:
                pass
                
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
                "stations_count": max(len(g_list), len(s_list))
            }
        history[date_str] = summary

    # Rewrite json
    with open(DATA_FILE, 'w') as f:
        json.dump(history, f, indent=2)
        
    print(f"Done. Processed {len(stats_by_date)} days.")

if __name__ == "__main__":
    process_history()
