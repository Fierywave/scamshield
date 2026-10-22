import joblib
from txn_sim import simulate, add_features

model = joblib.load("models/txn_model.joblib")
df = simulate(n_users=300, days=10, n_fraud=100, seed=7)
df, X = add_features(df)
y = df.is_fraud.values
rn = df.groupby("user").cumcount().values + 1
ml = (model.predict_proba(X)[:, 1] >= 0.5)
warm = rn > 5


def stats(flag):
    tp = int((flag & (y == 1)).sum())
    fp = int((flag & (y == 0)).sum())
    fn = int((~flag & (y == 1)).sum())
    return tp, fp, fn, tp / max(tp + fp, 1), tp / max(tp + fn, 1)


for thr in [5, 6, 8, 10]:
    rule = ((X.is_new_payee == 1) & (X.amount_ratio > thr)).values | (X.txn_count_10m >= 4).values
    flag = ml | rule
    tp, fp, fn, p, r = stats(flag)
    htp, hfp, hfn, hp, hr = stats(flag & warm)
    low = flag & ~warm
    print(f"\nRule threshold {thr}x")
    print(f"  all flags:            precision {p:.2f}  recall {r:.2f}  false positives {fp}")
    print(f"  high priority queue:  precision {hp:.2f}  false positives {hfp}")
    print(f"  limited-history queue: {int(low.sum())} flags, {int((low & (y == 1)).sum())} real fraud")
