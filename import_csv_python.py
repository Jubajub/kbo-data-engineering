"""
import_csv_python.py
Alternative à import_csv.py qui n'a besoin d'aucun outil externe
(pas de mongoimport) : lecture des CSV avec pandas, insertion par lots
dans MongoDB avec pymongo.

Utile si l'installation de mongodb-database-tools pose problème (Windows).
"""

import glob
import os
import time

import pandas as pd

from db import get_db, MONGO_URI, DB_NAME

CSV_DIR = "./data/csv"
CHUNK_SIZE = 20000  # nombre de lignes lues/insérées par lot


def import_all_csv(csv_dir: str = CSV_DIR, uri: str = MONGO_URI, db_name: str = DB_NAME) -> list:
    db = get_db(uri, db_name)
    report = []

    csv_files = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))
    if not csv_files:
        print(f" Aucun fichier CSV trouvé dans '{csv_dir}'")
        return report

    print(f" {len(csv_files)} fichier(s) CSV détecté(s) dans '{csv_dir}'\n")

    for csv_path in csv_files:
        collection_name = os.path.splitext(os.path.basename(csv_path))[0].lower()
        coll = db[collection_name]
        coll.drop()  # repart propre si le script est relancé

        start = time.time()
        total_rows = 0
        error = None

        try:
            for chunk in pd.read_csv(csv_path, chunksize=CHUNK_SIZE, dtype=str, keep_default_na=False):
                records = chunk.to_dict(orient="records")
                if records:
                    coll.insert_many(records, ordered=False)
                    total_rows += len(records)
                    print(f"   ...{collection_name} : {total_rows} lignes insérées", end="\r")
            print()
        except Exception as e:
            error = str(e)

        duration = time.time() - start

        if error:
            print(f" [{collection_name}] erreur : {error}")
            report.append({
                "collection": collection_name,
                "file": csv_path,
                "status": "ERROR",
                "duration_s": round(duration, 2),
                "error": error,
            })
        else:
            print(f" [{collection_name}] {total_rows} lignes importées en {duration:.1f}s")
            report.append({
                "collection": collection_name,
                "file": csv_path,
                "status": "OK",
                "duration_s": round(duration, 2),
                "rows": total_rows,
            })

    return report


if __name__ == "__main__":
    r = import_all_csv()
    for line in r:
        print(line)