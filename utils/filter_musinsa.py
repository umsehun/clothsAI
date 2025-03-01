import json
import pandas as pd

# 1. JSON 파일 로드 (파일명: data.json)
with open("data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

# 2. JSON 데이터가 리스트 형태라고 가정
# 예: json_data = [ {...}, {...}, ... ]
if not isinstance(json_data, list):
    print("JSON 데이터 형식이 리스트가 아닙니다.")
    exit()

# 3. "무신사"가 포함된 항목 필터링 (예: "name" 필드에 "무신사"가 있는 경우)
filtered = [item for item in json_data if "무신사" in item.get("name", "")]

# 4. 결과를 DataFrame으로 변환 후 CSV 저장
if filtered:
    df = pd.DataFrame(filtered)
    # CSV 파일로 저장 (UTF-8-SIG 인코딩으로 한글 깨짐 방지)
    output_file = "musinsa_only.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"필터링된 데이터를 {output_file} 파일로 저장했습니다.")
else:
    print("필터링된 '무신사' 데이터가 없습니다.")
