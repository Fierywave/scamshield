import pandas as pd, joblib

vec, model = joblib.load("models/combined.joblib")
test = pd.read_csv("data_india/india_test.csv")
test["y"] = (test["label"] == "spam").astype(int)
test["pred"] = model.predict(vec.transform(test["text"]))
pd.set_option("display.max_colwidth", 120)
print(test[test["pred"] != test["y"]][["label", "text"]].to_string())
