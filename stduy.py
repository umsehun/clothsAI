import os
import json
import pandas as pd
import re
from fashion_db import FashionDB
from PIL import Image
import requests
from io import BytesIO
import time
from datetime import datetime
import random

class MusinsaDataProcessor:
    def __init__(self):
        self.db = FashionDB()
        self.image_save_dir = "musinsa_images"
        
        # 디렉토리 생성
        if not os.path.exists(self.image_save_dir):
            os.makedirs(self.image_save_dir)
            
        # 태그 추출용 키워드 사전
        self.style_keywords = {
            "미니멀": ["미니멀", "심플", "베이직", "클래식", "기본"],
            "캐주얼": ["캐주얼", "데일리", "일상", "편안한", "루즈핏", "오버핏"],
            "스트릿": ["스트릿", "힙합", "그래픽", "로고", "스트리트", "스케이트"],
            "스포티": ["스포티", "액티브", "애슬레저", "스포츠", "운동"],
            "레트로": ["레트로", "빈티지", "올드스쿨", "복고", "클래식"],
            "모던": ["모던", "세련된", "시크", "컨템포러리", "도시적"],
            "페미닌": ["페미닌", "로맨틱", "여성스러운", "레이스", "플라워", "플로럴"],
            "럭셔리": ["럭셔리", "고급", "프리미엄", "명품", "클래식"],
        }
        
        self.season_keywords = {
            "봄": ["봄", "spring", "가벼운", "얇은"],
            "여름": ["여름", "summer", "시원한", "쿨링", "쿨", "통풍"],
            "가을": ["가을", "autumn", "fall", "두꺼운", "웜"],
            "겨울": ["겨울", "winter", "패딩", "눕시", "퍼", "기모", "보온", "따뜻한"]
        }
        
        self.category_keywords = {
            "상의": ["티셔츠", "니트", "맨투맨", "후드", "셔츠", "블라우스", "스웨터", "티", "탑"],
            "하의": ["팬츠", "바지", "청바지", "데님", "스커트", "레깅스", "슬랙스", "쇼츠", "치마"],
            "아우터": ["자켓", "코트", "패딩", "점퍼", "가디건", "집업", "베스트", "후드집업", "윈드브레이커"],
            "신발": ["스니커즈", "로퍼", "샌들", "슬리퍼", "부츠", "런닝화", "힐", "슈즈", "워커"],
            "액세서리": ["모자", "벨트", "장갑", "스카프", "양말", "백", "가방", "선글라스", "주얼리", "시계", "캡"]
        }
        
        self.color_keywords = {
            "검정": ["블랙", "검정", "검은색", "black"],
            "흰색": ["화이트", "흰색", "하얀색", "white"],
            "빨강": ["레드", "빨간색", "빨강", "red", "버건디"],
            "파랑": ["블루", "파란색", "파랑", "blue", "네이비"],
            "초록": ["그린", "초록색", "green"],
            "노랑": ["옐로우", "노란색", "yellow"],
            "회색": ["그레이", "회색", "gray", "grey"],
            "베이지": ["베이지", "beige", "아이보리", "ivory", "크림", "cream"],
            "보라": ["퍼플", "보라색", "purple", "라벤더"],
            "핑크": ["핑크", "분홍색", "pink"],
            "갈색": ["브라운", "갈색", "brown"],
            "주황": ["오렌지", "주황색", "orange"]
        }
    
    def download_and_save_image(self, image_url, product_id):
        """이미지를 다운로드하여 저장하고 로컬 경로를 반환"""
        try:
            # 최대 3번 시도
            for attempt in range(3):
                try:
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        break
                except:
                    if attempt == 2:  # 마지막 시도
                        return None
                    time.sleep(1)  # 재시도 전 1초 대기
            
            if response.status_code != 200:
                return None
                
            # 이미지 저장
            img = Image.open(BytesIO(response.content))
            file_path = os.path.join(self.image_save_dir, f"{product_id}.jpg")
            img.save(file_path)
            return file_path
            
        except Exception as e:
            print(f"이미지 다운로드 오류 ({image_url}): {e}")
            return None
            
