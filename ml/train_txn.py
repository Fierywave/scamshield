import joblib
from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score
from txn_sim import simulate, add_features

df = simulate()
df, X = add_features(df)
print(len(df), "transactions,", int(df.is_fraud.sum()), "fraud")

is_test = df["user"].isin(range(800, 1000)).values
unseen = (df["pattern"] == "scam_pay").values
train_mask = (~is_test) & (~unseen)

model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.1,
                      scale_pos_weight=20, eval_metric="logloss")
model.fit(X[train_mask], df.is_fraud[train_mask])

X_te, d_te = X[is_test], df[is_test]
y_te = d_te.is_fraud.values

ml_pred = model.predict(X_te)
rule_pred = (((X_te.is_new_payee == 1) & (X_te.amount_ratio > 5)) |
             (X_te.txn_count_10m >= 4)).astype(int).values


def report(name, pred):
    p = precision_score(y_te, pred, zero_division=0)
    r = recall_score(y_te, pred)
    fpr = ((pred == 1) & (y_te == 0)).sum() / (y_te == 0).sum()
    print(f"\n{name}: precision {p:.2f}  recall {r:.2f}  false-positive rate {fpr:.4f}")
    for pat in ["takeover", "test_then_drain", "scam_pay"]:
        m = d_te.pattern.values == pat
        print(f"   recall on {pat}: {pred[m].mean():.2f} ({m.sum()} txns)")


report("Rules baseline", rule_pred)
report("XGBoost model", ml_pred)

joblib.dump(model, "models/txn_model.joblib")
print("\nSaved models/txn_model.joblib")
