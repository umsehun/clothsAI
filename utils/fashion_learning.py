import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import random
import argparse
from fashion_db import FashionDB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split

# 인자 파서 설정
parser = argparse.ArgumentParser(description='패션 아이템 학습 및 코디 생성')
parser.add_argument('--mode', choices=['train', 'generate', 'analyze'], default='train', 
                    help='실행 모드 (train: 학습, generate: 코디 생성, analyze: 분석)')
parser.add_argument('--iterations', type=int, default=1000, help='학습 반복 횟수')
parser.add_argument('--outfit_count', type=int, default=50, help='생성할 코디 수')
args = parser.parse_args()

# DB 인스턴스 생성
db = FashionDB()

def prepare_training_dataset(augment=True):
    """학습을 위한 데이터셋 준비"""
    print("학습 데이터셋 준비 중...")
    
    # DB에서 태그가 있는 모든 아이템 가져오기
    items = db.get_all_tags()
    crawled_items = db.get_crawled_items(limit=10000)
    
    dataset = []
    
    # 태그 데이터 처리
    if items:
        for item in items:
            item_id, image_path, image_name, tags_json, created_at = item
            
            if tags_json:
                tags = json.loads(tags_json)
                dataset.append({
                    'id': item_id,
                    'image_path': image_path,
                    'tags': tags,
                    'source': 'tags'
                })
    
    # 크롤링된 아이템 처리
    if crawled_items:
        for item in crawled_items:
            item_id, name, image_path, source_url, source_site, tags_json, created_at = item
            
            if tags_json:
                tags = json.loads(tags_json)
                dataset.append({
                    'id': item_id,
                    'name': name,
                    'image_path': image_path,
                    'tags': tags,
                    'source': source_site
                })
    
    print(f"기본 데이터셋: {len(dataset)}개의 아이템")
    
    # 데이터 증강 (선택사항)
    if augment and dataset:
        augmented_dataset = augment_dataset(dataset)
        print(f"데이터 증강 후: {len(augmented_dataset)}개의 아이템")
        dataset = augmented_dataset
    
    # 데이터셋 저장
    with open('fashion_dataset.json', 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    return dataset

def augment_dataset(dataset, multiplier=3):
    """데이터 증강: 유사한 태그 조합 생성"""
    augmented = []
    augmented.extend(dataset)  # 원본 데이터 포함
    
    all_tags = set()
    category_tags = {'상의': [], '하의': [], '아우터': [], '원피스': [], '신발': [], '액세서리': []}
    
    # 모든 태그와 카테고리별 태그 수집
    for item in dataset:
        tags = item.get('tags', [])
        for tag in tags:
            all_tags.add(tag)
            for category in category_tags.keys():
                if tag == category:
                    for t in tags:
                        if t != category:
                            category_tags[category].append(t)
    
    # 각 아이템에 대해 새로운 아이템 생성
    for idx, item in enumerate(dataset):
        orig_tags = item.get('tags', [])
        
        # 유사 아이템 여러 개 생성
        for i in range(multiplier - 1):
            # 복제본 생성
            new_item = item.copy()
            
            # 아이디 변경
            new_item['id'] = f"{item['id']}_aug_{i}"
            
            # 태그 수정: 일부 태그 추가 또는 삭제
            new_tags = orig_tags.copy()
            
            # 랜덤하게 태그 추가/삭제
            if len(new_tags) > 2 and random.random() < 0.4:
                # 태그 삭제 (1개)
                remove_idx = random.randint(0, len(new_tags) - 1)
                removed_tag = new_tags.pop(remove_idx)
                
                # 만약 카테고리 태그라면 삭제하지 않음
                if removed_tag in category_tags:
                    new_tags.append(removed_tag)
            
            # 태그 추가 (1-2개)
            for _ in range(random.randint(1, 2)):
                # 랜덤 태그 추가
                available_tags = list(all_tags - set(new_tags))
                if available_tags:
                    new_tag = random.choice(available_tags)
                    new_tags.append(new_tag)
            
            new_item['tags'] = new_tags
            augmented.append(new_item)
            
    return augmented

def train_tag_embedding_model(dataset, iterations=1000):
    """태그 임베딩 모델 생성 및 강화 학습"""
    print(f"태그 임베딩 모델 생성 중... (반복: {iterations}회)")
    
    # 모든 태그 모음
    all_tag_docs = []
    
    for item in dataset:
        if 'tags' in item and item['tags']:
            # 태그 목록을 공백으로 구분된 문자열로 변환
            tag_doc = " ".join(item['tags'])
            all_tag_docs.append(tag_doc)
    
    # 학습 데이터와 검증 데이터 분리
    train_docs, test_docs = train_test_split(all_tag_docs, test_size=0.2, random_state=42)
    
    # 추가 학습 데이터 생성 (반복)
    extended_docs = []
    for _ in range(iterations // len(train_docs) + 1):
        extended_docs.extend(train_docs)
    
    # 최대 iterations 수만큼 사용
    extended_docs = extended_docs[:iterations]
    print(f"확장된 학습 데이터: {len(extended_docs)}개")
    
    # TF-IDF 벡터화
    vectorizer = TfidfVectorizer(max_features=1000)
    tfidf_matrix = vectorizer.fit_transform(extended_docs)
    
    # 검증 데이터로 성능 평가
    test_matrix = vectorizer.transform(test_docs)
    validation_score = cosine_similarity(test_matrix, tfidf_matrix).mean()
    print(f"모델 검증 점수: {validation_score:.4f}")
    
    # 모델 저장
    import pickle
    with open('tag_vectorizer.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)
    
    with open('tag_matrix.pkl', 'wb') as f:
        pickle.dump(tfidf_matrix, f)
    
    print(f"태그 임베딩 모델 생성 완료 (어휘 크기: {len(vectorizer.vocabulary_)})")
    return vectorizer, tfidf_matrix

def generate_sample_outfits(count=50):
    """샘플 코디 자동 생성 함수"""
    print(f"{count}개의 샘플 코디 생성 시작...")
    
    try:
        with open('fashion_dataset.json', 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except:
        print("학습 데이터셋을 찾을 수 없습니다. 새로 준비합니다.")
        dataset = prepare_training_dataset()
    
    if not dataset:
        print("코디 생성을 위한 충분한 아이템이 없습니다.")
        return 0
    
    # 카테고리별로 아이템 분류
    categorized_items = {
        '상의': [],
        '하의': [],
        '아우터': [],
        '원피스': [],
        '신발': [],
        '액세서리': []
    }
    
    for item in dataset:
        if 'tags' in item and item['tags']:
            for tag in item['tags']:
                for category in categorized_items.keys():
                    if tag == category:
                        categorized_items[category].append(item)
                        break
    
    # 충분한 아이템이 있는지 확인
    total_items = sum(len(items) for items in categorized_items.values())
    if total_items < 10:
        print("코디 생성을 위한 충분한 아이템이 없습니다.")
        return 0
    
    # 스타일 옵션
    styles = ["미니멀룩", "스트릿패션", "보헤미안룩", "럭셔리룩", "빈티지룩", "스포티룩", "모던룩"]
    seasons = ["봄", "여름", "가을", "겨울"]
    
    created_count = 0
    
    # 코디 생성
    for i in range(count):
        try:
            style = random.choice(styles)
            season = random.choice(seasons)
            
            # 코디 구성 (최소 2개 이상의 카테고리)
            outfit = {}
            
            # 상의 또는 원피스는 필수
            if categorized_items['원피스'] and random.random() < 0.3:  # 30% 확률로 원피스 선택
                outfit['원피스'] = random.choice(categorized_items['원피스'])
            else:
                if categorized_items['상의']:
                    outfit['상의'] = random.choice(categorized_items['상의'])
                
                if categorized_items['하의']:
                    outfit['하의'] = random.choice(categorized_items['하의'])
            
            # 추가 아이템
            if categorized_items['아우터'] and random.random() < 0.7:  # 70% 확률로 아우터 추가
                outfit['아우터'] = random.choice(categorized_items['아우터'])
            
            if categorized_items['신발'] and random.random() < 0.8:  # 80% 확률로 신발 추가
                outfit['신발'] = random.choice(categorized_items['신발'])
            
            if categorized_items['액세서리'] and random.random() < 0.6:  # 60% 확률로 액세서리 추가
                outfit['액세서리'] = random.choice(categorized_items['액세서리'])
            
            # 최소 2개 이상의 아이템으로 구성
            if len(outfit) >= 2:
                # 코디 저장 형식 변환
                outfit_data = {}
                for category, item in outfit.items():
                    outfit_data[category] = {
                        'name': item.get('name', 'Unknown'),
                        'brand': '',
                        'price': 0,
                        'image_url': item.get('image_path', ''),
                        'id': item.get('id', '')
                    }
                
                # 기본 색상
                base_color = None
                for item in outfit.values():
                    for tag in item.get('tags', []):
                        if tag in ["검정", "흰색", "회색", "빨강", "파랑", "초록", "노랑", "보라", "핑크", "베이지"]:
                            base_color = tag
                            break
                    if base_color:
                        break
                
                # DB에 저장
                outfit_id = db.save_outfit(style, season, base_color, outfit_data)
                if outfit_id:
                    created_count += 1
                    print(f"코디 #{created_count} 생성 성공: {style} / {season} / {base_color}")
            
        except Exception as e:
            print(f"코디 생성 오류: {e}")
    
    print(f"총 {created_count}개의 코디가 생성되었습니다.")
    return created_count

def analyze_tag_distribution():
    """태그 분포 분석"""
    print("태그 분포 분석 중...")
    try:
        with open('fashion_dataset.json', 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        # 모든 태그 수집
        all_tags = []
        for item in dataset:
            all_tags.extend(item.get('tags', []))
        
        # 태그 빈도 분석
        from collections import Counter
        tag_counts = Counter(all_tags)
        
        # 상위 30개 태그
        top_tags = tag_counts.most_common(30)
        print("\n상위 30개 태그:")
        for tag, count in top_tags:
            print(f"{tag}: {count}개")
        
        # 카테고리 분석
        categories = ['상의', '하의', '아우터', '원피스', '신발', '액세서리']
        category_counts = {cat: tag_counts.get(cat, 0) for cat in categories}
        print("\n카테고리 분포:")
        for cat, count in category_counts.items():
            print(f"{cat}: {count}개")
        
        # 결과를 JSON 파일로 저장
        analysis_result = {
            'total_tags': len(all_tags),
            'unique_tags': len(tag_counts),
            'top_tags': dict(top_tags),
            'categories': category_counts
        }
        with open('tag_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n분석 결과가 'tag_analysis.json'에 저장되었습니다.")
        
    except Exception as e:
        print(f"태그 분석 중 오류: {e}")

if __name__ == "__main__":
    print(f"패션 데이터 처리 시작... 모드: {args.mode}")
    
    if args.mode == 'train':
        # 1. 학습 데이터셋 준비
        dataset = prepare_training_dataset(augment=True)
        
        # 2. 태그 임베딩 모델 생성
        if dataset:
            vectorizer, tfidf_matrix = train_tag_embedding_model(dataset, iterations=args.iterations)
            print("학습 완료!")
        
    elif args.mode == 'generate':
        # 샘플 코디 생성
        outfit_count = generate_sample_outfits(args.outfit_count)
        print(f"코디 생성 완료: {outfit_count}개")
        
    elif args.mode == 'analyze':
        # 태그 분석
        analyze_tag_distribution()
    
    print("처리 완료!")