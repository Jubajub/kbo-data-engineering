from db import get_db
from pymongo import UpdateOne

TARGET_NACE = ["55100", "55201", "55202", "55203", "55204", "55209", "55300", "55400", "55900"]
EXCLUDED_FORMS = ["110", "114", "116", "117", "301", "302", "303", "310", "320", "330", "340", "350", "400", "411", "412", "413", "414", "415", "416", "417", "418", "419", "420"]

def init_statedb():
    db = get_db()
    
    # Requête de ciblage strict
    query = {
        "Status": "AC",
        "TypeOfEnterprise": "2",
        "JuridicalForm": { "$nin": EXCLUDED_FORMS },
        "activity": {  # <-- Modification ici (singulier)
            "$elemMatch": {
                "Classification": "MAIN",
                "NaceCode": { "$in": TARGET_NACE }
            }
        }
    }
    
    cursor = db["enterprise_silver"].find(query, {"EnterpriseNumber": 1})
    
    operations = []
    for doc in cursor:
        # Upsert pour être idempotent : ne pas écraser les status "done" si on relance
        op = UpdateOne(
            {"enterprise_number": doc["EnterpriseNumber"]},
            {"$setOnInsert": {
                "enterprise_number": doc["EnterpriseNumber"],
                "status": "pending",
                "filings_done": [],
                "filings_count": 0
            }},
            upsert=True
        )
        operations.append(op)
        
        # Batch par 10k pour soulager la RAM
        if len(operations) >= 10000:
            db["statedb"].bulk_write(operations)
            operations = []
            
    if operations:
        db["statedb"].bulk_write(operations)
        
    db["statedb"].create_index("status")
    print(f"✅ StateDB initialisée. Cibles potentielles : {db['statedb'].count_documents({})}")

if __name__ == "__main__":
    init_statedb()