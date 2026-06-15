"""
Concurrency load test: simulates many simultaneous users hitting the API.

Usage:
    python load_test.py [BASE_URL] [N_USERS] [REQUESTS_PER_USER]
Example:
    python load_test.py http://localhost:8077 200 5
"""
import asyncio
import random
import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8077"
N_USERS = int(sys.argv[2]) if len(sys.argv) > 2 else 200
REQS = int(sys.argv[3]) if len(sys.argv) > 3 else 5

QUESTIONS = [
    "How does Imabari connect to Japan's emissions goal?",
    "What are the offshore wind targets?",
    "How is hydrogen related to zero emission ships?",
    "How does shipbuilding converge with green technology?",
    "What is the 7th Basic Energy Plan?",
    "What are Japan's hydrogen targets?",
    "Tell me about ammonia co-firing",
    "What is the JMU acquisition?",
]

latencies = []
errors = 0


async def user_session(client: httpx.AsyncClient, uid: int):
    global errors
    for _ in range(REQS):
        action = random.random()
        t0 = time.perf_counter()
        try:
            if action < 0.7:  # 70% ask
                q = random.choice(QUESTIONS)
                r = await client.post("/api/ask", json={"question": q}, timeout=30)
            elif action < 0.9:  # 20% graph
                r = await client.get("/api/graph", timeout=30)
            else:  # 10% stats
                r = await client.get("/api/stats", timeout=30)
            r.raise_for_status()
            latencies.append((time.perf_counter() - t0) * 1000)
        except Exception:
            errors += 1
        await asyncio.sleep(random.uniform(0, 0.05))


async def main():
    print(f"Load test -> {BASE}")
    print(f"Simulating {N_USERS} concurrent users x {REQS} requests = {N_USERS * REQS} total\n")
    limits = httpx.Limits(max_connections=N_USERS + 50, max_keepalive_connections=N_USERS)
    t0 = time.perf_counter()
    async with httpx.AsyncClient(base_url=BASE, limits=limits) as client:
        await asyncio.gather(*[user_session(client, i) for i in range(N_USERS)])
    total = time.perf_counter() - t0

    n = len(latencies)
    latencies.sort()
    def pct(p):
        return latencies[min(n - 1, int(n * p / 100))] if n else 0
    done = n + errors
    print("===== RESULTS =====")
    print(f"Completed requests : {n}/{done}")
    print(f"Errors             : {errors}")
    print(f"Wall time          : {total:.2f}s")
    print(f"Throughput         : {done / total:.0f} req/s")
    if n:
        print(f"Latency  avg       : {sum(latencies)/n:.1f} ms")
        print(f"Latency  p50       : {pct(50):.1f} ms")
        print(f"Latency  p95       : {pct(95):.1f} ms")
        print(f"Latency  p99       : {pct(99):.1f} ms")
        print(f"Latency  max       : {latencies[-1]:.1f} ms")


if __name__ == "__main__":
    asyncio.run(main())