def extract_tags_from_product(self, product_data):
    """상품 데이터에서 태그 추출"""
    tags = []
    
    # 제품명이나 브랜드명이 없으면 빈 태그 리스트 반환
    product_name = product_data.get('product_name', '')
    if not product_name:
        return tags
        
    # 카테고리 태그 추출
    category_found = False
    for category, keywords in self.category_keywords.items():
        if not category_found:
            for keyword in keywords:
                if keyword.lower() in product_name.lower():
                    tags.append(category)
                    tags.append(keyword)
                    category_found = True
                    break
    
    # 기본 카테고리 할당 (태그가 없는 경우)
    if not category_found:
        tags.append("의류")
    
    # 스타일 태그 추출
    style_found = False
    for style, keywords in self.style_keywords.items():
        if not style_found:
            for keyword in keywords:
                if keyword.lower() in product_name.lower():
                    tags.append(style)
                    style_found = True
                    break
    
    # 기본 스타일 할당 (태그가 없는 경우)
    if not style_found:
        tags.append("캐주얼")
                    
    # 색상 태그 추출
    color_found = False
    for color, keywords in self.color_keywords.items():
        if not color_found:
            for keyword in keywords:
                if keyword.lower() in product_name.lower():
                    tags.append(color)
                    color_found = True
                    break
    
    # 브랜드 추가
    if 'brand_name' in product_data and product_data['brand_name']:
        tags.append(product_data['brand_name'])
        
    # 중복 제거 및 정렬
    tags = list(set(tags))
    return tags
            
def process_musinsa_ranking_csv(self, csv_file="musinsa_ranking_api.csv"):
    """무신사 랭킹 CSV 파일 처리"""
    try:
        print(f"무신사 랭킹 CSV 처리 시작: {csv_file}")
        
        # 기존 코드 대신 더 간단한 방법으로 처리
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        print(f"CSV 데이터 로드 성공: {len(df)}행")
        
        # 데이터 구조 확인을 위해 첫 행 출력
        print("첫 번째 행 샘플:")
        first_row = df.iloc[0]
        print(first_row)
        
        processed_count = 0
        
        # 데이터 구조에 맞게 처리 로직 수정
        for idx, row in df.iterrows():
            try:
                # JSON 문자열로 저장된 행인지 확인
                first_cell = str(row.iloc[0]) if len(row) > 0 else ""
                
                # JSON 형식이 아니면 일반 CSV로 처리
                if not first_cell.startswith('{'):
                    # 기본 필드 추출
                    product_id = str(idx)
                    product_name = row.get('productName', '') if 'productName' in df.columns else ''
                    brand_name = row.get('brandName', '') if 'brandName' in df.columns else ''
                    
                    # 태그 추출
                    product_data = {
                        'product_id': product_id,
                        'product_name': product_name,
                        'brand_name': brand_name
                    }
                    
                    tags = self.extract_tags_from_product(product_data)
                    
                    # 상품명이 없으면 스킵
                    if not product_name:
                        continue
                    
                    # DB에 저장
                    self.db.save_crawled_item(
                        name=product_name,
                        image_path="placeholder.jpg", # 이미지 없음
                        source_url="",
                        source_site='musinsa',
                        tags=tags
                    )
                    processed_count += 1
                    
                else:
                    # 기존 코드 (JSON 파싱) 실행
                    # ...기존 코드...
                    pass
                
            except Exception as e:
                print(f"행 처리 중 오류 (행 {idx}): {e}")
                continue
        
        print(f"무신사 랭킹 CSV 처리 완료, {processed_count}개 상품 저장됨")
        return processed_count
        
    except Exception as e:
        print(f"CSV 파일 처리 중 오류: {e}")
        return 0

