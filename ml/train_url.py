import pandas as pd, joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from xgboost import XGBClassifier
from url_features import url_features

df = pd.read_csv("data/malicious_phish.csv")
df = df[df["type"] != "defacement"]
df["y"] = (df["type"] != "benign").astype(int)
df = df.drop_duplicates(subset="url")
df = df.sample(n=min(100000, len(df)), random_state=42)

X = pd.DataFrame([url_features(u) for u in df["url"]])
y = df["y"].values
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

model = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, eval_metric="logloss")
model.fit(X_tr, y_tr)
print(classification_report(y_te, model.predict(X_te), target_names=["benign", "bad"]))

joblib.dump((model, list(X.columns)), "models/url_model.joblib")
print("Saved models/url_model.joblib")
