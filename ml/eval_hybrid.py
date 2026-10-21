import joblib
from sklearn.metrics import precision_score, recall_score
from txn_sim import simulate, add_features

df = simulate()
df, X = add_features(df)
model = joblib.load("models/txn_model.joblib")

is_test = df["user"].isin(range(800, 1000)).values
X_te, d_te = X[is_test], df[is_test]
y_te = d_te.is_fraud.values

ml = model.predict(X_te)
rules = (((X_te.is_new_payee == 1) & (X_te.amount_ratio > 5)) |
         (X_te.txn_count_10m >= 4)).astype(int).values
hybrid = ((ml == 1) | (rules == 1)).astype(int)


def report(name, pred):
    p = precision_score(y_te, pred, zero_division=0)
    r = recall_score(y_te, pred)
    fpr = ((pred == 1) & (y_te == 0)).sum() / (y_te == 0).sum()
    print(f"\n{name}: precision {p:.2f}  recall {r:.2f}  false-positive rate {fpr:.4f}")
    for pat in ["takeover", "test_then_drain", "scam_pay"]:
        m = d_te.pattern.values == pat
        print(f"   recall on {pat}: {pred[m].mean():.2f}")


report("Rules", rules)
report("XGBoost", ml)
report("Hybrid (rules OR model)", hybrid)