def process_musinsa_detailed_json(self, json_file="musinsa_detailed.json"):
    """무신사 상세 JSON 파일 처리"""
    try:
        print(f"무신사 상세 JSON 처리 시작: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"JSON 데이터 타입: {type(data)}")
        
        processed_count = 0
        
        # 데이터 구조가 예상과 다를 경우 대비한 처리
        if isinstance(data, dict):
            # 구조 출력
            print("JSON 최상위 키:")
            for key in data.keys():
                print(f" - {key}")
                
            # 각 항목을 순회하면서 처리
            for key, value in data.items():
                try:
                    # 타입 체크
                    if isinstance(value, str):
                        print(f"키 '{key}'는 문자열 값입니다. 건너뜁니다.")
                        continue
                        
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                # 상품 데이터 추출
                                product_name = item.get('name', '')
                                if not product_name:
                                    product_name = item.get('goodsName', '')
                                
                                image_url = item.get('imageUrl', '')
                                
                                # 상품 데이터 처리
                                product_data = {
                                    'product_id': item.get('id', str(random.randint(100000, 999999))),
                                    'product_name': product_name,
                                    'brand_name': item.get('brandName', ''),
                                    'image_url': image_url
                                }
                                
                                # 태그 추출
                                tags = self.extract_tags_from_product(product_data)
                                
                                # DB에 저장
                                if product_name:
                                    self.db.save_crawled_item(
                                        name=product_name,
                                        image_path="placeholder.jpg",  # 이미지 없음
                                        source_url="",
                                        source_site='musinsa_detailed',
                                        tags=tags
                                    )
                                    processed_count += 1
                    
                    elif isinstance(value, dict):
                        # 딕셔너리는 재귀적으로 처리할 수 있도록 추가 구현
                        pass
                        
                except Exception as e:
                    print(f"키 '{key}' 처리 중 오류: {e}")
        
        print(f"무신사 상세 JSON 처리 완료, {processed_count}개 상품 저장됨")
        return processed_count
            
    except Exception as e:
        print(f"JSON 파일 처리 중 오류: {e}")
        return 0
            
    def process_musinsa_detailed_json(self, json_file="musinsa_detailed.json"):
        """무신사 상세 JSON 파일 처리"""
        try:
            print(f"무신사 상세 JSON 처리 시작: {json_file}")
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            processed_count = 0
            
            # 스토어 데이터 순회
            for store_name, store_data in data.items():
                # 판별 데이터 순회
                for panel_name, panel_data in store_data.items():
                    for item in panel_data:
                        try:
                            # 상품 ID 생성 (없으면 랜덤)
                            product_id = item.get('id', str(random.randint(100000, 999999)))
                            
                            # 기본 정보 추출
                            product_name = item.get('goodsName', '')
                            if not product_name:
                                product_name = item.get('name', '')
                            
                            brand_name = item.get('brandName', '')
                            price = item.get('price', 0)
                            
                            # 이미지 URL 추출
                            image_url = item.get('imageUrl', '')
                            if not image_url and 'thumbnailImageUrl' in item:
                                image_url = item['thumbnailImageUrl']
                                
                            # 상품 URL 추출
                            product_url = item.get('linkUrl', '')
                            
                            # 상세 상품 정보 구성
                            product_data = {
                                'product_id': product_id,
                                'product_name': product_name,
                                'brand_name': brand_name,
                                'price': price,
                                'image_url': image_url,
                                'product_url': product_url,
                                'category_id': item.get('categoryId', ''),
                                'original_price': item.get('originalPrice', price)
                            }
                            
                            # 태그 추출
                            tags = self.extract_tags_from_product(product_data)
                            
                            # 이미지 다운로드
                            if image_url:
                                local_image_path = self.download_and_save_image(image_url, product_id)
                                
                                if local_image_path:
                                    # DB에 저장
                                    self.db.save_crawled_item(
                                        name=product_name,
                                        image_path=local_image_path,
                                        source_url=product_url,
                                        source_site='musinsa_detailed',
                                        tags=tags
                                    )
                                    processed_count += 1
                                    
                                    # 진행 상황 표시
                                    if processed_count % 10 == 0:
                                        print(f"{processed_count}개 상품 처리 완료")
                        
                        except Exception as e:
                            print(f"아이템 처리 중 오류: {e}")
                            continue
            
            print(f"무신사 상세 JSON 처리 완료, {processed_count}개 상품 저장됨")
            return processed_count
                
        except Exception as e:
            print(f"JSON 파일 처리 중 오류: {e}")
            return 0
            
    def generate_sample_outfits(self, count=20):
        """저장된 상품을 기반으로 샘플 코디 생성"""
        try:
            print(f"{count}개의 샘플 코디 생성 시작")
            
            # 크롤링된 아이템 가져오기
            items = self.db.get_crawled_items(limit=500)  # 충분한 데이터 확보
            
            if not items:
                print("코디 생성을 위한 충분한 아이템이 없습니다.")
                return 0
                
            # 아이템을 카테고리별로 분류
            categorized = {
                "상의": [],
                "하의": [],
                "아우터": [],
                "신발": [],
                "액세서리": []
            }
            
            for item in items:
                try:
                    item_id, name, image_path, source_url, source_site, tags_json, created_at = item
                    
                    if tags_json:
                        tags = json.loads(tags_json)
                        
                        # 카테고리 결정
                        for tag in tags:
                            for category in categorized.keys():
                                if tag == category:
                                    categorized[category].append({
                                        'id': item_id,
                                        'name': name,
                                        'image_path': image_path,
                                        'tags': tags
                                    })
                                    break
                except Exception as e:
                    continue
            
            # 충분한 아이템이 있는 카테고리 확인
            valid_categories = {}
            for category, items in categorized.items():
                if len(items) >= 5:  # 최소 5개 이상 있어야 유효
                    valid_categories[category] = items
            
            if len(valid_categories) < 2:
                print("코디 생성을 위한 충분한 카테고리 데이터가 없습니다.")
                return 0
                
            # 스타일 목록 (앱의 STYLE_OPTIONS와 일치)
            styles = [
                "미니멀룩", "스트릿패션", "보헤미안룩", "럭셔리룩", 
                "아방가르드룩", "러블리룩", "빈티지룩", "스포티룩", 
                "모던룩", "그런지룩", "프레피룩"
            ]
            
            seasons = ["봄", "여름", "가을", "겨울"]
            colors = [None, "검정", "흰색", "베이지", "회색", "파랑", "갈색", "초록"]
            
            created_count = 0
            
            for _ in range(count):
                try:
                    # 코디에 포함할 카테고리 선택 (최소 2개 ~ 최대 5개)
                    categories_to_include = random.sample(
                        list(valid_categories.keys()),
                        min(random.randint(2, 5), len(valid_categories))
                    )
                    
                    # 코디 아이템 선택
                    outfit = {}
                    for category in categories_to_include:
                        selected_item = random.choice(valid_categories[category])
                        outfit[category] = {
                            'name': selected_item['name'],
                            'image': selected_item['image_path']
                        }
                    
                    # 랜덤 스타일, 시즌, 색상 선택
                    style = random.choice(styles)
                    season = random.choice(seasons)
                    color = random.choice(colors)
                    
                    # DB에 저장
                    outfit_id = self.db.save_outfit(style, season, color, outfit)
                    if outfit_id:
                        created_count += 1
                        
                except Exception as e:
                    print(f"코디 생성 중 오류: {e}")
                    continue
                    
            print(f"샘플 코디 생성 완료, {created_count}개 생성됨")
            return created_count
            
        except Exception as e:
            print(f"샘플 코디 생성 중 오류: {e}")
            return 0

# 실행
if __name__ == "__main__":
    processor = MusinsaDataProcessor()
    
    # CSV 파일 처리
    csv_count = processor.process_musinsa_ranking_csv()
    
    # JSON 파일 처리
    json_count = processor.process_musinsa_detailed_json()
    
    # 샘플 코디 생성
    outfit_count = processor.generate_sample_outfits(50)
    
    print(f"\n처리 결과 요약:")
    print(f"CSV 파일에서 {csv_count}개 상품 처리")
    print(f"JSON 파일에서 {json_count}개 상품 처리")
    print(f"{outfit_count}개의 샘플 코디 생성")