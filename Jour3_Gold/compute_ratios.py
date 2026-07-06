import socket
from hdfs import InsecureClient
from db import get_db

# --- PATCH DNS HDFS (Requis pour Docker sous Windows) ---
original_getaddrinfo = socket.getaddrinfo

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if port == 9864:
        host = "127.0.0.1"
    return original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = patched_getaddrinfo
# --------------------------------------------------------

HDFS_URL = "http://localhost:9870"

def generate_gold_layer():
    db = get_db()
    hdfs_client = InsecureClient(HDFS_URL, user="root")
    
    # On cible uniquement les entreprises dont le scraping a réussi dans la StateDB
    targets = db["statedb"].find({"status": "done"})
    
    # Réinitialiser la table Gold pour éviter les doublons lors des tests
    db["enterprise_gold"].drop()
    
    gold_records = []
    total_processed = 0
    
    print(" Lancement de l'analyse financière vers la couche Gold...")
    
    for state in targets:
        bce = state["enterprise_number"]
        
        try:
            # Lister les dossiers d'années disponibles pour cette entreprise dans HDFS
            years = hdfs_client.list(f"/{bce}/hbb")
        except Exception:
            continue  # Le dossier n'existe pas dans HDFS
            
        for year in years:
            try:
                files = hdfs_client.list(f"/{bce}/hbb/{year}")
                for file in files:
                    if not file.endswith(".csv"):
                        continue
                        
                    path = f"/{bce}/hbb/{year}/{file}"
                    reference = file.replace(".csv", "")
                    
                    # Lecture du fichier depuis HDFS directement en mémoire (sans l'écrire sur le disque local)
                    with hdfs_client.read(path) as reader:
                        content = reader.read().decode("utf-8")
                        
                    # Parsing du CSV "code_pcmn;valeur"
                    data = {}
                    lines = content.split("\n")
                    for line in lines[1:]:  # Ignorer la ligne d'en-tête
                        if ";" in line:
                            code, val = line.split(";")
                            try:
                                data[code] = float(val)
                            except ValueError:
                                pass
                                
                    # Extraction des variables selon les codes PCMN du Mock
                    ca = data.get("70", 0.0)
                    resultat_net = data.get("9904", 0.0)
                    fonds_propres = data.get("10", 0.0)
                    tresorerie = data.get("54", 0.0) + data.get("55", 0.0)
                    dettes_ct = data.get("43", 0.0)
                    
                    # Calculs financiers (avec protection division par 0)
                    roe = round((resultat_net / fonds_propres) * 100, 2) if fonds_propres != 0 else None
                    marge_nette = round((resultat_net / ca) * 100, 2) if ca != 0 else None
                    liquidite_reduite = round(tresorerie / dettes_ct, 2) if dettes_ct != 0 else None
                    
                    gold_records.append({
                        "EnterpriseNumber": bce,
                        "Year": int(year),
                        "Reference": reference,
                        "ChiffreAffaires": ca,
                        "ResultatNet": resultat_net,
                        "FondsPropres": fonds_propres,
                        "ROE_percent": roe,
                        "MargeNette_percent": marge_nette,
                        "LiquiditeReduite_ratio": liquidite_reduite
                    })
                    total_processed += 1
                    
            except Exception as e:
                print(f"⚠️ Erreur lors du traitement de {bce} ({year}) : {e}")
                
        # Bulk insert par lots de 1000 pour préserver la RAM
        if len(gold_records) >= 1000:
            db["enterprise_gold"].insert_many(gold_records)
            gold_records = []
            
    # Insérer le reliquat
    if gold_records:
        db["enterprise_gold"].insert_many(gold_records)
        
    # Création d'index pour faciliter les futures requêtes d'analyse
    db["enterprise_gold"].create_index([("EnterpriseNumber", 1), ("Year", -1)])
    db["enterprise_gold"].create_index("ROE_percent")
    
    print(f"✅ Couche Gold générée avec succès ! {total_processed} bilans financiers analysés.")

if __name__ == "__main__":
    generate_gold_layer()