import pandas as pd
import joblib
from sklearn.metrics import classification_report

vec, model = joblib.load("models/baseline.joblib")
df = pd.read_csv("data_india/india_messages.csv")
y = (df["label"] == "spam").astype(int)

preds = model.predict(vec.transform(df["text"]))
print(classification_report(y, preds, target_names=["ham", "spam"]))
