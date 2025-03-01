import requests
import pandas as pd

def crawl_musinsa_ranking_api():
    # 무신사 랭킹 API (현재 'musinsa' 스토어)
    ranking_api_url = "https://api.musinsa.com/api2/hm/v4/pans/ranking?storeCode=musinsa"
    headers = {'User-Agent': 'Mozilla/5.0'}

    response = requests.get(ranking_api_url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        # json_data 내부 구조 확인
        # 실제 아이템들이 어디에 있는지 살펴봐야 함
        # 예: json_data.get("data", []) 로 리스트를 얻을 수도 있고,
        #     "goods" 키 아래 들어있을 수도 있음.

        # 여기서는 단순히 data 필드만 DataFrame으로 변환해보는 예시
        data = json_data.get("data", [])
        if data:
            df = pd.DataFrame(data)
            df.to_csv("musinsa_ranking_api.csv", index=False, encoding="utf-8-sig")
            print("무신사 랭킹 데이터를 musinsa_ranking_api.csv 파일로 저장했습니다.")
        else:
            print("JSON 내에 'data' 필드가 비어있습니다.")
    else:
        print("랭킹 API 호출 실패, 상태코드:", response.status_code)

if __name__ == "__main__":
    crawl_musinsa_ranking_api()
