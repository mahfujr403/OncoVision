"""Prediction Response Builder package (Phase 4.8.1, ADR-028).

Introduces the Response Builder architecture described by ADR-028:
`PredictionResponseBuilder` (`app.ml.response.response_builder`) and its
standardized output, `PredictionResponseResult`
(`app.ml.response.response_result`).

This package consumes only `FinalPredictionResult`
(`app.ml.ensemble.final_prediction_result`, ADR-027) -- the Final
Prediction Builder's output -- and never performs prediction logic of
its own. It never communicates with `AIRuntimeManager`,
`PredictionEngine`, `PredictionService`, or TensorFlow models.
"""
