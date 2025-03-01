"""추천 알고리즘 관련 기능"""
import numpy as np
from sklearn.neighbors import NearestNeighbors

def find_similar_products(feature_list, query_features, n_recommendations=5):
    """유사한 제품 찾기"""
    neighbors = NearestNeighbors(n_neighbors=n_recommendations, algorithm='brute', metric='euclidean')
    neighbors.fit(feature_list)
    
    distances, indices = neighbors.kneighbors([query_features])
    return indices[0], distances[0]