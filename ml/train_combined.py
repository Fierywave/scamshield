import pandas as pd, numpy as np, joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

uci = pd.read_csv("data/SMSSpamCollection", sep="\t", names=["label", "text"])
ind = pd.read_csv("data_india/india_train.csv")
test = pd.read_csv("data_india/india_test.csv")

train = pd.concat([uci, ind], ignore_index=True)
y = (train["label"] == "spam").astype(int)
weights = np.concatenate([np.ones(len(uci)), np.full(len(ind), 5.0)])

vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(vec.fit_transform(train["text"]), y, sample_weight=weights)

yt = (test["label"] == "spam").astype(int)
print(classification_report(yt, model.predict(vec.transform(test["text"])), target_names=["ham", "spam"]))

joblib.dump((vec, model), "models/combined.joblib")
