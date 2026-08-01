"""Model-driven image preprocessing.

Preprocessing parameters (currently the input size) always originate from
the Model Manifest via `ModelManifestEntry.input_size`, never from a
hardcoded constant, so preprocessing remains correct even as new models
with different input requirements are added.
"""

import numpy as np
from PIL import Image

_RGB_MODE = "RGB"


class ImagePreprocessor:
    """Converts a validated PIL image into a model-ready input tensor."""

    def preprocess(self, image: Image.Image, input_size: int) -> np.ndarray:
        """Prepare a single batched, normalized input tensor for a model.

        Args:
            image: A validated, decodable PIL image.
            input_size: The model's required square input dimension,
                sourced from the Model Manifest.

        Returns:
            A float32 array of shape `(1, input_size, input_size, 3)`, with
            raw pixel values in the `[0, 255]` range -- matching what every
            current production model was trained on (see
            `app.ml.preprocessing.transforms.normalize_pixels`).
        """
        rgb_image = image.convert(_RGB_MODE)
        resized_image = rgb_image.resize((input_size, input_size), Image.Resampling.LANCZOS)

        array = np.asarray(resized_image, dtype=np.float32)
        return np.expand_dims(array, axis=0)
