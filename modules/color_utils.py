# modules/color_utils.py
import streamlit as st
from colorthief import ColorThief
from modules.constants import COLOR_MAP
from typing import Tuple, List

def find_closest_color(rgb: Tuple[int, int, int]) -> str:
    """RGB 값을 기반으로 가장 가까운 색상 이름 찾기"""
    min_distance = float('inf')
    closest_color = None
    for color_name, color_rgb in COLOR_MAP.items():
        distance = sum([(a - b) ** 2 for a, b in zip(rgb, color_rgb)])
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name
    return closest_color

def extract_colors(image_path: str, color_count: int = 3) -> Tuple[List[Tuple[int,int,int]], List[str]]:
    """이미지에서 색상 팔레트를 추출하고, 각 색상에 가장 가까운 COLOR_MAP 색상 이름을 반환"""
    try:
        color_thief = ColorThief(image_path)
        palette = color_thief.get_palette(color_count=color_count)
        color_names = [find_closest_color(rgb) for rgb in palette]
        return palette, color_names
    except Exception as e:
        st.error(f"색상 추출 중 오류가 발생했습니다: {e}")
        return [], []

def color_harmony_check(main_color: str, sub_color: str) -> bool:
    """두 색상이 조화로운지 판단"""
    compatible_colors = {
        '검정': ['흰색', '회색', '빨강', '파랑', '초록', '노랑', '보라', '핑크', '주황', '갈색', '베이지'],
        '흰색': ['검정', '회색', '빨강', '파랑', '초록', '노랑', '보라', '핑크', '주황', '갈색'],
        '회색': ['검정', '흰색', '빨강', '파랑', '초록', '보라', '핑크'],
        '빨강': ['검정', '흰색', '회색', '베이지'],
        '파랑': ['검정', '흰색', '회색', '베이지'],
        '초록': ['검정', '흰색', '회색', '베이지'],
        '노랑': ['검정', '회색', '보라'],
        '보라': ['검정', '흰색', '회색', '노랑', '베이지'],
        '핑크': ['검정', '흰색', '회색', '베이지'],
        '주황': ['검정', '회색', '파랑'],
        '갈색': ['검정', '흰색', '베이지'],
        '베이지': ['검정', '빨강', '파랑', '초록', '보라', '핑크', '갈색']
    }
    if not main_color or not sub_color:
        return True
    if main_color in compatible_colors and sub_color in compatible_colors[main_color]:
        return True
    return False

def seasonal_recommendation(outfit: dict, season: str) -> bool:
    """코디 데이터에 계절에 맞는 아이템이 포함되어 있는지 확인"""
    season_mapping = {
        '봄': ['얇은 자켓', '셔츠', '맨투맨', '데님', '치노'],
        '여름': ['반팔', '반바지', '린넨', '샌들', '슬리퍼'],
        '가을': ['가디건', '맨투맨', '후드', '청자켓', '트렌치코트'],
        '겨울': ['패딩', '코트', '니트', '목도리', '부츠']
    }
    if season not in season_mapping:
        season = '봄'
    seasonal_keywords = season_mapping[season]
    for category, item in outfit.items():
        if 'name' in item:
            for keyword in seasonal_keywords:
                if keyword in str(item['name']).lower():
                    return True
    return False
