import pandas as pd
import json

# CSV 파일 확인
print("==== CSV 파일 구조 확인 ====")
try:
    df = pd.read_csv("musinsa_ranking_api.csv", encoding='utf-8-sig')
    print(f"CSV 컬럼: {df.columns.tolist()}")
    print(f"CSV 샘플 (첫 번째 행):")
    print(df.iloc[0])
except Exception as e:
    print(f"CSV 파일 읽기 오류: {e}")

# JSON 파일 확인
print("\n==== JSON 파일 구조 확인 ====")
try:
    with open("musinsa_detailed.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"JSON 최상위 타입: {type(data)}")
    
    if isinstance(data, dict):
        print(f"최상위 키: {list(data.keys())}")
        # 첫 번째 키의 값 확인
        first_key = list(data.keys())[0]
        first_value = data[first_key]
        print(f"첫 번째 키의 값 타입: {type(first_value)}")
        
        # 값이 리스트인 경우 첫 번째 항목 확인
        if isinstance(first_value, list) and len(first_value) > 0:
            print(f"첫 번째 항목 타입: {type(first_value[0])}")
            print("첫 번째 항목 샘플:", json.dumps(first_value[0], ensure_ascii=False)[:200] + "...")
        # 값이 딕셔너리인 경우 키 확인
        elif isinstance(first_value, dict):
            print(f"하위 키: {list(first_value.keys())}")
except Exception as e:
    print(f"JSON 파일 읽기 오류: {e}")