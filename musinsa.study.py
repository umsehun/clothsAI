import os
import json
import pickle
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from fashion_db import FashionDB
from PIL import Image
from io import BytesIO
import time
from datetime import datetime
import random

# DB 연결
db = FashionDB()

def crawl_more_musinsa_data(pages=5, items_per_page=60):
    """무신사 데이터 추가 수집"""
    print(f"무신사 데이터 추가 수집 시작 (총 {pages} 페이지)")
    
    # 수집할 카테고리 URL 리스트 (각 카테고리별 인기 상품)
    category_urls = [
        "https://www.musinsa.com/category/001?gf=A", # 상의
        "https://www.musinsa.com/category/003?gf=A", # 하의
        "https://www.musinsa.com/category/002?gf=A", # 아우터
        "https://www.musinsa.com/category/100?gf=A", # 원피스
        "https://www.musinsa.com/main/sneaker/recommend", # 신발
        "https://www.musinsa.com/category/101?gf=A"  # 액세서리
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    collected_items = 0
    
    for category_url in category_urls:
        category_name = category_url.split('/')[-1]
        print(f"\n카테고리 '{category_name}' 수집 시작...")
        
        for page in range(1, pages + 1):
            try:
                # 페이지 URL 구성
                page_url = f"{category_url}?page={page}"
                print(f"페이지 {page} 처리 중... ({page_url})")
                
                response = requests.get(page_url, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 상품 목록 가져오기
                    items = soup.select('li.li_box')
                    
                    # 페이지당 설정한 수만큼만 처리
                    for idx, item in enumerate(items[:items_per_page]):
                        try:
                            # 상품 정보 추출
                            img_element = item.select_one('img.lazyload')
                            brand_element = item.select_one('p.item_title')
                            title_element = item.select_one('p.list_info')
                            price_element = item.select_one('p.price')
                            
                            if not (img_element and title_element):
                                continue
                                
                            # 이미지 URL 가져오기
                            img_url = img_element.get('data-original', '') or img_element.get('src', '')
                            if img_url.startswith('//'):
                                img_url = 'https:' + img_url
                            
                            # 상품명 가져오기
                            product_name = title_element.text.strip() if title_element else "제품명 없음"
                            brand_name = brand_element.text.strip() if brand_element else ""
                            price = price_element.text.strip() if price_element else ""
                            
                            # 태그 추출
                            product_data = {
                                'productName': product_name,
                                'brandName': brand_name,
                                'category': map_category_name(category_name),
                                'price': price
                            }
                            
                            tags = extract_tags_from_product(product_data)
                            
                            # DB에 저장
                            db.save_crawled_item(
                                name=product_name,
                                image_path=img_url,  # 이미지 URL 저장
                                source_url=page_url,
                                source_site='musinsa',
                                tags=tags
                            )
                            
                            collected_items += 1
                            if collected_items % 10 == 0:
                                print(f"총 {collected_items}개 항목 수집 완료")
                            
                        except Exception as e:
                            print(f"아이템 처리 중 오류: {e}")
                    
                    # 과도한 요청 방지를 위한 대기
                    time.sleep(2)
                    
                else:
                    print(f"페이지 {page} 접근 실패: HTTP {response.status_code}")
            
            except Exception as e:
                print(f"페이지 {page} 처리 중 오류: {e}")
    
    print(f"\n데이터 수집 완료: 총 {collected_items}개 항목 수집")
    return collected_items

def map_category_name(category_code):
    """카테고리 코드를 이름으로 매핑"""
    category_map = {
        '001': '상의',
        '002': '아우터',
        '003': '하의',
        '020': '원피스',
        '005': '신발',
        '011': '액세서리'
    }
    return category_map.get(category_code, '기타')

def extract_tags_from_product(product_data):
    """상품 정보에서 태그 추출"""
    tags = []
    
    # 브랜드명 추가
    if 'brandName' in product_data and product_data['brandName']:
        tags.append(product_data['brandName'])
    
    # 카테고리 추가
    if 'category' in product_data and product_data['category']:
        tags.append(product_data['category'])
    
    # 상품명에서 키워드 추출
    if 'productName' in product_data and product_data['productName']:
        product_name = product_data['productName'].lower()
        
        # 색상 태그 추출
        colors = {
            '검정': ['블랙', '검정', '검은색', 'black'],
            '흰색': ['화이트', '흰색', '하얀색', 'white'],
            '빨강': ['레드', '빨강', '빨간색', 'red', '버건디'],
            '파랑': ['블루', '파랑', '파란색', 'blue', '네이비'],
            '초록': ['그린', '초록', '초록색', 'green', '카키'],
            '노랑': ['옐로우', '노랑', '노란색', 'yellow'],
            '회색': ['그레이', '회색', 'gray', 'grey'],
            '베이지': ['베이지', 'beige', '아이보리', 'ivory', '크림'],
            '보라': ['퍼플', '보라', '보라색', 'purple', '라벤더'],
            '핑크': ['핑크', '분홍', '분홍색', 'pink'],
            '갈색': ['브라운', '갈색', 'brown', '탄', '탄색'],
            '주황': ['오렌지', '주황', '주황색', 'orange']
        }
        
        for color, keywords in colors.items():
            for keyword in keywords:
                if keyword in product_name:
                    tags.append(color)
                    break
        
        # 소재 태그 추출
        materials = {
            '데님': ['데님', '청', '진', 'jeans', 'denim'],
            '코튼': ['코튼', '면', 'cotton'],
            '니트': ['니트', '울', '캐시미어', '스웨터', 'knit', 'wool'],
            '가죽': ['가죽', '레더', 'leather'],
            '린넨': ['린넨', '마', 'linen'],
            '실크': ['실크', '시크', 'silk'],
            '플리스': ['플리스', '양털', 'fleece'],
            '폴리에스터': ['폴리에스터', '폴리', 'polyester']
        }
        
        for material, keywords in materials.items():
            for keyword in keywords:
                if keyword in product_name:
                    tags.append(material)
                    break
        
        # 계절 태그 추출
        seasons = {
            '봄': ['봄', 'spring', '20ss', '21ss', '22ss', '23ss'],
            '여름': ['여름', '서머', 'summer', '썸머'],
            '가을': ['가을', '오텀', 'autumn', 'fall'],
            '겨울': ['겨울', '윈터', 'winter']
        }
        
        for season, keywords in seasons.items():
            for keyword in keywords:
                if keyword in product_name:
                    tags.append(season)
                    break
        
        # 스타일 태그 추출
        styles = {
            '캐주얼': ['캐주얼', '데일리', '일상', '캐쥬얼', 'casual'],
            '스트릿': ['스트릿', '힙합', '그래픽', '로고', '스트리트', '스케이트', 'street', 'streetwear'],
            '미니멀': ['미니멀', '심플', '베이직', '미니멀리즘', 'minimal', 'simple', 'basic'],
            '빈티지': ['빈티지', '레트로', '올드스쿨', '클래식', 'vintage', 'retro'],
            '스포티': ['스포티', '액티브', '애슬레저', '스포츠', '운동', 'sport', 'active'],
            '포멀': ['포멀', '드레스', '정장', '포멜', 'formal', 'suit']
        }
        
        for style, keywords in styles.items():
            for keyword in keywords:
                if keyword in product_name:
                    tags.append(style)
                    break
        
        # 핏 태그 추출
        fits = {
            '오버사이즈': ['오버사이즈', '오버핏', '루즈', 'oversize', 'oversized'],
            '슬림핏': ['슬림핏', '스키니', '슬림', 'slim', 'skinny'],
            '크롭': ['크롭', '크롭핏', '크롭드', 'crop', 'cropped'],
            '와이드': ['와이드', '통넓은', '배기', '벙넙', 'wide'],
            '테이퍼드': ['테이퍼드', '테이퍼', 'tapered'],
            '레귤러': ['레귤러', '스탠다드', '일자', 'regular', 'standard']
        }
        
        for fit, keywords in fits.items():
            for keyword in keywords:
                if keyword in product_name:
                    tags.append(fit)
                    break
    
    # 중복 제거 및 정렬
    tags = list(set(tags))
    return tags

def enrich_existing_tags():
    """기존에 저장된 아이템의 태그 품질 향상"""
    print("기존 아이템의 태그 품질 향상 시작...")
    
    # DB에서 크롤링된 모든 아이템 가져오기
    crawled_items = db.get_crawled_items(limit=10000)
    
    updated_count = 0
    for item in crawled_items:
        item_id, name, image_path, source_url, source_site, tags_json, created_at = item
        
        try:
            # 기존 태그 로드
            existing_tags = json.loads(tags_json) if tags_json else []
            
            # 상품 데이터 구성
            product_data = {
                'productName': name,
                'category': extract_category_from_tags(existing_tags)
            }
            
            # 새로운 태그 추출
            new_tags = extract_tags_from_product(product_data)
            
            # 기존 태그와 새 태그 병합 (중복 제거)
            combined_tags = list(set(existing_tags + new_tags))
            
            # 태그가 추가되었으면 DB 업데이트
            if len(combined_tags) > len(existing_tags):
                db._connect()
                db.conn.cursor().execute(
                    "UPDATE crawled_items SET tags = ? WHERE id = ?",
                    (json.dumps(combined_tags), item_id)
                )
                db.conn.commit()
                db._close()
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"{updated_count}개 아이템 태그 업데이트 완료")
                
        except Exception as e:
            print(f"아이템 ID {item_id} 태그 업데이트 실패: {e}")
    
    print(f"태그 품질 향상 완료: 총 {updated_count}개 아이템 업데이트")
    return updated_count

def extract_category_from_tags(tags):
    """태그 리스트에서 카테고리 추출"""
    categories = ['상의', '하의', '아우터', '원피스', '신발', '액세서리']
    for tag in tags:
        if tag in categories:
            return tag
    return ''

def generate_enhanced_outfits(count=50):
    """향상된 코디 생성 함수"""
    print(f"향상된 코디 {count}개 생성 시작...")
    
    # 기존 코디 수 확인
    existing_outfits = db.get_all_outfits()
    existing_count = len(existing_outfits)
    print(f"현재 저장된 코디 수: {existing_count}")
    
    # 크롤링된 아이템 가져오기
    crawled_items = db.get_crawled_items(limit=2000)
    
    # 카테고리별 아이템 분류
    categorized_items = {
        '상의': [],
        '하의': [],
        '아우터': [],
        '원피스': [],
        '신발': [],
        '액세서리': []
    }
    
    # 아이템 분류
    for item in crawled_items:
        item_id, name, image_path, source_url, source_site, tags_json, created_at = item
        
        if not tags_json:
            continue
            
        tags = json.loads(tags_json)
        item_data = {
            'id': item_id,
            'name': name,
            'image_path': image_path,
            'tags': tags
        }
        
        # 카테고리 분류
        for category in categorized_items.keys():
            if category in tags:
                categorized_items[category].append(item_data)
                break
    
    # 각 카테고리별 아이템 수 확인
    for category, items in categorized_items.items():
        print(f"{category}: {len(items)}개 아이템")
    
    # 아이템이 너무 적은 경우 종료
    if sum(len(items) for items in categorized_items.values()) < 20:
        print("코디 생성을 위한 충분한 아이템이 없습니다.")
        return 0
    
    created_count = 0
    
    # 코디 생성
    for i in range(count):
        try:
            # 랜덤 스타일과 계절 선택
            style = random.choice([
                "미니멀룩", "스트릿패션", "캐주얼룩", "빈티지룩", 
                "스포티룩", "포멀룩", "모던룩"
            ])
            
            season = random.choice(["봄", "여름", "가을", "겨울"])
            
            # 코디 생성 방식 선택 (1: 원피스 기반, 2: 상하의 기반)
            outfit_type = random.choice([1, 2])
            
            outfit = {}
            
            # 색상 조합 원칙
            base_colors = ["검정", "흰색", "회색", "베이지", None]
            base_color = random.choice(base_colors)
            
            # 원피스 기반 코디
            if outfit_type == 1 and categorized_items['원피스']:
                outfit['원피스'] = random.choice(categorized_items['원피스'])
            # 상하의 기반 코디
            else:
                if categorized_items['상의']:
                    outfit['상의'] = random.choice(categorized_items['상의'])
                if categorized_items['하의']:
                    outfit['하의'] = random.choice(categorized_items['하의'])
            
            # 기본 아이템이 부족하면 다음 반복으로
            if len(outfit) < 1:
                continue
            
            # 아우터 추가 (계절에 맞게, 가을/겨울에 확률 높임)
            if categorized_items['아우터'] and season in ["가을", "겨울", "봄"] and random.random() < 0.8:
                outfit['아우터'] = random.choice(categorized_items['아우터'])
            elif categorized_items['아우터'] and season == "여름" and random.random() < 0.3:
                outfit['아우터'] = random.choice(categorized_items['아우터'])
            
            # 신발 추가 (80% 확률)
            if categorized_items['신발'] and random.random() < 0.8:
                outfit['신발'] = random.choice(categorized_items['신발'])
            
            # 액세서리 추가 (60% 확률)
            if categorized_items['액세서리'] and random.random() < 0.6:
                outfit['액세서리'] = random.choice(categorized_items['액세서리'])
            
            # 최소 2개 이상의 아이템으로 구성
            if len(outfit) >= 2:
                # 코디 데이터 구성
                outfit_data = {}
                for category, item in outfit.items():
                    outfit_data[category] = {
                        'name': item['name'],
                        'brand': '',
                        'price': 0,
                        'image_url': item['image_path'],
                        'id': item['id'],
                        'tags': item['tags']
                    }
                
                # 코디 컬러 조합 추출
                outfit_colors = []
                for item in outfit.values():
                    for tag in item['tags']:
                        if tag in ["검정", "흰색", "회색", "베이지", "빨강", "파랑", "초록", 
                                 "노랑", "보라", "핑크", "갈색", "주황"]:
                            outfit_colors.append(tag)
                            break
                
                # 베이스 컬러 설정
                if outfit_colors:
                    # 가장 많이 사용된 색상을 베이스로
                    from collections import Counter
                    color_counts = Counter(outfit_colors)
                    base_color = color_counts.most_common(1)[0][0]
                
                # DB에 저장
                outfit_id = db.save_outfit(style, season, base_color, outfit_data)
                if outfit_id:
                    created_count += 1
                    print(f"코디 #{i+1} 생성: {style} / {season} / {base_color} (구성: {', '.join(outfit_data.keys())})")
        
        except Exception as e:
            print(f"코디 #{i+1} 생성 중 오류: {e}")
    
    print(f"코디 생성 완료: {created_count}개 생성됨")
    return created_count

if __name__ == "__main__":
    # 메뉴 출력
    print("=== 무신사 데이터 학습 강화 시스템 ===")
    print("1. 추가 데이터 수집")
    print("2. 기존 태그 품질 향상")
    print("3. 고급 코디 생성")
    print("4. 전체 작업 실행")
    print("5. 종료")
    
    choice = input("실행할 작업을 선택하세요 (1-5): ")
    
    if choice == '1':
        pages = int(input("수집할 페이지 수 (기본 5): ") or 5)
        collected = crawl_more_musinsa_data(pages=pages)
        print(f"총 {collected}개 아이템 수집 완료")
    
    elif choice == '2':
        updated = enrich_existing_tags()
        print(f"총 {updated}개 아이템 태그 개선 완료")
    
    elif choice == '3':
        count = int(input("생성할 코디 수 (기본 30): ") or 30)
        created = generate_enhanced_outfits(count=count)
        print(f"총 {created}개 코디 생성 완료")
    
    elif choice == '4':
        print("\n=== 전체 작업 시작 ===")
        collected = crawl_more_musinsa_data(pages=3)
        print(f"수집 완료: {collected}개 아이템")
        
        updated = enrich_existing_tags()
        print(f"태그 개선 완료: {updated}개 아이템")
        
        created = generate_enhanced_outfits(count=30)
        print(f"코디 생성 완료: {created}개")
        
        print("\n=== 모든 작업 완료 ===")
    
    else:
        print("프로그램을 종료합니다.")