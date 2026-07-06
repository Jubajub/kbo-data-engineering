import random
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(title="Mock NBB CBSO API")

# Génération déterministe pour un BCE donné
def get_filings_for_bce(bce: str):
    random.seed(bce)
    nb_filings = random.randint(2, 6)
    years = sorted(random.sample(range(2020, 2026), nb_filings), reverse=True)
    
    filings = []
    for year in years:
        filings.append({
            "reference": f"{year}-{random.randint(100000, 999999)}",
            "accountingYearEndDate": f"{year}-12-31"
        })
    return filings

@app.get("/api/enterprises/{bce}/filings")
async def list_filings(bce: str, request: Request):
    # Simulation de Rate Limit (5% de chances de throw 429)
    if random.random() < 0.05:
        raise HTTPException(status_code=429, detail="Too Many Requests")
    
    return get_filings_for_bce(bce)

@app.get("/api/filings/{reference}/document", response_class=PlainTextResponse)
async def get_document(reference: str, request: Request):
    if random.random() < 0.05:
        raise HTTPException(status_code=429, detail="Too Many Requests")

    # Extraire l'année de la référence pour varier légèrement les montants
    try:
        year = int(reference.split("-")[0])
    except:
        year = 2023

    random.seed(reference)
    ca = random.uniform(100000, 2000000) # 70 (CA)
    achats = ca * random.uniform(0.3, 0.7) # 60 (Achats)
    ebit = ca - achats # 9901 (EBIT)
    
    csv_lines = [
        "code_pcmn;valeur",
        f"70;{ca:.2f}",
        f"60;{achats:.2f}",
        f"71;{random.uniform(-10000, 10000):.2f}", # Variation stocks
        f"9901;{ebit:.2f}",
        f"9904;{(ebit * 0.7):.2f}", # Résultat net
        f"54;{random.uniform(5000, 50000):.2f}", # Trésorerie
        f"55;{random.uniform(1000, 20000):.2f}",
        f"17;{random.uniform(0, 500000):.2f}", # Dettes > 1 an
        f"43;{random.uniform(10000, 100000):.2f}", # Dettes < 1 an
        f"10;{random.uniform(50000, 500000):.2f}", # Fonds propres (Capital)
        f"100;{random.uniform(50000, 100000):.2f}", # Capital souscrit
    ]
    return "\n".join(csv_lines)

if __name__ == "__main__":
    uvicorn.run("mock_nbb_api:app", host="0.0.0.0", port=8080, reload=True)