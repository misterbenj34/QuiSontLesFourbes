import json
import os

DATA_FILE = "/home/openclaw/.openclaw/workspace/QuiSontLesFourbes/gas_prices.json"

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

def process():
    if not os.path.exists(DATA_FILE):
        print("Fichier non trouvé.")
        return

    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    for date_key, day_data in data.items():
        old_brands = day_data.get("brands", {})
        new_brands = {}
        agg_data = {}
        
        for brand_name, metrics in old_brands.items():
            new_name = normalize_brand(brand_name)
            
            if new_name not in agg_data:
                agg_data[new_name] = {
                    "gazole_sum": 0.0,
                    "gazole_count": 0,
                    "sp95_sum": 0.0,
                    "sp95_count": 0,
                    "stations_count": 0,
                    "date": metrics.get("date")
                }
            
            # Utilisation du nombre de stations comme poids pour recalculer la moyenne pondérée
            st_count = metrics.get("stations_count", 0)
            
            if metrics.get("gazole_moy") is not None:
                agg_data[new_name]["gazole_sum"] += metrics["gazole_moy"] * st_count
                agg_data[new_name]["gazole_count"] += st_count
                
            if metrics.get("sp95_moy") is not None:
                agg_data[new_name]["sp95_sum"] += metrics["sp95_moy"] * st_count
                agg_data[new_name]["sp95_count"] += st_count
                
            agg_data[new_name]["stations_count"] += st_count
        
        # Recalcul des moyennes
        for new_name, totals in agg_data.items():
            gazole_moy = round(totals["gazole_sum"] / totals["gazole_count"], 3) if totals["gazole_count"] > 0 else None
            sp95_moy = round(totals["sp95_sum"] / totals["sp95_count"], 3) if totals["sp95_count"] > 0 else None
            
            new_brands[new_name] = {
                "gazole_moy": gazole_moy,
                "sp95_moy": sp95_moy,
                "stations_count": totals["stations_count"],
                "date": totals["date"]
            }
            
        data[date_key]["brands"] = new_brands
        
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    process()
    print("Historique retraité avec succès.")