# Rapport d'exécution — 2026-07-02T13:50:28

## 1. Connexion MongoDB
- URI : `mongodb://localhost:27017`
- Base : `kbo_database`
- Statut : **OK**
- Durée : 0.12s

## 2. Import des CSV
- 9 collection(s) importée(s) avec succès, 0 en erreur.

| Collection | Fichier | Statut | Durée (s) |
|---|---|---|---|
| activity | ./data/csv\activity.csv | OK | 998.23 |
| address | ./data/csv\address.csv | OK | 150.85 |
| branch | ./data/csv\branch.csv | OK | 0.24 |
| code | ./data/csv\code.csv | OK | 0.73 |
| contact | ./data/csv\contact.csv | OK | 17.67 |
| denomination | ./data/csv\denomination.csv | OK | 84.83 |
| enterprise | ./data/csv\enterprise.csv | OK | 65.3 |
| establishment | ./data/csv\establishment.csv | OK | 37.93 |
| meta | ./data/csv\meta.csv | OK | 0.03 |

## 3. Jointure des collections
### Index créés avant jointure
| Collection | Champ | Statut | Durée (s) |
|---|---|---|---|
| enterprise | EnterpriseNumber | OK | 7.03 |
| denomination | EntityNumber | OK | 15.6 |
| address | EntityNumber | OK | 18.08 |
| contact | EntityNumber | OK | 2.69 |
| activity | EntityNumber | OK | 172.63 |
| establishment | EnterpriseNumber | OK | 9.37 |
| branch | EnterpriseNumber | OK | 0.08 |

- Collection pivot : `enterprise`
- Collection résultat : `entreprises_completes`
- Collections jointes : denomination, address, contact, activity, establishment, branch
- Documents générés : 1951671
- Durée : 344.28s
