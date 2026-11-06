import os, random, asyncio, datetime
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

DELAY_MS = int(os.getenv("DELAY_MS", "300"))
ERROR_500_PCT = float(os.getenv("ERROR_500_PCT", "5"))
ERROR_3S_PCT = float(os.getenv("ERROR_3S_PCT", "0"))
PROVIDER_ID = os.getenv("PROVIDER_ID", "1")

AIRPORTS = ['SVO','DME','VKO','LED','KZN','OVB','SVX','AER','ROV','KRR',
            'UFA','KUF','CEK','IKT','KJA','VVO','KHV','TJM','OMS','OSB',
            'MRV','BZK','TUL','PEE','STW','ASF','BQS','CIT','MJZ','HTA']

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/flights")
async def get_flights(date: str = Query(...)):
    delay = (DELAY_MS * random.uniform(0.7, 1.3)) / 1000.0
    await asyncio.sleep(delay)

    if random.random() * 100 < ERROR_500_PCT:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    if random.random() * 100 < ERROR_3S_PCT:
        await asyncio.sleep(3)

    random.seed(f"{PROVIDER_ID}_{date}")
    flights = []
    for _ in range(500):
        origin = random.choice(AIRPORTS)
        destination = random.choice([a for a in AIRPORTS if a != origin])
        dep_time = datetime.datetime.strptime(date, "%Y-%m-%d") + \
            datetime.timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
        arr_time = dep_time + datetime.timedelta(hours=random.randint(1, 6))

        flights.append({
            "carrier": f"P{PROVIDER_ID}",
            "flight_number": str(random.randint(100, 999)),
            "origin": origin,
            "destination": destination,
            "departure_time": dep_time.isoformat(),
            "arrival_time": arr_time.isoformat(),
            "price": random.randint(3000, 30000),
        })
    return {"flights": flights}