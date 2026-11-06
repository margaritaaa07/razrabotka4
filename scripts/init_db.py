import os, random, datetime
from sqlalchemy import (create_engine, insert, Table, Column, String,
                        Integer, DateTime, Numeric, MetaData, text)

DB_URL = os.getenv("DB_URL", "postgresql+psycopg://user:password@localhost:5432/flights")
engine = create_engine(DB_URL)

# Описание структуры таблицы
metadata = MetaData()
flights_table = Table(
    "flights", metadata,
    Column("id", Integer, primary_key=True),
    Column("carrier", String(10)),
    Column("flight_number", String(10)),
    Column("origin", String(3)),
    Column("destination", String(3)),
    Column("departure_time", DateTime),
    Column("arrival_time", DateTime),
    Column("price", Numeric(10, 2)),
)

AIRPORTS = ['SVO','DME','VKO','LED','KZN','OVB','SVX','AER','ROV','KRR',
            'UFA','KUF','CEK','IKT','KJA','VVO','KHV','TJM','OMS','OSB',
            'MRV','BZK','TUL','PEE','STW','ASF','BQS','CIT','MJZ','HTA']
CARRIERS = ['SU','S7','U6','DP','WZ','UT','N4','5N']

def init_db():
    print("1. Создание таблицы и индекса...")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS flights (
                id SERIAL PRIMARY KEY,
                carrier VARCHAR(10) NOT NULL,
                flight_number VARCHAR(10) NOT NULL,
                origin VARCHAR(3) NOT NULL,
                destination VARCHAR(3) NOT NULL,
                departure_time TIMESTAMP NOT NULL,
                arrival_time TIMESTAMP NOT NULL,
                price NUMERIC(10, 2) NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_flights_departure_date
                ON flights (CAST(departure_time AS DATE));
        """))

    print("2. Генерация данных (120 дней по 1500 рейсов)...")
    random.seed(42)  # Фиксируем seed для детерминизма (п. 3.1.2)
    start_date = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    flights_data = []
    
    for day in range(120):
        current_date = start_date + datetime.timedelta(days=day)
        for _ in range(1500):
            origin = random.choice(AIRPORTS)
            destination = random.choice([a for a in AIRPORTS if a != origin])
            dur_h = random.randint(1, 6)
            dur_m = random.choice([0, 15, 30, 45])
            dep = current_date.replace(hour=random.randint(0, 23), minute=random.randint(0, 59))
            arr = dep + datetime.timedelta(hours=dur_h, minutes=dur_m)
            
            flights_data.append({
                "carrier": random.choice(CARRIERS),
                "flight_number": f"{random.randint(100, 9999)}",
                "origin": origin,
                "destination": destination,
                "departure_time": dep,
                "arrival_time": arr,
                "price": round(random.uniform(3000, 50000), 2),
            })

    total = len(flights_data)
    print(f"Сгенерировано {total} записей.")

    print("3. Загрузка данных в БД пачками...")
    batch_size = 5000
    with engine.begin() as conn:
        for i in range(0, total, batch_size):
            batch = flights_data[i:i + batch_size]
            conn.execute(insert(flights_table), batch)
            print(f"  Загружено: {i + len(batch)} / {total}")

    print(f"Все {total} записей успешно загружены!")

if __name__ == "__main__":
    init_db()