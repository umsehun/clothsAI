# modules/tag_utils.py
import os
import re
import json
import random
import pickle
import streamlit as st
from modules.constants import COLOR_MAP
from fashion_db import FashionDB
from sklearn.metrics.pairwise import cosine_similarity

db = FashionDB()

def save_tags(image_path: str, tags: list) -> str:
    """태그를 파일과 DB에 저장 (DB 사용 버전)"""
    if not os.path.exists('saved_tags'):
        os.makedirs('saved_tags')
    filename = os.path.basename(image_path)
    base_name = os.path.splitext(filename)[0]
    json_path = f'saved_tags/{base_name}_tags.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'image': filename, 'tags': tags}, f, ensure_ascii=False)
    tag_id = db.save_tags(image_path, tags)
    return json_path

def detect_pattern(image_path: str) -> str:
    """이미지에서 패턴 감지 (예시)"""
    patterns = ["단색", "스트라이프", "체크", "도트", "플로럴", "기하학적", "그래픽", "카무플라주"]
    return random.choice(patterns)

def recommend_season(color_name: str, clothing_type: str) -> str:
    """색상과 의류 종류를 기반으로 계절 추천"""
    summer_colors = ["빨강", "주황", "노랑", "하얀"]
    winter_colors = ["검정", "남색", "회색"]
    if color_name in summer_colors:
        return "여름"
    elif color_name in winter_colors:
        return "겨울"
    else:
        return "가을" if clothing_type in ["아우터", "하의"] else "봄"

def extract_musinsa_tags(product_data: dict) -> list:
    """무신사 데이터에서 태그 추출"""
    tags = []
    if 'brandName' in product_data and product_data['brandName']:
        tags.append(product_data['brandName'])
    color_matched = False
    if 'productName' in product_data and product_data['productName']:
        product_name = product_data['productName'].lower()
        for color_name in COLOR_MAP.keys():
            color_keywords = [color_name]
            if color_name == '빨강': color_keywords.extend(['레드', 'red'])
            elif color_name == '파랑': color_keywords.extend(['블루', 'blue'])
            elif color_name == '초록': color_keywords.extend(['그린', 'green'])
            elif color_name == '노랑': color_keywords.extend(['옐로우', 'yellow'])
            elif color_name == '검정': color_keywords.extend(['블랙', 'black'])
            elif color_name == '흰색': color_keywords.extend(['화이트', 'white'])
            for keyword in color_keywords:
                if keyword.lower() in product_name:
                    tags.append(color_name)
                    color_matched = True
                    break
            if color_matched:
                break
    categories = {
        '상의': ['티셔츠', '니트', '셔츠', '맨투맨', '후드', '블라우스', '탑'],
        '하의': ['팬츠', '진', '청바지', '슬랙스', '스커트', '쇼츠', '레깅스', 'pants'],
        '아우터': ['자켓', '코트', '패딩', '집업', '점퍼', '가디건', '베스트', 'jacket'],
        '원피스': ['원피스', '드레스', 'dress'],
        '신발': ['스니커즈', '구두', '로퍼', '슬리퍼', '샌들', '힐', '부츠', 'shoes'],
        '액세서리': ['모자', '가방', '벨트', '양말', '주얼리', '팔찌', '목걸이', 'cap', 'bag']
    }
    if 'productName' in product_data and product_data['productName']:
        product_name = product_data['productName'].lower()
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword.lower() in product_name:
                    tags.append(category)
                    tags.append(keyword)
                    break
    style_keywords = {
        '미니멀룩': ['미니멀', '심플', '베이직'],
        '스트릿패션': ['스트릿', '캐주얼', '힙합', '어반'],
        '럭셔리룩': ['럭셔리', '포멀', '엘레강스'],
        '빈티지룩': ['빈티지', '레트로', '올드스쿨'],
        '스포티룩': ['스포티', '애슬레저', '액티브'],
        '모던룩': ['모던', '컨템포러리']
    }
    if 'productName' in product_data and product_data['productName']:
        product_name = product_data['productName'].lower()
        for style, keywords in style_keywords.items():
            for keyword in keywords:
                if keyword.lower() in product_name:
                    tags.append(style)
                    break
    tags = [tag.strip() for tag in tags if tag.strip()]
    return list(set(tags))

def extract_hashtags(text: str) -> list:
    """상품 설명에서 해시태그 추출"""
    import re
    return re.findall(r"#(\w+)", text)

def enrich_tags_with_hashtags(tags: list, product_name: str) -> list:
    """해시태그를 통한 태그 보강"""
    hashtags = extract_hashtags(product_name)
    if hashtags:
        return list(set(tags + hashtags))
    return tags

def recommend_tags_from_model(image_tags: list) -> list:
    """학습된 모델 기반 태그 추천 함수"""
    try:
        with open('tag_vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)
        with open('fashion_dataset.json', 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        input_vec = vectorizer.transform([" ".join(image_tags)])
        with open('tag_matrix.pkl', 'rb') as f:
            tfidf_matrix = pickle.load(f)
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(input_vec, tfidf_matrix).flatten()
        top_indices = similarities.argsort()[-5:][::-1]
        recommended_tags = []
        for idx in top_indices:
            if idx < len(dataset):
                recommended_tags.extend(dataset[idx].get('tags', []))
        recommended_tags = list(set(recommended_tags) - set(image_tags))
        return recommended_tags[:10]
    except Exception as e:
        print(f"태그 추천 오류: {e}")
        return []
