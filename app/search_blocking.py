import os, time, requests
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from app.core.routing import build_routes

app = FastAPI()

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/flights")
engine = create_engine(DB_URL, pool_size=20, max_overflow=10)

PROVIDERS = [
    os.getenv("PROVIDER_1_URL", "http://localhost:8001"),
    os.getenv("PROVIDER_2_URL", "http://localhost:8002"),
    os.getenv("PROVIDER_3_URL", "http://localhost:8003"),
]

def fetch_from_provider(url: str, date: str):
    for attempt in range(2):
        try:
            resp = requests.get(f"{url}/flights", params={"date": date}, timeout=2.0)
            if resp.status_code == 200:
                return resp.json().get("flights", []), True
            elif resp.status_code == 500:
                pass
        except requests.exceptions.RequestException:
            pass
        if attempt == 0:
            time.sleep(0.2)
    return [], False

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/search")
async def search(origin: str, destination: str, date: str):
    start_time = time.time()
    failed_providers = []

    query = text("""
        SELECT carrier, flight_number, origin, destination,
               departure_time, arrival_time, price
        FROM flights
        WHERE CAST(departure_time AS DATE) = :date
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"date": date})
        own_flights = [dict(row._mapping) for row in result]

    provider_flights = []
    for i, url in enumerate(PROVIDERS):
        flights, success = fetch_from_provider(url, date)
        if success:
            filtered = [f for f in flights
                        if f["origin"] == origin or f["destination"] == destination]
            provider_flights.append(filtered)
        else:
            failed_providers.append(f"Provider {i+1}")

    top_20 = build_routes(own_flights, provider_flights, origin, destination)
    process_time = (time.time() - start_time) * 1000

    return {
        "routes": top_20,
        "failed_providers": failed_providers,
        "processing_time_ms": round(process_time, 2),
    }