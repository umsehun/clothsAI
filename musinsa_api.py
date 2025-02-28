import requests
import json

# 무신사 API 엔드포인트 설정
store_api = {
    "musinsa": {
        "추천": "https://api.musinsa.com/api2/hm/v4/pans/recommend?storeCode=musinsa",
        "랭킹": "https://api.musinsa.com/api2/hm/v4/pans/ranking?storeCode=musinsa",
        "세일": "https://api.musinsa.com/api2/hm/v2/pans/sale?storeCode=musinsa",
        "브랜드": "https://api.musinsa.com/api2/hm/v3/pans/brand?storeCode=musinsa",
        "신상": "https://api.musinsa.com/api2/hm/v1/pans/release?storeCode=musinsa"
    }
}

# 상품 데이터를 찾을 수 있는 키 목록
PRODUCT_KEYS = ["items", "products", "list", "goods"]

# 스타일 리스트
STYLE_OPTIONS = ["캐주얼", "미니멀", "스포티", "워크웨어", "시크",
                 "고프코어", "프레피", "에스닉", "스트릿", "걸리시",
                 "클래식", "로맨틱", "시티보이", "레트로", "리조트"]

# API 호출 함수
def fetch_api(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)

        # 응답이 JSON이 아니라면 오류 처리
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API 호출 실패: {url} (상태: {response.status_code})")
            return None
    except Exception as e:
        print(f"❌ 오류 발생: {e} - {url}")
        return None

# 데이터 수집 및 저장
final_data = {}

for store, pans in store_api.items():
    final_data[store] = {}
    for pan_type, api_url in pans.items():
        print(f"🔍 가져오는 중: {store} - {pan_type} ({api_url})")
        data = fetch_api(api_url)

        # API 응답이 딕셔너리인지 확인
        if isinstance(data, dict) and "data" in data and "modules" in data["data"]:
            modules = data["data"]["modules"]
        else:
            print(f"⚠️ API 응답이 예상과 다름 (modules 없음): {data}")
            modules = []

        # 상품 데이터 저장 리스트
        product_items = []

        # 🔹 modules에서 상품 데이터가 포함된 부분 탐색
        for module in modules:
            for key in PRODUCT_KEYS:
                if key in module and isinstance(module[key], list):
                    product_items.extend(module[key])  # 상품 리스트 추가

        # 상품이 없는 경우 경고 메시지 출력
        if not product_items:
            print(f"⚠️ {pan_type}에서 상품 데이터를 찾을 수 없음!")

        # 🔹 상품 데이터에 스타일 추가
        processed_items = []
        for item in product_items:
            try:
                item_id = int(item.get("id", 0))  # ID가 없거나 문자열이면 0으로 설정
                item["style"] = STYLE_OPTIONS[item_id % len(STYLE_OPTIONS)]  # 스타일 추가

                # 이미지 URL 추가
                item["image_url"] = item.get("image", "이미지 없음")

                # 최종 리스트에 추가
                processed_items.append(item)

            except Exception as e:
                print(f"⚠️ 데이터 처리 오류: {e}, item 데이터: {item}")

        # 최종 데이터 저장
        final_data[store][pan_type] = processed_items

# 🔹 JSON 파일 저장
with open("musinsa_detailed.json", "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)

print("✅ 무신사 데이터를 musinsa_detailed.json 파일에 저장했습니다.")
