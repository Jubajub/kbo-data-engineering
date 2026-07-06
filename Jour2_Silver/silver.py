import time
from db import get_db

def build_silver_collection():
    db = get_db()
    
    # ⚠️ Indispensable avant de lancer le $lookup sur 1.95M docs
    db["code"].create_index([("Category", 1), ("Code", 1)])
    
    print(" Lancement du pipeline d'agrégation (cela peut prendre plusieurs minutes)...")
    start = time.time()
    
    pipeline = [
        # 1. Nettoyage de base : Date, Adresses, Tris
        {
            "$set": {
                "StartDate": {
                    "$cond": {
                        "if": { "$regexMatch": { "input": "$StartDate", "regex": "^\\d{2}-\\d{2}-\\d{4}$" } },
                        "then": { 
                            "$dateToString": { 
                                "format": "%Y-%m-%d", 
                                "date": { "$dateFromString": { "dateString": "$StartDate", "format": "%d-%m-%Y" } } 
                            } 
                        },
                        "else": "$StartDate"
                    }
                },
                "address": {
                    "$filter": {
                        "input": "$address",
                        "as": "addr",
                        "cond": { "$eq": ["$$addr.TypeOfAddress", "REGO"] }
                    }
                },
                "denomination": {
                    "$sortArray": {
                        "input": "$denomination",
                        "sortBy": { "TypeOfDenomination": 1 }
                    }
                },
                # 2. Déduplication complexe des activités
                "activities": {
                    "$reduce": {
                        "input": "$activities",
                        "initialValue": [],
                        "in": {
                            "$cond": [
                                # Vérifie si la combinaison NaceCode + Classification existe déjà dans l'accumulateur
                                { "$in": [ 
                                    { "NaceCode": "$$this.NaceCode", "Classification": "$$this.Classification" },
                                    { "$map": { "input": "$$value", "as": "v", "in": { "NaceCode": "$$v.NaceCode", "Classification": "$$v.Classification" } } }
                                ]},
                                "$$value",
                                { "$concatArrays": ["$$value", ["$$this"]] }
                            ]
                        }
                    }
                }
            }
        },
        # 3. Enrichissements (Lookups sur la collection "code")
        # JuridicalForm
        {
            "$lookup": {
                "from": "code",
                "let": { "jf": "$JuridicalForm" },
                "pipeline": [
                    { "$match": { "$expr": { "$and": [ 
                        { "$eq": ["$Category", "JuridicalForm"] }, 
                        { "$eq": ["$Code", "$$jf"] },
                        { "$eq": ["$Language", "FR"] } # Optionnel : selon la structure de ton CSV code
                    ]}}}
                ],
                "as": "_jf_doc"
            }
        },
        { "$set": { "JuridicalFormLabel": { "$arrayElemAt": ["$_jf_doc.Description", 0] } } },
        { "$unset": "_jf_doc" },
        
        # 4. Écriture finale
        { "$out": "enterprise_silver" }
    ]
    
    # allowDiskUse est obligatoire pour les grosses volumétries
    db["entreprises_completes"].aggregate(pipeline, allowDiskUse=True)
    
    count = db["enterprise_silver"].count_documents({})
    # Création d'index pour la suite
    db["enterprise_silver"].create_index("EnterpriseNumber", unique=True)
    db["enterprise_silver"].create_index("Status")
    db["enterprise_silver"].create_index("activities.NaceCode")
    
    print(f"✅ Collection Silver créée en {time.time() - start:.1f}s avec {count} documents.")

if __name__ == "__main__":
    build_silver_collection()