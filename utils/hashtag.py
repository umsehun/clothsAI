import requests
import json
import re

# --- Step 1: (예시) 무신사 상품 데이터 ---
# 실제 크롤링 코드를 통해 CSV/JSON으로 저장한 데이터를 로드하는 방식으로 대체할 수 있음.
musinsa_products = [
    {
        "id": "4421493",
        "brand": "디미트리블랙",
        "product": "에센셜 헤어리 스트라이프 라운드 니트_그레이 #패션 #트렌드",
        "image_url": "https://image.msscdn.net/images/goods_img/20240909/4421493/4421493_17268233006136_500.jpg"
    },
    {
        "id": "1234567",
        "brand": "브랜드A",
        "product": "심플 캐주얼 후드티 #심플 #캐주얼",
        "image_url": "https://example.com/image_1234567.jpg"
    }
]

# --- Step 2: 해시태그 추출 함수 ---
def extract_hashtags(text):
    """
    상품 설명에서 #기호 뒤의 단어를 추출 (예: "#패션" → "패션")
    """
    return re.findall(r"#(\w+)", text)

# --- Step 3: Hashscraper API 호출 함수 ---
api_key = '8e1ee1befba5d21f1f512e7a40fbb89a'  # 본인의 API 키로 변경하세요.
hashscraper_url = 'http://api.hashscraper.com/api/get_schedules'
hashscraper_headers = {
    'Content-Type': 'application/json; version=2'
}

def get_hashtag_schedule(hashtag, page='1'):
    """
    주어진 해시태그에 대해 Hashscraper API를 호출하여 스케줄 정보를 반환
    """
    data = {
      'api_key': api_key,
      'page': page,
      'hashtag': hashtag
    }
    try:
        response = requests.post(hashscraper_url, headers=hashscraper_headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"해시태그 #{hashtag} 조회 오류: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"해시태그 #{hashtag} 조회 중 예외 발생: {e}")
        return None

# --- Step 4: 각 상품 데이터 처리 및 해시태그 기반 추가 정보 조회 ---
for product in musinsa_products:
    print("상품명:", product["product"])
    hashtags = extract_hashtags(product["product"])
    print("추출된 해시태그:", hashtags)
    for tag in hashtags:
        schedule_info = get_hashtag_schedule(tag)
        print(f"#{tag} 스케줄 정보:")
        if schedule_info:
            print(json.dumps(schedule_info, ensure_ascii=False, indent=2))
        else:
            print("정보 없음")
    print("-" * 40)
