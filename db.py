"""
db.py
Connexion centralisée à MongoDB + rapport de connexion.
"""

import time
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

MONGO_URI = "mongodb://admin:password123@localhost:27017/"
DB_NAME = "kbo_database"


def get_db(uri: str = MONGO_URI, db_name: str = DB_NAME, verbose: bool = True):
    """
    Ouvre une connexion MongoDB et renvoie l'objet database.
    Lève une exception claire si le serveur est injoignable.
    """
    start = time.time()
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)

    try:
        client.admin.command("ping")
        duration = time.time() - start
        if verbose:
            print(f"✅ Connexion MongoDB réussie -> {uri} (db='{db_name}') en {duration:.2f}s")
        return client[db_name]
    except ServerSelectionTimeoutError as e:
        print(f"❌ Impossible de joindre MongoDB sur {uri} : {e}")
        raise


def connection_report(uri: str = MONGO_URI, db_name: str = DB_NAME) -> dict:
    """
    Renvoie un mini rapport structuré sur l'état de la connexion,
    utilisé par main.py pour construire le rapport final.
    """
    report = {"uri": uri, "db_name": db_name, "status": None, "duration_s": None, "error": None}
    start = time.time()
    try:
        db = get_db(uri, db_name, verbose=False)
        report["status"] = "OK"
        report["duration_s"] = round(time.time() - start, 2)
        report["collections_existantes"] = db.list_collection_names()
    except Exception as e:
        report["status"] = "ERROR"
        report["duration_s"] = round(time.time() - start, 2)
        report["error"] = str(e)
    return report


if __name__ == "__main__":
    db = get_db()
    print("Collections existantes :", db.list_collection_names())