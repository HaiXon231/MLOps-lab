import mlflow
import mlflow.sklearn
import pandas as pd

mlflow.set_tracking_uri("http://127.0.0.1:5000")

MODEL_URI = "models:/iris-classifier@champion"

model = mlflow.sklearn.load_model(MODEL_URI)

sample = pd.DataFrame(
    [[5.1, 3.5, 1.4, 0.2]],
    columns=[
        "sepal length (cm)",
        "sepal width (cm)",
        "petal length (cm)",
        "petal width (cm)",
    ],
)

prediction = model.predict(sample)

print("Prediction:", prediction)
