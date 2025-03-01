"""이미지 특징 추출 기능"""
import numpy as np
from PIL import Image
from tensorflow.keras.preprocessing import image

def extract_features(img_path, model):
    """이미지에서 특징 추출"""
    img = Image.open(img_path).resize((244, 244))
    img_array = image.img_to_array(img)
    expanded_img = np.expand_dims(img_array, axis=0)
    preprocessed_img = expanded_img / 255.0
    features = model.predict(preprocessed_img)
    return features.flatten()