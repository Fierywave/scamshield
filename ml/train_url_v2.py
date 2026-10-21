import re
import pandas as pd, joblib, scipy.sparse as sp
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from url_features import url_features

def clean(u):
    u = re.sub(r"^https?://", "", str(u).lower())
    return re.sub(r"^www\.", "", u)

df = pd.read_csv("data/malicious_phish.csv")
df = df[df["type"] != "defacement"]
df["y"] = (df["type"] != "benign").astype(int)
df = df.drop_duplicates(subset="url")
df = df.sample(n=min(100000, len(df)), random_state=42)

urls = df["url"].map(clean)
num = pd.DataFrame([url_features(u) for u in df["url"]])
y = df["y"].values

idx_tr, idx_te = train_test_split(range(len(df)), test_size=0.2, stratify=y, random_state=42)

vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=300000, sublinear_tf=True)
scaler = StandardScaler(with_mean=False)

X_tr = sp.hstack([vec.fit_transform(urls.iloc[idx_tr]), scaler.fit_transform(num.iloc[idx_tr])]).tocsr()
X_te = sp.hstack([vec.transform(urls.iloc[idx_te]), scaler.transform(num.iloc[idx_te])]).tocsr()

model = LogisticRegression(max_iter=2000, class_weight="balanced", C=5)
model.fit(X_tr, y[idx_tr])

print(classification_report(y[idx_te], model.predict(X_te), target_names=["benign", "bad"]))
joblib.dump((vec, scaler, model, list(num.columns)), "models/url_model_v2.joblib")
print("Saved models/url_model_v2.joblib")
