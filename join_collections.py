"""
join_collections.py
Fait la jointure entre toutes les collections importées, en se basant sur
EnterpriseNumber (collection pivot: "enterprise") et EntityNumber
(clé utilisée par la plupart des collections annexes de la BCE/KBO).

Résultat : une collection unique "entreprises_completes" où chaque document
"enterprise" embarque ses dénominations, adresses, activités, contacts,
établissements, etc.
"""

import time
from pymongo import MongoClient

from db import MONGO_URI, DB_NAME

# Pour chaque collection annexe : quelle clé côté "foreign" correspond
# à EnterpriseNumber côté collection pivot "enterprise".
JOIN_MAP = {
    "denomination": "EntityNumber",
    "address": "EntityNumber",
    "contact": "EntityNumber",
    "activity": "EntityNumber",
    "establishment": "EnterpriseNumber",
    "branch": "EnterpriseNumber",
}

PIVOT_COLLECTION = "enterprise"
OUTPUT_COLLECTION = "entreprises_completes"


def build_joined_collection(uri: str = MONGO_URI, db_name: str = DB_NAME) -> dict:
    client = MongoClient(uri)
    db = client[db_name]

    existing = db.list_collection_names()
    if PIVOT_COLLECTION not in existing:
        raise RuntimeError(
            f"Collection pivot '{PIVOT_COLLECTION}' introuvable. "
            "Importez d'abord les CSV (import_csv.py)."
        )

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
                "localField": "EnterpriseNumber",
                "foreignField": join_key,
                "as": coll_name,
            }
        })
        joined.append(coll_name)

    pipeline.append({"$out": OUTPUT_COLLECTION})

    print(f"🔗 Jointure de '{PIVOT_COLLECTION}' avec : {joined}")
    if skipped:
        print(f"⚠️ Collections absentes, ignorées : {skipped}")

    start = time.time()
    list(db[PIVOT_COLLECTION].aggregate(pipeline, allowDiskUse=True))
    duration = time.time() - start

    count = db[OUTPUT_COLLECTION].count_documents({})
    # Index pour accélérer les recherches ultérieures par numéro d'entreprise
    db[OUTPUT_COLLECTION].create_index("EnterpriseNumber", unique=True)

    print(f"✅ Jointure terminée en {duration:.1f}s — {count} documents dans '{OUTPUT_COLLECTION}'")

    return {
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
