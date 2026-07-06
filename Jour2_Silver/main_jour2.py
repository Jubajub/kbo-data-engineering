from Jour2_Silver.silver import build_silver_collection
from Jour2_Silver.target_hotel import init_statedb
from Jour2_Silver.scrapper_nbb import run_scraper

def main():
    print("=== JOUR 2 : DEBUT DU PIPELINE ===")
    
    print("\n--- ETAPE 1 : Nettoyage Silver ---")
    # build_silver_collection()
    
    print("\n--- ETAPE 2 : Ciblage (StateDB) ---")
    init_statedb()
    
    print("\n--- ETAPE 3 : Scraping NBB vers HDFS ---")
    # Note : Assure-toi que mock_nbb_api.py tourne dans un autre terminal !
    run_scraper()
    
    print("\n=== JOUR 2 : TERMINE ===")

if __name__ == "__main__":
    main()