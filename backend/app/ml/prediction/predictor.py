"""Single-model inference execution.

`ModelPredictor` runs inference for exactly one already-loaded model
instance. Per ADR-007, it never loads, downloads, or unloads models
itself; it only consumes an instance already provided by the
`AIRuntimeManager`.
"""

import asyncio
import time
from typing import Any

import numpy as np

from app.core.logging import get_logger
from app.ml.prediction.confidence import ConfidenceCalculator
from app.ml.prediction.exceptions import PredictionExecutionError
from app.ml.prediction.prediction_result import IndividualPrediction
from app.ml.schemas import ModelManifestEntry

logger = get_logger(__name__)


class ModelPredictor:
    """Executes inference for a single loaded model and formats its result."""

    def __init__(self, confidence_calculator: ConfidenceCalculator | None = None) -> None:
        self._confidence_calculator = confidence_calculator or ConfidenceCalculator()

    async def predict(
        self,
        entry: ModelManifestEntry,
        model: Any,
        input_tensor: np.ndarray,
    ) -> IndividualPrediction:
        """Run inference for one model and return its formatted individual prediction.

        Raises:
            PredictionExecutionError: If TensorFlow inference fails for any reason.
        """
        started_at = time.perf_counter()

        try:
            output = await asyncio.to_thread(
                self._run_inference, entry, model, input_tensor
            )
        except Exception as exc:
            logger.error("Inference failed for model '%s'.", entry.id, exc_info=True)
            raise PredictionExecutionError(
                f"Model '{entry.id}' failed during inference."
            ) from exc

        inference_time_ms = round((time.perf_counter() - started_at) * 1000, 2)

        confidence = self._confidence_calculator.compute(
            probabilities=output,
            class_labels=entry.class_labels,
        )

        return IndividualPrediction(
            model_id=entry.id,
            model_name=entry.display_name,
            model_version=entry.version,
            predicted_label=confidence.top_class,
            predicted_class_index=confidence.top_class_index,
            confidence=confidence,
            probability_vector=confidence.raw_probabilities,
            inference_time_ms=inference_time_ms,
        )

    @staticmethod
    def _run_inference(
        entry: ModelManifestEntry, model: Any, input_tensor: np.ndarray
    ) -> np.ndarray:
        """Synchronously run the blocking forward pass, dispatching on `entry.format`.

        Executed inside `asyncio.to_thread` so a slow model never blocks
        the event loop or other concurrent predictions.
        """
        if entry.format == "tflite":
            return ModelPredictor._run_tflite_inference(model, input_tensor)
        predictions = model.predict(input_tensor, verbose=0)
        return np.asarray(predictions[0])

    @staticmethod
    def _run_tflite_inference(interpreter: Any, input_tensor: np.ndarray) -> np.ndarray:
        """Run a forward pass through an already-allocated TFLite Interpreter."""
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        tensor = input_tensor.astype(input_details[0]["dtype"], copy=False)

        if list(input_details[0]["shape"]) != list(tensor.shape):
            interpreter.resize_tensor_input(input_details[0]["index"], tensor.shape)
            interpreter.allocate_tensors()
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

        interpreter.set_tensor(input_details[0]["index"], tensor)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]["index"])
        return np.asarray(output[0])
