"""
Loads the fine-tuned EfficientNetB0 classifier.
Place your trained model file at: backend/models/pothole_classifier.h5
"""

import os
import numpy as np
from PIL import Image

MODEL_PATH = os.path.join(os.path.dirname(__file__), "pothole_classifier.h5")
CATEGORIES = ["dead_animals", "garbage", "illegal_dumping", "pothole", "sewer", "streetlight", "waterlogging"]

# Map model's 7 classes down to the 3 civic categories
CATEGORY_MAP = {
    "dead_animals": "garbage",
    "garbage": "garbage",
    "illegal_dumping": "garbage",
    "pothole": "pothole",
    "sewer": "waterlogging",
    "streetlight": "garbage",  # streetlight damage → report as garbage/misc
    "waterlogging": "waterlogging",
}

_model = None


MODEL_AVAILABLE = os.path.exists(MODEL_PATH)


def load_model():
    global _model
    if _model is None:
        import tf_keras as keras
        _model = keras.models.load_model(MODEL_PATH)
    return _model


def preprocess_image(image_bytes):
    """
    Converts raw uploaded image bytes into the array shape EfficientNetB0 expects.
    IMPORTANT: do NOT divide by 255 here - EfficientNetB0's internal rescaling
    layer handles that. Passing raw [0,255] pixel values is correct.
    """
    from io import BytesIO
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = image.resize((224, 224))
    array = np.array(image, dtype=np.float32)
    return np.expand_dims(array, axis=0)


def predict(image_bytes):
    if not MODEL_AVAILABLE:
        # TEMPORARY: model still training. Returns a fixed placeholder so the
        # rest of the pipeline (upload, geocode, duplicate check, priority,
        # DB save, dashboard display) can be built and tested end-to-end
        # without waiting on the trained model file.
        print("[classifier] WARNING: pothole_classifier.h5 not found - using placeholder prediction")
        return "pothole", 0.75

    model = load_model()
    processed = preprocess_image(image_bytes)
    prediction = model.predict(processed, verbose=0)
    category_index = int(np.argmax(prediction[0]))
    raw_category = CATEGORIES[category_index]
    confidence = float(np.max(prediction[0]))
    return CATEGORY_MAP[raw_category], confidence
