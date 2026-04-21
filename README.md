# Qui Sont Les Fourbes ? ⛽📊

## But du projet
"Qui Sont Les Fourbes ?" est un projet d'analyse et de suivi des prix des carburants en France. L'objectif est d'observer le comportement des différents distributeurs (Total, Leclerc, Système U, Esso, etc.) face aux fluctuations du cours du pétrole brut (Brent). 

En mettant en parallèle l'évolution du baril et les prix à la pompe, ce projet permet d'identifier quelles enseignes jouent le jeu des baisses de prix, et à l'inverse, qui sont les "fourbes" qui maintiennent des prix artificiellement hauts pour maximiser leurs marges.

## Le Tableau de Bord (Dashboard)
Le projet intègre une interface web (située dans le dossier `dashboard/`) qui permet de visualiser graphiquement :
- L'évolution quotidienne du prix moyen du Gazole et du SP95 par marque.
- La corrélation avec l'évolution du cours du baril de Brent.
- Le classement des distributeurs des moins chers aux plus chers.

## Sources de données
Pour réaliser ces analyses, le projet agrège quotidiennement plusieurs sources de données :

1. **Les prix à la pompe (Gouvernement Français)**  
   Les tarifs bruts sont récupérés via l'API Open Data de l'État : [Prix des carburants en France - Flux instantané v2](https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2).

2. **L'identification des marques (Communauté Open Source)**  
   L'API du gouvernement ne fournissant pas les enseignes associées aux stations, nous utilisons le dictionnaire de mapping maintenu par la communauté Home Assistant via le projet GitHub [Aohzan/hass-prixcarburant](https://github.com/Aohzan/hass-prixcarburant). Cela permet d'associer précisément chaque station à son distributeur.

3. **Le cours du baril (Brent)**  
   Récupéré via le script `fetch_brent.py`, il sert de valeur de référence pour évaluer la répercussion des coûts sur le prix final payé par les automobilistes.

## Fonctionnement
- `fetch_prices.py` : Script principal qui télécharge les prix de l'API gouvernementale, croise les identifiants avec le mapping communautaire pour déduire les marques, et génère l'historique dans `gas_prices.json`.
- `fetch_brent.py` : Récupère et met à jour l'historique du cours du baril dans `brent_prices.json`.
