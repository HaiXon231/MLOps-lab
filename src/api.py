import mlflow
import mlflow.sklearn
import pandas as pd
import os

from fastapi import FastAPI
from pydantic import BaseModel

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "http://127.0.0.1:5000",
)

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

MODEL_URI = os.getenv(
    "MODEL_URI",
    "models:/iris-classifier@champion",
)

model = mlflow.sklearn.load_model(MODEL_URI)


app = FastAPI(
    title="Iris ML API",
    version="1.1.0",
)

TARGET_NAMES = [
    "setosa",
    "versicolor",
    "virginica",
]


class IrisInput(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": MODEL_URI,
    }


@app.post("/predict")
def predict(data: IrisInput):

    sample = pd.DataFrame(
        [
            [
                data.sepal_length,
                data.sepal_width,
                data.petal_length,
                data.petal_width,
            ]
        ],
        columns=[
            "sepal length (cm)",
            "sepal width (cm)",
            "petal length (cm)",
            "petal width (cm)",
        ],
    )

    prediction = int(model.predict(sample)[0])

    probabilities = model.predict_proba(sample)[0]

    return {
        "class_id": prediction,
        "class_name": TARGET_NAMES[prediction],
        "probabilities": {
            name: float(prob)
            for name, prob in zip(
                TARGET_NAMES,
                probabilities,
            )
        },
    }
