from fashion_db import FashionDB
import json

db = FashionDB()

# 모든 코디 조회
outfits = db.get_all_outfits()
print(f"저장된 코디 수: {len(outfits)}")

# 첫 번째 코디 상세 정보 출력
if outfits:
    first_outfit = outfits[0]
    outfit_id, style, season, base_color, outfit_json, created_at = first_outfit
    
    print(f"코디 ID: {outfit_id}")
    print(f"스타일: {style}")
    print(f"계절: {season}")
    print(f"기본 색상: {base_color}")
    print(f"생성 날짜: {created_at}")
    
    # 코디 구성 아이템
    outfit_data = json.loads(outfit_json)
    print("\n코디 구성:")
    for category, item in outfit_data.items():
        print(f"- {category}: {item['name']} (이미지: {item['image_url']})")