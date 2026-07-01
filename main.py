"""
main.py
Enchaîne les 3 étapes et génère un rapport final (console + fichier report.md) :
  1. Connexion MongoDB
  2. Import des CSV (une collection par fichier)
  3. Jointure des collections (EnterpriseNumber / EntityNumber)
"""

import datetime

from db import connection_report, MONGO_URI, DB_NAME
from import_csv_python  import import_all_csv, CSV_DIR
from join_collections import build_joined_collection


def write_report(conn_report: dict, import_report: list, join_report: dict, path: str = "report.md"):
    lines = []
    lines.append(f"# Rapport d'exécution — {datetime.datetime.now().isoformat(timespec='seconds')}\n")

    # 1. Connexion
    lines.append("## 1. Connexion MongoDB")
    lines.append(f"- URI : `{conn_report['uri']}`")
    lines.append(f"- Base : `{conn_report['db_name']}`")
    lines.append(f"- Statut : **{conn_report['status']}**")
    lines.append(f"- Durée : {conn_report['duration_s']}s")
    if conn_report.get("error"):
        lines.append(f"- Erreur : {conn_report['error']}")
    lines.append("")

    # 2. Import CSV
    lines.append("## 2. Import des CSV")
    if not import_report:
        lines.append("- Aucun fichier importé.")
    else:
        ok = [r for r in import_report if r["status"] == "OK"]
        ko = [r for r in import_report if r["status"] == "ERROR"]
        lines.append(f"- {len(ok)} collection(s) importée(s) avec succès, {len(ko)} en erreur.\n")
        lines.append("| Collection | Fichier | Statut | Durée (s) |")
        lines.append("|---|---|---|---|")
        for r in import_report:
            lines.append(f"| {r['collection']} | {r['file']} | {r['status']} | {r.get('duration_s', '-')} |")
    lines.append("")

    # 3. Jointure
    lines.append("## 3. Jointure des collections")
    lines.append(f"- Collection pivot : `{join_report['collection_pivot']}`")
    lines.append(f"- Collection résultat : `{join_report['collection_sortie']}`")
    lines.append(f"- Collections jointes : {', '.join(join_report['collections_jointes']) or 'aucune'}")
    if join_report["collections_ignorees"]:
        lines.append(f"- Collections ignorées (absentes) : {', '.join(join_report['collections_ignorees'])}")
    lines.append(f"- Documents générés : {join_report['documents_generes']}")
    lines.append(f"- Durée : {join_report['duration_s']}s")
    lines.append("")

    content = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n📄 Rapport écrit dans {path}")
    return content


def main():
    print("=== ÉTAPE 1/3 : Connexion MongoDB ===")
    conn_report = connection_report()
    if conn_report["status"] != "OK":
        print("❌ Arrêt : impossible de continuer sans connexion MongoDB.")
        return

    print("\n=== ÉTAPE 2/3 : Import des CSV ===")
    import_report = import_all_csv(csv_dir=CSV_DIR)

    print("\n=== ÉTAPE 3/3 : Jointure des collections ===")
    join_report = build_joined_collection()

    write_report(conn_report, import_report, join_report)


if __name__ == "__main__":
    main()
