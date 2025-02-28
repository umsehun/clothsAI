import pandas as pd
import json
import os
import ast
from fashion_db import FashionDB

# DB 인스턴스 생성
db = FashionDB()

def process_musinsa_ranking_csv(csv_file="musinsa_ranking_api.csv"):
    """무신사 랭킹 CSV 파일 처리 (JSON 문자열 구조 처리)"""
    print(f"무신사 랭킹 CSV 처리 시작: {csv_file}")
    
    try:
        # CSV 파일 로드
        df = pd.read_csv(csv_file, encoding="utf-8-sig")
        print(f"CSV 데이터 로드 성공: {len(df)}행")
        
        processed_count = 0
        products = []
        
        # 각 행 처리
        for idx, row in df.iterrows():
            try:
                # JSON 문자열로 저장된 내용 파싱
                json_str = row['modules']
                
                # 문자열을 dict로 변환 (안전하게 처리)
                try:
                    data = ast.literal_eval(json_str)
                except:
                    try:
                        data = json.loads(json_str)
                    except:
                        print(f"행 {idx}: JSON 파싱 실패")
                        continue
                
                # 상품 아이템 추출
                if 'items' in data:
                    items = data['items']
                    for item in items:
                        if item.get('type') == 'PRODUCT_COLUMN':
                            product = {
                                'id': item.get('id'),
                                'brandName': item.get('info', {}).get('brandName'),
                                'productName': item.get('info', {}).get('productName'),
                                'price': item.get('info', {}).get('finalPrice'),
                                'image_url': item.get('image', {}).get('url'),
                                'discount': item.get('info', {}).get('discountRatio', 0)
                            }
                            
                            # 유효한 상품 데이터인지 확인
                            if product['productName'] and product['brandName']:
                                products.append(product)
                                processed_count += 1
                                
                                # 태그 추출
                                tags = extract_tags_from_product(product)
                                
                                # DB에 저장 (이미지 URL만 저장)
                                db.save_crawled_item(
                                    name=product['productName'],
                                    image_path=product.get('image_url', ''),
                                    source_url='',
                                    source_site='musinsa',
                                    tags=tags
                                )
            
            except Exception as e:
                print(f"행 {idx} 처리 중 오류: {e}")
        
        # 결과를 CSV로 저장 (옵션)
        if products:
            products_df = pd.DataFrame(products)
            products_df.to_csv("processed_musinsa_products.csv", index=False, encoding="utf-8-sig")
            
        print(f"무신사 랭킹 CSV 처리 완료, {processed_count}개 상품 저장됨")
        return processed_count
    
    except Exception as e:
        print(f"CSV 처리 중 오류: {e}")
        return 0

