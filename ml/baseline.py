import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

df = pd.read_csv("data/SMSSpamCollection", sep="\t", names=["label", "text"])
df["y"] = (df["label"] == "spam").astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    df["text"], df["y"], test_size=0.2, stratify=df["y"], random_state=42
)

vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2)
model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(vec.fit_transform(X_train), y_train)

preds = model.predict(vec.transform(X_test))
print(classification_report(y_test, preds, target_names=["ham", "spam"]))

import os
os.makedirs("models", exist_ok=True)
joblib.dump((vec, model), "models/baseline.joblib")
print("Saved models/baseline.joblib")
