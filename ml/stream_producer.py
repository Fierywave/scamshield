import sys
import time
import redis
from txn_sim import simulate

rate = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
df = simulate(n_users=300, days=10, n_fraud=100, seed=7).sort_values("ts")
print(len(df), "transactions,", int(df.is_fraud.sum()), "fraud")

start = time.time()
for i, row in enumerate(df.itertuples(index=False)):
    delay = start + i / rate - time.time()
    if delay > 0:
        time.sleep(delay)
    r.xadd("transactions", {
        "user": int(row.user), "ts": float(row.ts), "payee": row.payee,
        "amount": float(row.amount), "is_fraud": int(row.is_fraud),
        "pattern": row.pattern, "sent_at": time.time(),
    })
print("Sent all")
