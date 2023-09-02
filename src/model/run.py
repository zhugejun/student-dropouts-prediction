import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import optuna
import xgboost as xgb
import pandas as pd
import numpy as np

from xgboost import plot_importance
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import (
    accuracy_score, 
    precision_score, 
    recall_score, 
    RocCurveDisplay,
    confusion_matrix,
    ConfusionMatrixDisplay,
    roc_auc_score
)

import matplotlib.pyplot as plt
from pathlib import Path

from config import PREV_TERM, CURR_TERM

import logging


logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler('model.log', 'w'))


# TODO: get max week number automatically
csv_files = sorted(list(Path("../../data/processed").glob("*.csv")))
df = pd.read_csv(csv_files[-1])


encoder = OneHotEncoder(sparse=False, drop="first", dtype=int)

# change some columns to category 
for col in ["Ethnicity", "Gender", "IsHispanic"]:
    df[col] = df[col].astype("category")

columns_to_encode = ["Ethnicity", "Gender", "IsHispanic"]
    
# one-hot encoding for ethnicity, gender, ishispanice
encoded_data = encoder.fit_transform(df[columns_to_encode])
encoded_df = pd.DataFrame(encoded_data, columns=encoder.get_feature_names_out(columns_to_encode))

df = pd.concat([df, encoded_df], axis=1)
df.drop(columns_to_encode, axis=1, inplace=True)

# features
features = [col for col in df.columns if col not in ["StudentID", "TermCode", "Target"]]


df = df[df["TermCode"] <= CURR_TERM]

X_train = df.loc[df["TermCode"] < PREV_TERM, features].copy()
y_train = df.loc[df["TermCode"] < PREV_TERM, "Target"].copy()

X_valid = df.loc[df["TermCode"] == PREV_TERM, features].copy()
y_valid = df.loc[df["TermCode"] == PREV_TERM, "Target"].copy()

print(f"Train on  {X_train.shape[0]} rows")
print(f"Validation on {X_valid.shape[0]} rows")
print('-' * 60)

print(f"Number of students dropped:          {sum(y_train == 1)}")
print(f"Total number of students in history: {len(y_train)}")
print("=============== Baseline without model (all students not dropping out) ==============")
print(f"Accuracy:  {1 - sum(y_train) / len(y_train)}")
# print(f"Pricision: {3}") # tp / (tp + fp)
# print(f"Recall:     {4}")


# TODO: calculate precision and recall for reference
neg, pos = np.bincount(y_train)
scale_pos_weight = neg / pos
# print(scale_pos_weight)

print("=========== Base model training WITHOUT parameter fine tuning... =================")
clf = xgb.XGBClassifier(tree_method="hist", enable_categorical=True)
clf.fit(X_train, y_train)


y_pred = clf.predict(X_valid)

cm = confusion_matrix(y_valid, y_pred, labels=clf.classes_)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=clf.classes_)

disp = ConfusionMatrixDisplay.from_estimator(clf, X_valid, y_valid, normalize='true', cmap=plt.cm.Blues)
disp.figure_.savefig("confusion_matrix_without_tuning.png")

print(f"Accuracy: {accuracy_score(y_valid, y_pred)}")
print(f"Precisoin: {precision_score(y_valid, y_pred)}")
print(f"Recall: {recall_score(y_valid, y_pred)}")
y_prob = clf.predict_proba(X_valid)
print(f"ROC AUC score: {roc_auc_score(y_valid, y_prob[:, 1])}")


print("=========== Base model training WITH parameter fine tuning... =================")

# fine tune parameters with optuna
def objective(trial):
    param = {
        "tree_method": "exact",
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 1e-1),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "subsample": trial.suggest_float("subsample", 0.5, 1),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1),
        "gamma": trial.suggest_float("gamma", 0, 10),
        "scale_pos_weight": scale_pos_weight,
        "n_estimators": 1000,
    }
    clf = xgb.XGBClassifier(**param)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_valid)
    score = roc_auc_score(y_valid, y_pred)
    return score


study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=50)
print(study.best_params)
print(study.best_value)
print(study.best_trial)


# train with best params
clf = xgb.XGBClassifier(**study.best_params)
clf.fit(X_train, y_train)


print("=========== Make predictions on test data =================")
df_test = df[df["TermCode"] == CURR_TERM].copy()

X_test = df.loc[df["TermCode"] == CURR_TERM, features].copy()
y_test = df.loc[df["TermCode"] == CURR_TERM, "Target"].copy()

y_pred = clf.predict(X_test)
y_prob = clf.predict_proba(X_test)

print(f"Accuracy: {accuracy_score(y_test, y_pred)}")
print(f"Precisoin: {precision_score(y_test, y_pred)}")
print(f"Recall: {recall_score(y_test, y_pred)}")
print(f"ROC AUC score: {roc_auc_score(y_test, y_prob[:, 1])}")


df_test["prediction"] = y_pred
df_test.to_csv(f"predictions-fall2023-current-week.csv", index=False)