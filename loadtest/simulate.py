"""Load test: N participants take the full 2-stage exam at the same time.

Every participant: opens the entry page data, starts an attempt, answers every
question with a separate autosave request (like the real UI), reloads its state
once, finishes stage 1, starts and finishes stage 2.

Afterwards the script logs into the admin API and checks, for every attempt,
that each answer stored on the server equals the last answer the client sent
(no lost or mixed-up answers).

Usage:
    pip install httpx
    python loadtest/simulate.py --base http://localhost:8080 --users 150 \
        --admin-user admin --admin-password '...'
"""
import argparse
import asyncio
import random
import statistics
import string
import time
from collections import defaultdict

import httpx

LAT = defaultdict(list)
ERRORS = defaultdict(int)


async def call(client, name, method, url, **kw):
    t0 = time.perf_counter()
    try:
        r = await client.request(method, url, **kw)
    except httpx.HTTPError as exc:
        ERRORS[f"{name}: {type(exc).__name__}"] += 1
        raise
    LAT[name].append((time.perf_counter() - t0) * 1000)
    if r.status_code >= 400:
        ERRORS[f"{name}: HTTP {r.status_code}"] += 1
        r.raise_for_status()
    return r.json()


def rand_name():
    return random.choice(string.ascii_uppercase) + "".join(random.choices(string.ascii_lowercase, k=7))


async def participant(base, meta, idx, think, results):
    leaves = []
    for s in meta["subjects"]:
        leaves += s["children"] if s["children"] else [s]
    subject = random.choice([s for s in leaves if s["selectable"]])
    branch = random.choice(meta["branches"])
    async with httpx.AsyncClient(base_url=base, timeout=30) as c:
        await call(c, "GET meta", "GET", "/api/public/meta/")
        res = await call(c, "POST start", "POST", "/api/attempts/", json={
            "first_name": rand_name(), "last_name": rand_name(), "branch_id": branch["id"], "subject_id": subject["id"],
        })
        token, state = res["token"], res["state"]
        h = {"X-Attempt-Token": token}
        aid = state["id"]
        sent = {}
        for stage in (1, 2):
            if stage == 2:
                state = await call(c, "POST start stage", "POST", f"/api/attempts/{aid}/stages/2/start/", json={}, headers=h)
            questions = state["questions"]
            for i, q in enumerate(questions):
                if random.random() < 0.1:
                    continue  # leave some blank
                opt = random.choice(q["options"])["id"]
                await call(c, "PUT answer", "PUT", f"/api/attempts/{aid}/answers/", json={
                    "stage": stage, "answers": [{"id": q["id"], "option": opt}]}, headers=h)
                sent[q["id"]] = opt
                if random.random() < 0.15:  # change mind
                    opt = random.choice(q["options"])["id"]
                    await call(c, "PUT answer", "PUT", f"/api/attempts/{aid}/answers/", json={
                        "stage": stage, "answers": [{"id": q["id"], "option": opt}]}, headers=h)
                    sent[q["id"]] = opt
                if i == len(questions) // 2:
                    await call(c, "GET state (reload)", "GET", f"/api/attempts/{aid}/", headers=h)
                await asyncio.sleep(random.uniform(0, think))
            state = await call(c, "POST finish stage", "POST", f"/api/attempts/{aid}/stages/{stage}/finish/",
                               json={"answers": []}, headers=h)
        results[aid] = sent
        return state["status"]


async def verify(base, user, password, results):
    async with httpx.AsyncClient(base_url=base, timeout=60) as c:
        await c.get("/api/admin/auth/csrf/")
        csrf = c.cookies.get("csrftoken")
        r = await c.post("/api/admin/auth/login/", json={"username": user, "password": password},
                         headers={"X-CSRFToken": csrf})
        r.raise_for_status()
        mismatches = 0
        for aid, sent in results.items():
            d = (await c.get(f"/api/admin/attempts/{aid}/")).json()
            stored = {a["id"]: a["selected_option"] for a in d["answers"]}
            for qid, opt in sent.items():
                if stored.get(qid) != opt:
                    mismatches += 1
            if d["status"] != "completed":
                mismatches += 1
        return mismatches


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p))]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--users", type=int, default=150)
    ap.add_argument("--think", type=float, default=0.3, help="max pause between answers, seconds")
    ap.add_argument("--admin-user", default="admin")
    ap.add_argument("--admin-password", required=True)
    args = ap.parse_args()

    async with httpx.AsyncClient(base_url=args.base, timeout=30) as c:
        meta = (await c.get("/api/public/meta/")).json()

    results = {}
    t0 = time.perf_counter()
    outcomes = await asyncio.gather(
        *[participant(args.base, meta, i, args.think, results) for i in range(args.users)], return_exceptions=True)
    wall = time.perf_counter() - t0
    failed = [o for o in outcomes if isinstance(o, Exception)]
    total_requests = sum(len(v) for v in LAT.values())

    print(f"\nParticipants: {args.users} concurrent, finished: {args.users - len(failed)}, failed: {len(failed)}")
    print(f"Duration: {wall:.1f}s, requests: {total_requests}, throughput: {total_requests / wall:.0f} req/s\n")
    print(f"{'endpoint':22} {'count':>6} {'avg ms':>8} {'p50':>7} {'p95':>7} {'p99':>7} {'max':>7}")
    for name, v in LAT.items():
        print(f"{name:22} {len(v):6} {statistics.mean(v):8.1f} {pct(v, .5):7.1f} {pct(v, .95):7.1f} "
              f"{pct(v, .99):7.1f} {max(v):7.1f}")
    print("\nErrors:", dict(ERRORS) or "none")
    mismatches = await verify(args.base, args.admin_user, args.admin_password, results)
    answers = sum(len(s) for s in results.values())
    print(f"Integrity check: {answers} answers in {len(results)} attempts, mismatches: {mismatches}")


if __name__ == "__main__":
    asyncio.run(main())
