import argparse
import os

import mlflow
import mlflow.sklearn

from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# ============================================================
# Configuration
# ============================================================

MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "http://127.0.0.1:5000",
)

MLFLOW_EXPERIMENT_NAME = os.getenv(
    "MLFLOW_EXPERIMENT_NAME",
    "iris-classification",
)

REGISTERED_MODEL_NAME = os.getenv(
    "REGISTERED_MODEL_NAME",
    "iris-classifier",
)


# ============================================================
# Model creation
# ============================================================


def build_model(
    n_estimators: int = 100,
    max_depth: int = 5,
) -> Pipeline:
    """
    Create the machine learning pipeline.

    This function is separated from main() so that it can
    be imported and tested independently by pytest.
    """

    model = Pipeline(
        [
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    max_depth=max_depth,
                    random_state=42,
                ),
            )
        ]
    )

    return model


# ============================================================
# Command-line arguments
# ============================================================


def parse_args():
    parser = argparse.ArgumentParser(description="Train Iris classification model")

    parser.add_argument(
        "--n-estimators",
        type=int,
        default=100,
        help="Number of trees in the Random Forest",
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Maximum depth of each tree",
    )

    return parser.parse_args()


# ============================================================
# Training
# ============================================================


def main():
    args = parse_args()

    # --------------------------------------------------------
    # 1. Configure MLflow
    # --------------------------------------------------------

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    print(f"MLflow tracking URI: " f"{MLFLOW_TRACKING_URI}")

    print(f"MLflow experiment: " f"{MLFLOW_EXPERIMENT_NAME}")

    # --------------------------------------------------------
    # 2. Load dataset
    # --------------------------------------------------------

    iris = load_iris(as_frame=True)

    X = iris.data
    y = iris.target

    print(f"Dataset shape: {X.shape}")

    # --------------------------------------------------------
    # 3. Split dataset
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    print(f"Training samples: " f"{len(X_train)}")

    print(f"Testing samples: " f"{len(X_test)}")

    # --------------------------------------------------------
    # 4. Create model
    # --------------------------------------------------------

    model = build_model(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
    )

    # --------------------------------------------------------
    # 5. Start MLflow run
    # --------------------------------------------------------

    with mlflow.start_run() as run:

        print(f"MLflow Run ID: " f"{run.info.run_id}")

        # ----------------------------------------------------
        # 6. Train model
        # ----------------------------------------------------

        model.fit(
            X_train,
            y_train,
        )

        # ----------------------------------------------------
        # 7. Evaluate model
        # ----------------------------------------------------

        y_pred = model.predict(X_test)

        accuracy = accuracy_score(
            y_test,
            y_pred,
        )

        print(f"Accuracy: " f"{accuracy:.4f}")

        print()

        print(
            classification_report(
                y_test,
                y_pred,
                target_names=iris.target_names,
            )
        )

        # ----------------------------------------------------
        # 8. Log parameters
        # ----------------------------------------------------

        mlflow.log_param(
            "model_type",
            "RandomForestClassifier",
        )

        mlflow.log_param(
            "n_estimators",
            args.n_estimators,
        )

        mlflow.log_param(
            "max_depth",
            args.max_depth,
        )

        mlflow.log_param(
            "test_size",
            0.2,
        )

        mlflow.log_param(
            "random_state",
            42,
        )

        # ----------------------------------------------------
        # 9. Log metrics
        # ----------------------------------------------------

        mlflow.log_metric(
            "accuracy",
            accuracy,
        )

        # ----------------------------------------------------
        # 10. Log and register model
        # ----------------------------------------------------

        model_info = mlflow.sklearn.log_model(
            sk_model=model,
            name="model",
            input_example=X_train.head(5),
            registered_model_name=REGISTERED_MODEL_NAME,
        )

        print("Model logged to MLflow")

        print(f"Model URI: " f"{model_info.model_uri}")

        print(f"Registered model: " f"{REGISTERED_MODEL_NAME}")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()
