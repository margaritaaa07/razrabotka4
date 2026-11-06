from datetime import datetime

def build_routes(own_flights, provider_flights_list, origin, destination):
    all_flights = own_flights.copy()
    for p_flights in provider_flights_list:
        all_flights.extend(p_flights)

    # Приводим типы (в БД datetime, из JSON — строки)
    for f in all_flights:
        if isinstance(f["departure_time"], str):
            f["departure_time"] = datetime.fromisoformat(f["departure_time"])
            f["arrival_time"] = datetime.fromisoformat(f["arrival_time"])
        f["price"] = float(f["price"])

    routes = []
    by_origin = {}
    for f in all_flights:
        by_origin.setdefault(f["origin"], []).append(f)

    for f1 in all_flights:
        if f1["origin"] != origin:
            continue

        # Прямые
        if f1["destination"] == destination:
            routes.append({"segments": [f1], "price": f1["price"]})

        # 1 пересадка
        for f2 in by_origin.get(f1["destination"], []):
            if f2["origin"] == f1["origin"]:
                continue
            layover = (f2["departure_time"] - f1["arrival_time"]).total_seconds() / 3600
            if not (1 <= layover <= 6):
                continue
            if f2["destination"] == destination:
                routes.append({"segments": [f1, f2],
                               "price": f1["price"] + f2["price"]})

            # 2 пересадки
            for f3 in by_origin.get(f2["destination"], []):
                if f3["destination"] != destination:
                    continue
                if f3["destination"] in (f1["origin"], f2["origin"]):
                    continue
                layover2 = (f3["departure_time"] - f2["arrival_time"]).total_seconds() / 3600
                if 1 <= layover2 <= 6:
                    routes.append({
                        "segments": [f1, f2, f3],
                        "price": f1["price"] + f2["price"] + f3["price"],
                    })

    routes.sort(key=lambda x: x["price"])
    return routes[:20]