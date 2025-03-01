# modules/outfit_generator.py
import streamlit as st
import random
import datetime
from modules.data_loader import load_fashion_data, categorize_fashion_items, extract_item_color
from modules.recommendation import generate_outfit
from fashion_db import FashionDB

db = FashionDB()

def generate_multiple_outfits(count: int = 50) -> int:
    """무신사 데이터를 활용한 다수의 샘플 코디 자동 생성 함수"""
    fashion_data = load_fashion_data()
    if fashion_data.empty:
        st.error("패션 데이터를 불러올 수 없습니다.")
        return 0
    fashion_data = categorize_fashion_items(fashion_data)
    fashion_data = extract_item_color(fashion_data)
    created_count = 0
    progress_bar = st.progress(0)
    status_text = st.empty()
    style_weights = {
        "미니멀룩": 0.3, "스트릿패션": 0.2, "보헤미안룩": 0.05,
        "럭셔리룩": 0.1, "아방가르드룩": 0.05, "러블리룩": 0.05,
        "빈티지룩": 0.1, "스포티룩": 0.15, "모던룩": 0.2,
        "그런지룩": 0.05, "프레피룩": 0.05
    }
    season_weights = {"봄": 0.1, "여름": 0.1, "가을": 0.1, "겨울": 0.1}
    current_month = datetime.datetime.now().month
    if 3 <= current_month <= 5:
        season_weights["봄"] = 0.7
    elif 6 <= current_month <= 8:
        season_weights["여름"] = 0.7
    elif 9 <= current_month <= 11:
        season_weights["가을"] = 0.7
    else:
        season_weights["겨울"] = 0.7
    basic_colors = ["검정", "흰색", "회색", "베이지", None]
    vibrant_colors = ["빨강", "파랑", "초록", "노랑", "보라", "핑크"]
    color_options = basic_colors + vibrant_colors
    color_weights = [0.15, 0.15, 0.1, 0.1, 0.1] + [0.05] * len(vibrant_colors)
    for i in range(count):
        try:
            style = random.choices(list(style_weights.keys()), weights=list(style_weights.values()), k=1)[0]
            season = random.choices(list(season_weights.keys()), weights=list(season_weights.values()), k=1)[0]
            color = random.choices(color_options, weights=color_weights, k=1)[0]
            outfit = generate_outfit(fashion_data, style=style, base_color=color)
            if outfit and len(outfit) >= 2:
                outfit_id = db.save_outfit(style, season, color, outfit)
                if outfit_id:
                    created_count += 1
                    status_text.text(f"{i+1}/{count} 생성 중... 성공: {created_count}")
            progress_bar.progress((i + 1) / count)
        except Exception as e:
            print(f"코디 생성 오류: {e}")
            continue
    return created_count
