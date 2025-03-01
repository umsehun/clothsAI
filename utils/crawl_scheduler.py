import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import random
import pandas as pd
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from modules.musinsa_api import fetch_recommended_products, fetch_product_detail
from utils.category import crawl_musinsa_category
from fashion_db import FashionDB

db = FashionDB()

def collect_musinsa_data(target_count=100):
    """무신사 데이터를 크롤링으로 수집하고 DB에 저장"""
    print(f"목표 수집 데이터: {target_count}개")
    total_saved = 0
    
    # 대체 데이터 소스 추가 - 무신사 대신 다른 패션몰도 고려
    categories = [
        # 무신사 카테고리
        "https://www.musinsa.com/categories/item/001",  # 상의
        "https://www.musinsa.com/categories/item/003",  # 하의
        "https://www.musinsa.com/categories/item/002",  # 아우터
        
        # 대체 패션몰 카테고리 URL (예: 29CM)
        "https://www.29cm.co.kr/shop/collection?tab=new",  # 신상품 
    ]
    
    # 각 카테고리당 최대 항목 수
    items_per_category = max(3, target_count // len(categories))  # 최소 3개씩은 수집
    
    for category_url in categories:
        try:
            # URL에 따라 크롤링 함수 호출
            if "musinsa.com" in category_url:
                category_name = category_url.split('/')[-1]
                print(f"\n무신사 {category_name} 카테고리 크롤링 시작...")
                products = crawl_musinsa_category(category_url, max_items=items_per_category)
                site_name = f"musinsa_{category_name}"
            elif "29cm.co.kr" in category_url:
                print(f"\n29CM 크롤링 시작...")
                products = crawl_29cm(category_url, max_items=items_per_category)
                site_name = "29cm"
            else:
                print(f"지원하지 않는 URL: {category_url}")
                continue
            
            if not products:
                print(f"URL {category_url}에서 상품을 찾지 못했습니다.")
                continue
                
            for product in products:
                # 태그 생성
                tags = []
                
                # 브랜드가 있으면 추가
                if 'brand' in product and product['brand']:
                    tags.append(product['brand'])
                
                # 카테고리 정보 추가
                if 'category' in product and product['category']:
                    tags.append(f"카테고리:{product['category']}")
                
                # 상품명에서 키워드 추출
                if 'name' in product and product['name']:
                    words = product['name'].split()
                    for word in words:
                        # 의미 있는 키워드만 추가
                        if len(word) > 1 and word not in ["상품", "제품", "신상", "할인", "세일"]:
                            tags.append(word)
                
                # DB에 저장
                db.save_crawled_item(
                    name=product.get('name', f"상품_{total_saved}"),
                    image_path=product.get('image_url', ''),
                    source_url=category_url,
                    source_site=site_name,
                    tags=tags
                )
                total_saved += 1
                
            print(f"{category_url}에서 {len(products)}개 수집 완료")
            
            # 사이트 간 대기 시간
            delay = random.uniform(10, 15)
            print(f"{delay:.1f}초 대기 중...")
            time.sleep(delay)
            
        except Exception as e:
            print(f"크롤링 중 오류: {e}")
    
    print(f"\n총 {total_saved}개의 상품 데이터를 저장했습니다.")
    return total_saved

def crawl_29cm(url, max_items=10):
    """29CM 웹사이트에서 상품 정보 수집"""
    print(f"29CM 크롤링: {url}")
    results = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"29CM 접근 실패: 상태 코드 {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 29CM 상품 요소 찾기
        items = soup.select('.product-card')
        
        for i, item in enumerate(items[:max_items]):
            try:
                # 상품명
                name_elem = item.select_one('.product-card__name')
                # 브랜드명
                brand_elem = item.select_one('.product-card__brand')
                # 이미지
                img_elem = item.select_one('.product-card__image img')
                
                if name_elem and img_elem:
                    product_name = name_elem.text.strip()
                    brand_name = brand_elem.text.strip() if brand_elem else ""
                    img_url = img_elem.get('src', '')
                    
                    if not img_url and img_elem.has_attr('data-src'):
                        img_url = img_elem['data-src']
                    
                    if img_url:
                        results.append({
                            'name': product_name,
                            'brand': brand_name,
                            'image_url': img_url,
                            'category': '29cm'  # 기본 카테고리
                        })
                        print(f"29CM 상품 추가: {product_name}")
            except Exception as e:
                print(f"29CM 상품 처리 중 오류: {e}")
                
        return results
    except Exception as e:
        print(f"29CM 크롤링 중 오류: {e}")
        return []

if __name__ == "__main__":
    # 데이터 수집 실행
    print("데이터 수집 시작...")
    num_collected = collect_musinsa_data(target_count=20)  # 테스트용 소량 수집
    
    # CSV 내보내기
    if num_collected > 0:
        try:
            items = db.get_crawled_items(limit=10000)
            if not items:
                print("내보낼 데이터가 없습니다.")
            else:
                df = pd.DataFrame(items, columns=['id', 'name', 'image_path', 'source_url', 'source_site', 'tags', 'created_at'])
                
                os.makedirs("dataset", exist_ok=True)
                now = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"dataset/fashion_data_{now}.csv"
                
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
                print(f"데이터를 {filepath}에 저장했습니다. (총 {len(df)}개 항목)")
        except Exception as e:
            print(f"CSV 내보내기 오류: {e}")