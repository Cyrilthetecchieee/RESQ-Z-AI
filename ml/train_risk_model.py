"""Train/evaluate the optional risk model on synthetic, deterministic data.

This is intentionally not required at runtime: the API uses the deterministic
rule model in ``app.services`` when a trained artifact is unavailable.
"""
import random

def build_dataset(n=200, seed=7):
    random.seed(seed)
    rows = []
    for _ in range(n):
        severity = random.randint(1, 5)
        keywords = random.choice([0, 1])
        score = severity * 16 + keywords * 25
        rows.append(([severity, keywords], int(score >= 60)))
    return [x for x, _ in rows], [y for _, y in rows]

def main():
    X, y = build_dataset()
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score
        from sklearn.ensemble import RandomForestClassifier
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.25, random_state=7, stratify=y)
        model = RandomForestClassifier(n_estimators=25, random_state=7).fit(X_train, y_train)
        print({"backend": "scikit-learn", "accuracy": round(accuracy_score(y_test, model.predict(X_test)), 3)})
    except ImportError:
        # Exact deterministic fallback: the same threshold used to label data.
        correct = sum(int((x[0] * 16 + x[1] * 25) >= 60) == label for x, label in zip(X, y))
        print({"backend": "deterministic-fallback", "accuracy": correct / len(y)})

if __name__ == "__main__":
    main()
