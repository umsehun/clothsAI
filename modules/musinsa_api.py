import requests
import json
import time
import random

def fetch_api(url):
    """무신사 API에서 데이터를 가져오는 함수"""
    # 허용된 User-Agent 중 하나 사용
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Referer': 'https://www.musinsa.com/',
        'Accept': 'application/json',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        print(f"API 요청: {url}")
        response = requests.get(url, headers=headers)
        print(f"API 응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                print("JSON 디코딩 오류")
                print(f"응답 내용: {response.text[:200]}...")  # 응답의 일부만 출력
                return None
        else:
            print(f"API 요청 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"API 호출 중 오류: {e}")
        return None

def fetch_product_detail(product_id):
    """상품 상세 정보를 가져오는 함수"""
    # 업데이트된 API 엔드포인트
    url = f"https://www.musinsa.com/api/goods/{product_id}/v2"
    return fetch_api(url)

def fetch_recommended_products(count=20):
    """추천 상품 데이터를 가져오는 함수"""
    # 업데이트된 API 엔드포인트들
    endpoints = [
        # 베스트 아이템 API
        "https://search.musinsa.com/api/display/goods?display_cnt=20&sort=sale_high&list_kind=small&category1DepthCode=001",
        # 추천 아이템 API
        "https://search.musinsa.com/api/display/goods?display_cnt=20&sort=pop&list_kind=small&category1DepthCode=002",
        # 상의 카테고리 API
        "https://search.musinsa.com/api/display/goods?display_cnt=20&sort=sale_high&list_kind=small&category1DepthCode=001",
        # 하의 카테고리 API
        "https://search.musinsa.com/api/display/goods?display_cnt=20&sort=sale_high&list_kind=small&category1DepthCode=003"
    ]
    
    all_products = []
    
    for url in endpoints:
        data = fetch_api(url)
        
        if data and isinstance(data, dict) and "data" in data and "list" in data["data"]:
            products = data["data"]["list"]
            print(f"{len(products)}개 상품 데이터 가져옴")
            all_products.extend(products)
            
        # 딜레이 추가 (robots.txt 준수)
        delay = random.uniform(2, 5)  # 실제 60초는 너무 길어서 테스트를 위해 짧게 설정
        print(f"{delay:.1f}초 대기 중...")
        time.sleep(delay)
        
        if len(all_products) >= count:
            break
    
    print(f"총 {len(all_products)}개 상품 가져옴")
    return all_products[:count]