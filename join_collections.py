"""
join_collections.py
Fait la jointure entre toutes les collections importées, en se basant sur
EnterpriseNumber (collection pivot: "enterprise") et EntityNumber/EnterpriseNumber
selon la collection (la clé n'est pas la même partout dans les données BCE/KBO).

Avant la jointure : création des index nécessaires sur CHAQUE collection,
sur la clé qui lui correspond, pour que $lookup soit rapide (sinon MongoDB
scanne toute la collection à chaque jointure).

Résultat : une collection unique "entreprises_completes" où chaque document
"enterprise" embarque ses dénominations, adresses, activités, contacts,
établissements, etc.
"""

import time
from pymongo import MongoClient

from db import MONGO_URI, DB_NAME

# Pour chaque collection annexe : quelle clé côté "foreign" correspond
# à EnterpriseNumber côté collection pivot "enterprise".
# ATTENTION : la clé n'est pas toujours "EnterpriseNumber", certaines
# collections BCE/KBO utilisent "EntityNumber" à la place.
JOIN_MAP = {
    "denomination": "EntityNumber",
    "address": "EntityNumber",
    "contact": "EntityNumber",
    "activity": "EntityNumber",
    "establishment": "EnterpriseNumber",
    "branch": "EnterpriseNumber",
}

PIVOT_COLLECTION = "enterprise"
PIVOT_KEY = "EnterpriseNumber"
OUTPUT_COLLECTION = "entreprises_completes"


def ensure_indexes(db, uri: str = MONGO_URI) -> list:
    """
    Crée un index sur la clé de jointure de chaque collection concernée
    (y compris la collection pivot). Renvoie un rapport par collection.
    """
    index_report = []
    existing = db.list_collection_names()

    # Index sur la collection pivot elle-même
    if PIVOT_COLLECTION in existing:
        start = time.time()
        db[PIVOT_COLLECTION].create_index(PIVOT_KEY)
        duration = time.time() - start
        print(f" Index créé sur '{PIVOT_COLLECTION}.{PIVOT_KEY}' en {duration:.2f}s")
        index_report.append({
            "collection": PIVOT_COLLECTION,
            "champ": PIVOT_KEY,
            "status": "OK",
            "duration_s": round(duration, 2),
        })

    # Index sur chaque collection annexe, sur SA clé propre
    for coll_name, join_key in JOIN_MAP.items():
        if coll_name not in existing:
            print(f" Collection '{coll_name}' absente, index ignoré")
            index_report.append({
                "collection": coll_name,
                "champ": join_key,
                "status": "SKIPPED",
            })
            continue

        start = time.time()
        try:
            db[coll_name].create_index(join_key)
            duration = time.time() - start
            print(f" Index créé sur '{coll_name}.{join_key}' en {duration:.2f}s")
            index_report.append({
                "collection": coll_name,
                "champ": join_key,
                "status": "OK",
                "duration_s": round(duration, 2),
            })
        except Exception as e:
            duration = time.time() - start
            print(f" Erreur index '{coll_name}.{join_key}' : {e}")
            index_report.append({
                "collection": coll_name,
                "champ": join_key,
                "status": "ERROR",
                "duration_s": round(duration, 2),
                "error": str(e),
            })

    return index_report


def build_joined_collection(uri: str = MONGO_URI, db_name: str = DB_NAME) -> dict:
    # socketTimeoutMS=None demande au script Python de patienter indéfiniment
    client = MongoClient(uri, socketTimeoutMS=None)
    db = client[db_name]

    existing = db.list_collection_names()
    if PIVOT_COLLECTION not in existing:
        raise RuntimeError(
            f"Collection pivot '{PIVOT_COLLECTION}' introuvable. "
            "Importez d'abord les CSV (import_csv.py / import_csv_python.py)."
        )

    # --- Étape 1 : index avant jointure ---
    print("=== Création des index avant jointure ===")
    index_report = ensure_indexes(db, uri)
    print()

    # --- Étape 2 : construction du pipeline $lookup ---
    pipeline = []
    joined = []
    skipped = []

    for coll_name, join_key in JOIN_MAP.items():
        if coll_name not in existing:
            skipped.append(coll_name)
            continue
        pipeline.append({
            "$lookup": {
                "from": coll_name,
                "localField": PIVOT_KEY,
                "foreignField": join_key,
                "as": coll_name,
            }
        })
        joined.append(coll_name)

    pipeline.append({"$out": OUTPUT_COLLECTION})

    print(f" Jointure de '{PIVOT_COLLECTION}' avec : {joined}")
    if skipped:
        print(f" Collections absentes, ignorées : {skipped}")

    start = time.time()
    list(db[PIVOT_COLLECTION].aggregate(pipeline, allowDiskUse=True))
    duration = time.time() - start

    count = db[OUTPUT_COLLECTION].count_documents({})
    # Index sur la collection résultat pour accélérer les recherches ultérieures
    db[OUTPUT_COLLECTION].create_index(PIVOT_KEY, unique=True)

    print(f" Jointure terminée en {duration:.1f}s — {count} documents dans '{OUTPUT_COLLECTION}'")

    return {
        "index_report": index_report,
        "collection_pivot": PIVOT_COLLECTION,
        "collection_sortie": OUTPUT_COLLECTION,
        "collections_jointes": joined,
        "collections_ignorees": skipped,
        "documents_generes": count,
        "duration_s": round(duration, 2),
    }


if __name__ == "__main__":
    r = build_joined_collection()
    print(r)