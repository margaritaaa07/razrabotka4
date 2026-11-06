import asyncio, os, time
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.routing import build_routes

SUPPLIERS = [
    os.getenv("PROVIDER_1_URL", "http://localhost:8001"),
    os.getenv("PROVIDER_2_URL", "http://localhost:8002"),
    os.getenv("PROVIDER_3_URL", "http://localhost:8003"),
]

# 1. Создание клиента и движка при запуске (lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Заменяем psycopg на asyncpg для асинхронной работы с БД
    url = os.getenv("DATABASE_URL", "").replace("psycopg", "asyncpg")
    app.state.engine = create_async_engine(url, pool_size=10, max_overflow=0)
    async with httpx.AsyncClient(timeout=None, trust_env=False) as client:
        app.state.client = client
        yield
    await app.state.engine.dispose()

app = FastAPI(lifespan=lifespan)

# 2. Асинхронный опрос поставщика с тайм-аутом и повтором
async def fetch_supplier(client, url, date):
    try:
        async with asyncio.timeout(2.0):
            for attempt in range(2):
                try:
                    resp = await client.get(f"{url}/flights", params={"date": date})
                    resp.raise_for_status()
                    return resp.json().get("flights", [])
                except (httpx.HTTPError, ValueError):
                    if attempt == 0:
                        # 3. Пауза через asyncio.sleep
                        await asyncio.sleep(0.2)
    except TimeoutError:
        pass
    return None

# Асинхронное чтение из БД
async def read_db(engine, date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    query = text("""
        SELECT carrier, flight_number, origin, destination,
               departure_time, arrival_time, price
        FROM flights
        WHERE CAST(departure_time AS DATE) = :date
    """)
    async with engine.connect() as conn:
        result = await conn.execute(query, {"date": date_obj})
        return [dict(row._mapping) for row in result]

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/search")
async def search(origin: str, destination: str, date: str):
    start_time = time.time()

    # 2. Одновременный опрос БД и всех поставщиков через asyncio.gather
    tasks = [read_db(app.state.engine, date)]
    tasks.extend([fetch_supplier(app.state.client, url, date) for url in SUPPLIERS])
    results = await asyncio.gather(*tasks)

    own_flights = results[0]
    supplier_results = results[1:]

    # Ошибка одного поставщика не прерывает остальных
    failed_providers = [f"Provider {i+1}" for i, res in enumerate(supplier_results)
                        if res is None]
    provider_flights = []
    for res in supplier_results:
        if res is not None:
            filtered = [f for f in res
                        if f["origin"] == origin or f["destination"] == destination]
            provider_flights.append(filtered)

    top_20 = build_routes(own_flights, provider_flights, origin, destination)
    process_time = (time.time() - start_time) * 1000

    return {
        "routes": top_20,
        "failed_providers": failed_providers,
        "processing_time_ms": round(process_time, 2),
    }