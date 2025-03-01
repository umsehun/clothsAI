# modules/model_utils.py
import os
import pickle
import numpy as np
import streamlit as st
import tensorflow
from tensorflow.keras.preprocessing import image
from tensorflow.keras.layers import GlobalMaxPooling2D
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from numpy.linalg import norm
from fashion_db import FashionDB

db = FashionDB()
feature_list = None
filenames = None
model = None

def load_model_and_features():
    """모델과 feature_list, filenames 로드 함수 수정"""
    try:
        # feature_list 로드
        if os.path.exists('features_list_for_prods.pkl'):
            with open('features_list_for_prods.pkl', 'rb') as f:
                feature_list = np.array(pickle.load(f))
        else:
            feature_list = np.array([])
            
        # filenames 로드
        if os.path.exists('filenames_products.pkl'):
            with open('filenames_products.pkl', 'rb') as f:
                filenames = pickle.load(f)
        else:
            filenames = []
            
        # 모델 로드
        base_model = ResNet50(weights='imagenet', include_top=False, input_shape=(244, 244, 3))
        base_model.trainable = False
        model = tensorflow.keras.Sequential([
            base_model,
            GlobalMaxPooling2D()
        ])
        print("모델 로드 완료!")
        
        return model, feature_list, filenames
        
    except Exception as e:
        print(f"모델 로드 오류: {e}")
        return None, np.array([]), []

def feature_extraction(img_path, model):
    """이미지에서 특징 추출 (model을 인자로 받도록 수정)"""
    if model is None:
        return None
        
    try:
        img = image.load_img(img_path, target_size=(244, 244))
        img_array = image.img_to_array(img)
        expanded_img_array = np.expand_dims(img_array, axis=0)
        preprocessed_img = preprocess_input(expanded_img_array)
        result = model.predict(preprocessed_img).flatten()
        normalized_result = result / norm(result)
        return normalized_result
    except Exception as e:
        print(f"특징 추출 오류: {e}")
        return None

def add_user_data_to_training(user_image_path: str, user_tags: list) -> bool:
    """사용자가 업로드한 이미지와 태그를 학습 데이터에 추가"""
    global model, feature_list, filenames
    if model is None:
        st.warning("모델이 로드되지 않아 학습 데이터에 추가할 수 없습니다.")
        return False
    features = feature_extraction(user_image_path, model)
    if features is None:
        return False
    try:
        if len(feature_list) > 0:
            new_feature_list = np.vstack([feature_list, features.reshape(1, -1)])
            filenames.append(user_image_path)
        else:
            new_feature_list = features.reshape(1, -1)
            filenames = [user_image_path]
        with open('features_list_for_prods.pkl', 'wb') as f:
            pickle.dump(new_feature_list, f)
        with open('filenames_products.pkl', 'wb') as f:
            pickle.dump(filenames, f)
        feature_list = new_feature_list
        db.save_tags(user_image_path, user_tags)
        return True
    except Exception as e:
        st.error(f"학습 데이터 추가 중 오류: {e}")
        return False
