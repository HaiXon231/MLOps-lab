import joblib
import pandas as pd


artifact = joblib.load("artifacts/iris_model.joblib")

model = artifact["model"]
feature_names = artifact["feature_names"]
target_names = artifact["target_names"]


sample = pd.DataFrame(
    [[5.1, 3.5, 1.4, 0.2]],
    columns=feature_names,
)

prediction = model.predict(sample)[0]

probabilities = model.predict_proba(sample)[0]


print("Prediction:", target_names[prediction])

print("Probabilities:")

for class_name, probability in zip(
    target_names,
    probabilities,
):
    print(f"  {class_name}: {probability:.4f}")