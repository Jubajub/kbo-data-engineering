import time
import random
import requests
import socket 

from hdfs import InsecureClient
from db import get_db
from utils import get_tor_session, renew_tor_ip, TOR_NODES # Import de ton utilitaire existant


# --- DEBUT DU PATCH DNS POUR HDFS (DOCKER) ---
original_getaddrinfo = socket.getaddrinfo

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    # Si la requête cible le port 9864 (WebHDFS Datanode), on force le trafic vers localhost
    if port == 9864:
        host = "127.0.0.1"
    return original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = patched_getaddrinfo
# --- FIN DU PATCH DNS ---

NBB_BASE_URL = "http://localhost:8080"
HDFS_URL = "http://localhost:9870"

def get_resilient_session(node_index: int):
    # Désactivation du routage Tor pour attaquer le Mock local
    return requests.Session()

def run_scraper():
    db = get_db()
    hdfs_client = InsecureClient(HDFS_URL, user="root")
    
    current_tor_idx = 0
    session = get_resilient_session(current_tor_idx)
    
    # Récupérer pending + in_progress (reprise sur crash)
    targets = db["statedb"].find({"status": { "$in": ["pending", "in_progress"] }})
    
    for state in targets:
        bce = state["enterprise_number"]
        db["statedb"].update_one({"_id": state["_id"]}, {"$set": {"status": "in_progress"}})
        
        # 1. Fetch Filings
        filings = None
        while filings is None:
            res = session.get(f"{NBB_BASE_URL}/api/enterprises/{bce}/filings")
            if res.status_code == 429:
                print(f"⚠️ 429 sur {bce} (filings) - Rotation IP...")
                renew_tor_ip(TOR_NODES[current_tor_idx]["ctrl_port"], TOR_NODES[current_tor_idx]["password"])
                current_tor_idx = (current_tor_idx + 1) % len(TOR_NODES)
                session = get_resilient_session(current_tor_idx)
                time.sleep(2)
            elif res.status_code == 200:
                filings = res.json()
            else:
                filings = [] # Autre erreur, on passe
                
        # Filtrer >= 2021
        valid_filings = [f for f in filings if f.get("accountingYearEndDate", "") >= "2021-01-01"]
        
        # 2. Fetch Documents
        for filing in valid_filings:
            ref = filing["reference"]
            year = filing["accountingYearEndDate"].split("-")[0]
            
            # Vérifier si déjà téléchargé lors d'un crash précédent
            if ref in state.get("filings_done", []):
                continue
                
            csv_data = None
            while csv_data is None:
                res = session.get(f"{NBB_BASE_URL}/api/filings/{ref}/document")
                if res.status_code == 429:
                    print(f"⚠️ 429 sur doc {ref} - Rotation IP...")
                    renew_tor_ip(TOR_NODES[current_tor_idx]["ctrl_port"], TOR_NODES[current_tor_idx]["password"])
                    current_tor_idx = (current_tor_idx + 1) % len(TOR_NODES)
                    session = get_resilient_session(current_tor_idx)
                    time.sleep(2)
                elif res.status_code == 200:
                    csv_data = res.text
                else:
                    csv_data = "" # Document introuvable
            
            if csv_data:
                # 3. Ecriture HDFS
                hdfs_path = f"/{bce}/hbb/{year}/{ref}.csv"
                # with hdfs_client.write... crée le fichier de manière distribuée
                with hdfs_client.write(hdfs_path, overwrite=True, encoding="utf-8") as writer:
                    writer.write(csv_data)
                
                # Update incrémental StateDB (très important pour la résilience)
                db["statedb"].update_one(
                    {"_id": state["_id"]},
                    {
                        "$push": {"filings_done": ref},
                        "$inc": {"filings_count": 1}
                    }
                )
        
        # Marquer l'entreprise comme terminée
        db["statedb"].update_one({"_id": state["_id"]}, {"$set": {"status": "done"}})
        print(f"✅ BCE {bce} traité. Dépôts scrappés : {len(valid_filings)}")

if __name__ == "__main__":
    run_scraper()