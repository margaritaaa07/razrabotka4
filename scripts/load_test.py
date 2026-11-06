import asyncio, httpx, time, argparse, random, statistics


async def health_checker(client, stop_event, health_latencies):
    while not stop_event.is_set():
        start = time.time()
        try:
            await client.get("/health", timeout=1.0)
            health_latencies.append((time.time() - start) * 1000)
        except Exception:
            pass
        await asyncio.sleep(0.1)


async def run_closed_mode(client, clients_count, duration, results, errors, search_date):
    stop_time = time.time() + duration

    async def worker():
        while time.time() < stop_time:
            start = time.time()
            try:
                resp = await client.get("/search", params={
                    "origin": "SVO", "destination": "LED", "date": search_date,
                }, timeout=30.0)
                if resp.status_code == 200:
                    results.append((time.time() - start) * 1000)
                else:
                    errors.append(1)
            except Exception:
                errors.append(1)

    await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(clients_count)])


async def run_open_mode(client, rps, duration, results, errors, search_date):
    stop_time = time.time() + duration
    tasks = set()

    async def send_request():
        start = time.time()
        try:
            resp = await client.get("/search", params={
                "origin": "SVO", "destination": "LED", "date": search_date,
            }, timeout=30.0)
            if resp.status_code == 200:
                results.append((time.time() - start) * 1000)
            else:
                errors.append(1)
        except Exception:
            errors.append(1)

    while time.time() < stop_time:
        await asyncio.sleep(random.expovariate(rps))
        if time.time() < stop_time:
            task = asyncio.create_task(send_request())
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    if tasks:
        await asyncio.gather(*tasks)


def print_stats(name, data, total_errors, duration):
    if not data:
        print(f"\n--- {name} ---\nНет данных")
        return
    data.sort()
    count = len(data)
    rps = count / duration
    p50 = statistics.median(data)
    idx_95 = min(int(count * 0.95), count - 1)
    idx_99 = min(int(count * 0.99), count - 1)
    p95 = data[idx_95]
    p99 = data[idx_99]
    p_max = max(data)
    err_pct = (total_errors / (count + total_errors)) * 100 if (count + total_errors) > 0 else 0

    print(f"\n--- {name} ---")
    print(f"Запросов в секунду: {rps:.2f} | Всего запросов: {count}")
    print(f"p50: {p50:.1f}ms | p95: {p95:.1f}ms | p99: {p99:.1f}ms | Max: {p_max:.1f}ms")
    print(f"Ошибки: {err_pct:.2f}% ({total_errors} шт.)")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["closed", "open"], required=True)
    parser.add_argument("--c", type=int, default=1)
    parser.add_argument("--rps", type=float, default=5.0)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--url", type=str, default="http://localhost:8000")
    parser.add_argument("--date", type=str, default="2026-11-06")
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.url) as client:
        print(f"Прогрев 10с... (Дата поиска: {args.date})")
        await run_closed_mode(client, 1, 10, [], [], args.date)

        results, errors, health_latencies = [], [], []
        stop_event = asyncio.Event()
        hc_task = asyncio.create_task(health_checker(client, stop_event, health_latencies))

        if args.mode == "closed":
            await run_closed_mode(client, args.c, args.duration, results, errors, args.date)
        else:
            await run_open_mode(client, args.rps, args.duration, results, errors, args.date)

        stop_event.set()
        await hc_task

    print_stats("Search", results, len(errors), args.duration)
    print_stats("Health", health_latencies, 0, args.duration)


if __name__ == "__main__":
    asyncio.run(main())