# modules/data_loader.py
import os
import json
import pandas as pd

def load_fashion_data():
    """무신사 데이터 로드 함수"""
    try:
        try:
            ranking_df = pd.read_csv("musinsa_ranking_api.csv", encoding="utf-8-sig")
            print(f"랭킹 데이터 로드 완료: {len(ranking_df)} 항목")
        except Exception as e:
            print(f"랭킹 데이터 로드 실패: {e}")
            ranking_df = pd.DataFrame()
        
        try:
            with open("musinsa_detailed.json", "r", encoding="utf-8") as f:
                detailed_data = json.load(f)
                if isinstance(detailed_data, dict) and "data" in detailed_data:
                    detailed_list = detailed_data["data"]
                elif isinstance(detailed_data, list):
                    detailed_list = detailed_data
                else:
                    detailed_list = []
                    for key, item in detailed_data.items():
                        if isinstance(item, dict):
                            item['id'] = key
                            detailed_list.append(item)
                detailed_df = pd.DataFrame(detailed_list)
                print(f"상세 데이터 로드 완료: {len(detailed_df)} 항목")
                if not ranking_df.empty and not detailed_df.empty:
                    if "id" in ranking_df.columns and "id" in detailed_df.columns:
                        merged_df = pd.merge(ranking_df, detailed_df, on="id", how="outer", suffixes=("_rank", "_detail"))
                        return merged_df
            return ranking_df if not ranking_df.empty else detailed_df
        except Exception as e:
            print(f"JSON 로드 실패: {e}. 랭킹 데이터만 사용합니다.")
            return ranking_df if not ranking_df.empty else pd.DataFrame()
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

def categorize_fashion_items(df):
    """패션 아이템을 상세 카테고리로 분류"""
    categories = {
        '상의': ['티셔츠', '니트', '셔츠', '맨투맨', '후드', '블라우스', '탑', '스웨터', '폴로', '크롭티'],
        '하의': ['팬츠', '진', '청바지', '슬랙스', '스커트', '쇼츠', '레깅스', '조거', '트랙팬츠', '카고팬츠', '와이드팬츠', '데님'],
        '아우터': ['자켓', '코트', '패딩', '집업', '점퍼', '가디건', '베스트', '플리스', '파카', '무스탕', '트렌치코트', '블레이저'],
        '원피스': ['원피스', '드레스', '점프수트', '롬퍼'],
        '신발': ['스니커즈', '구두', '로퍼', '슬리퍼', '샌들', '힐', '부츠', '워커', '러닝화', '슬립온', '운동화', '첼시부츠'],
        '액세서리': ['모자', '가방', '벨트', '양말', '주얼리', '팔찌', '목걸이', '귀걸이', '반지', '백팩', '크로스백', '토트백', '지갑']
    }
    
    def classify_item(row):
        if 'productName' in row and pd.notna(row['productName']):
            name = str(row['productName']).lower()
            for category, keywords in categories.items():
                for keyword in keywords:
                    if keyword.lower() in name:
                        return category
            if 'brandName' in row and pd.notna(row['brandName']):
                brand = str(row['brandName']).lower()
                footwear_brands = ['나이키', '아디다스', '컨버스', '반스', '뉴발란스', '푸마']
                accessory_brands = ['제이에스티나', '스와로브스키', '판도라']
                for b in footwear_brands:
                    if b.lower() in brand:
                        return '신발'
                for b in accessory_brands:
                    if b.lower() in brand:
                        return '액세서리'
        return '기타'
    
    df['category'] = df.apply(classify_item, axis=1)
    return df

def extract_item_color(df):
    """상품명이나 이미지에서 색상 정보 추출"""
    colors = {
        '검정': ['검정', '블랙', 'black'],
        '흰색': ['흰색', '화이트', '화잇', 'white'],
        '회색': ['회색', '그레이', 'gray', 'grey'],
        '빨강': ['빨강', '레드', 'red'],
        '파랑': ['파랑', '블루', 'blue'],
        '초록': ['초록', '그린', 'green'],
        '노랑': ['노랑', '옐로우', 'yellow'],
        '보라': ['보라', '퍼플', 'purple'],
        '핑크': ['핑크', '분홍', 'pink'],
        '주황': ['주황', '오렌지', 'orange'],
        '갈색': ['갈색', '브라운', 'brown'],
        '베이지': ['베이지', 'beige']
    }
    
    def find_color(name):
        if pd.isna(name):
            return None
        name = str(name).lower()
        for color, keywords in colors.items():
            for keyword in keywords:
                if keyword in name:
                    return color
        return None
    
    name_col = None
    for col in ['productName', '제품명', 'name']:
        if col in df.columns:
            name_col = col
            break
    if name_col:
        df['color'] = df[name_col].apply(find_color)
    else:
        df['color'] = None
    return df