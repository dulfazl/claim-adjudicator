"""A check on the image itself, made before the model is asked to read it.

The model reads a blurred photo with the same confidence as a sharp one and fills the gaps
with plausible guesses, and when asked it calls every image clear. So readability is not
something to ask the model about. It is measured directly from the pixels instead.
"""

import io

import numpy as np
from PIL import Image

STANDARD_WIDTH = 1000  # every image is resized to this width first, so photos of different sizes are comparable
MIN_SHARPNESS = 150.0


def sharpness(image_bytes: bytes) -> float:
    """Variance of the Laplacian: high when the image has crisp edges such as readable text, low when it is blurred."""
    image = Image.open(io.BytesIO(image_bytes)).convert("L")
    height = round(image.height * STANDARD_WIDTH / image.width)
    gray = np.asarray(image.resize((STANDARD_WIDTH, height)), dtype=float)
    # Each pixel compared with its four neighbours; large differences mean a sharp edge.
    laplacian = gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:] - 4 * gray[1:-1, 1:-1]
    return float(laplacian.var())


def is_readable(image_bytes: bytes) -> bool:
    return sharpness(image_bytes) >= MIN_SHARPNESS