def process_musinsa_detailed_json(json_file="musinsa_detailed.json"):
    """무신사 상세 JSON 파일 처리"""
    print(f"무신사 상세 JSON 처리 시작: {json_file}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'musinsa' not in data:
            print("JSON 파일에 'musinsa' 키가 없습니다.")
            return 0
        
        musinsa_data = data['musinsa']
        processed_count = 0
        products = []
        
        # 각 섹션 처리 ('추천', '랭킹', '세일', '브랜드', '신상')
        for section_key, section_data in musinsa_data.items():
            print(f"섹션 처리: {section_key}")
            
            # 재귀적으로 상품 정보 찾기
            extract_products_recursive(section_data, products)
            
        # 중복 제거 (ID 기준)
        unique_products = {}
        for product in products:
            if 'id' in product and product['id'] not in unique_products:
                unique_products[product['id']] = product
        
        # DB에 저장
        for product in unique_products.values():
            if product.get('productName') and product.get('brandName'):
                # 태그 추출
                tags = extract_tags_from_product(product)
                
                # DB에 저장
                db.save_crawled_item(
                    name=product['productName'],
                    image_path=product.get('image_url', ''),
                    source_url='',
                    source_site='musinsa_detailed',
                    tags=tags
                )
                processed_count += 1
                
        # 결과를 CSV로 저장 (옵션)
        if unique_products:
            products_df = pd.DataFrame(list(unique_products.values()))
            products_df.to_csv("processed_musinsa_detailed.csv", index=False, encoding="utf-8-sig")
        
        print(f"무신사 상세 JSON 처리 완료, {processed_count}개 상품 저장됨")
        return processed_count
        
    except Exception as e:
        print(f"JSON 파일 처리 중 오류: {e}")
        return 0

def extract_products_recursive(data, products_list):
    """딕셔너리에서 재귀적으로 상품 정보 추출"""
    if isinstance(data, dict):
        # 상품 정보 패턴 확인
        if 'id' in data and 'productName' in data:
            # 상품 정보 추출
            product = {
                'id': data.get('id'),
                'brandName': data.get('brandName'),
                'productName': data.get('productName'),
                'price': data.get('finalPrice') or data.get('price'),
                'image_url': data.get('imageUrl') or (data.get('image', {}) or {}).get('url'),
                'discount': data.get('discountRatio') or data.get('discount', 0)
            }
            products_list.append(product)
        
        # 하위 항목 재귀적 탐색
        for key, value in data.items():
            if key == 'items' and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and item.get('type') == 'PRODUCT_COLUMN':
                        info = item.get('info', {})
                        image = item.get('image', {})
                        product = {
                            'id': item.get('id'),
                            'brandName': info.get('brandName'),
                            'productName': info.get('productName'),
                            'price': info.get('finalPrice'),
                            'image_url': image.get('url'),
                            'discount': info.get('discountRatio', 0)
                        }
                        products_list.append(product)
                    else:
                        extract_products_recursive(item, products_list)
            else:
                extract_products_recursive(value, products_list)
    
    elif isinstance(data, list):
        for item in data:
            extract_products_recursive(item, products_list)

def extract_tags_from_product(product_data):
    """상품 데이터에서 태그 추출"""
    tags = []
    
    # 브랜드 태그
    if 'brandName' in product_data and product_data['brandName']:
        tags.append(product_data['brandName'])
    
    # 상품명에서 태그 추출
    if 'productName' in product_data and product_data['productName']:
        product_name = product_data['productName'].lower()
        
        # 색상 태그 추출
        colors = {
            '검정': ['블랙', '검정', '검은색', 'black'],
            '흰색': ['화이트', '흰색', '하얀색', 'white'],
            '빨강': ['레드', '빨간색', '빨강', 'red', '버건디'],
            '파랑': ['블루', '파란색', '파랑', 'blue', '네이비'],
            '초록': ['그린', '초록색', 'green'],
            '노랑': ['옐로우', '노란색', 'yellow'],
            '회색': ['그레이', '회색', 'gray', 'grey'],
            '베이지': ['베이지', 'beige', '아이보리', 'ivory'],
            '보라': ['퍼플', '보라색', 'purple', '라벤더'],
            '핑크': ['핑크', '분홍색', 'pink'],
            '갈색': ['브라운', '갈색', 'brown'],
            '주황': ['오렌지', '주황색', 'orange']
        }
        
        for color, keywords in colors.items():
            for keyword in keywords:
                if keyword.lower() in product_name:
                    tags.append(color)
                    break
        
        # 카테고리 태그
        categories = {
            '상의': ['티셔츠', '니트', '맨투맨', '후드', '셔츠', '블라우스', '탑', '스웨터'],
            '하의': ['팬츠', '바지', '청바지', '데님', '슬랙스', '조거', '쇼츠', '레깅스', '스커트'],
            '아우터': ['자켓', '코트', '패딩', '점퍼', '집업', '가디건', '베스트'],
            '원피스': ['원피스', '드레스'],
            '신발': ['스니커즈', '구두', '로퍼', '샌들', '슬리퍼', '부츠'],
            '액세서리': ['모자', '벨트', '장갑', '스카프', '양말', '백', '가방']
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword.lower() in product_name:
                    tags.append(category)
                    tags.append(keyword)
                    break
    
    # 중복 제거 및 정렬
    tags = list(set(tags))
    return tags

if __name__ == "__main__":
    print("무신사 데이터 처리 시작...")
    
    # 랭킹 CSV 처리
    csv_count = process_musinsa_ranking_csv()
    
    # 상세 JSON 처리
    json_count = process_musinsa_detailed_json()
    
    print(f"\n처리 결과 요약:")
    print(f"CSV 파일에서 {csv_count}개 상품 처리")
    print(f"JSON 파일에서 {json_count}개 상품 처리")