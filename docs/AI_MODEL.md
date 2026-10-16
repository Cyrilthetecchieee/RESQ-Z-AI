# AI model and limitations

`ml/train_risk_model.py` builds a deterministic synthetic dataset from severity
and hazard-keyword features, holds out 25% for evaluation, and trains a
scikit-learn `RandomForestClassifier`. It prints an accuracy result from the
actual train/test split. The current script does not persist a model artifact;
runtime inference therefore uses the deterministic rule service rather than a
serialized estimator.

## Verified local evaluation

Using the default seed (`200` rows, `150/50` train/test split,
`random_state=7`, `25` trees), the measured holdout results were:

* Confusion matrix: `[[26, 0], [0, 24]]`
* Precision: `1.000`
* Recall: `1.000`
* F1: `1.000`

This perfect score is expected because the labels are generated directly from
the same threshold rule represented by the two features. It is evidence that
the pipeline executes deterministically, not evidence of real-world predictive
power. A future production-like iteration must use independently collected,
governed data and a persisted, versioned model artifact with drift monitoring.

Runtime scoring in `app/services.py` is intentionally transparent: severity
contributes to a 0-100 score and terms such as `fire`, `trapped`, and
`multiple` add a hazard signal. The score maps to low, medium, high, or
critical. This deterministic path is also the fallback when optional ML
dependencies are unavailable.

The dataset is synthetic and small, so it cannot establish clinical validity,
real-world calibration, fairness, or operational safety. Outputs are
decision-support signals only and require trained human review.
