# 최상단에 streamlit import 추가
import streamlit as st
import os
import numpy as np
import pandas as pd
import json
import pickle
import tensorflow
from PIL import Image
import re
from tensorflow.keras.preprocessing import image
from tensorflow.keras.layers import GlobalMaxPooling2D
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from numpy.linalg import norm
from colorthief import ColorThief
import matplotlib.pyplot as plt
from gtts import gTTS
from numpy.linalg import norm
from colorthief import ColorThief
import matplotlib.pyplot as plt
from gtts import gTTS
from tempfile import NamedTemporaryFile
from tempfile import NamedTemporaryFile
import sqlite3
import sqlite3

from fashion_db import FashionDB  # fashion_db.py 파일 필요




# DB 인스턴스 생성
db = FashionDB()

# 기존 save_tags 함수를 DB 사용 버전으로 수정
def save_tags(image_path, tags):
    """태그를 저장하는 함수 (DB 사용)"""
    # 기존 파일 저장 방식 유지
    if not os.path.exists('saved_tags'):
        os.makedirs('saved_tags')
    
    filename = os.path.basename(image_path)
    base_name = os.path.splitext(filename)[0]
    json_path = f'saved_tags/{base_name}_tags.json'
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'image': filename, 'tags': tags}, f, ensure_ascii=False)
    
    # DB에도 저장
    tag_id = db.save_tags(image_path, tags)
    
    return json_path

# 색상 이름과 RGB 값 매핑
COLOR_MAP = {
    "빨강": [255, 0, 0],
    "주황": [255, 165, 0],
    "노랑": [255, 255, 0],
    "연두": [178, 255, 102],
    "초록": [0, 128, 0],
    "민트": [170, 240, 209],
    "파랑": [0, 0, 255],
    "남색": [0, 0, 128],
    "보라": [128, 0, 128],
    "핑크": [255, 192, 203],
    "갈색": [165, 42, 42],
    "베이지": [245, 245, 220],
    "흰색": [255, 255, 255],
    "회색": [128, 128, 128],
    "검정": [0, 0, 0]
}

# 상단 전역 변수 영역에 스타일 옵션 추가
STYLE_OPTIONS = [
    "미니멀룩", 
    "스트릿패션", 
    "보헤미안룩", 
    "럭셔리룩", 
    "아방가르드룩", 
    "러블리룩", 
    "빈티지룩", 
    "스포티룩", 
    "모던룩", 
    "그런지룩",
    "프레피룩"
]

# AI 코디 추천 관련 함수들
def load_fashion_data():
    """무신사 데이터 로드 함수"""
    try:
        # 랭킹 데이터 로드
        try:
            ranking_df = pd.read_csv("musinsa_ranking_api.csv", encoding="utf-8-sig")
            print(f"랭킹 데이터 로드 완료: {len(ranking_df)} 항목")
        except Exception as e:
            print(f"랭킹 데이터 로드 실패: {e}")
            ranking_df = pd.DataFrame()
        
        # JSON 파일 로드 (상세 데이터)
        try:
            with open("musinsa_detailed.json", "r", encoding="utf-8") as f:
                detailed_data = json.load(f)
                
                # 데이터 구조 확인 및 파싱
                if isinstance(detailed_data, dict) and "data" in detailed_data:
                    detailed_list = detailed_data["data"]
                elif isinstance(detailed_data, list):
                    detailed_list = detailed_data
                else:
                    # 맵핑된 형태로 변환 시도
                    detailed_list = []
                    for key, item in detailed_data.items():
                        if isinstance(item, dict):
                            item['id'] = key
                            detailed_list.append(item)
                
                detailed_df = pd.DataFrame(detailed_list)
                print(f"상세 데이터 로드 완료: {len(detailed_df)} 항목")
                
                # 두 데이터프레임 병합
                if not ranking_df.empty and not detailed_df.empty:
                    if "id" in ranking_df.columns and "id" in detailed_df.columns:
                        merged_df = pd.merge(ranking_df, detailed_df, on="id", how="outer", suffixes=("_rank", "_detail"))
                        return merged_df
            
            # 병합 실패한 경우 랭킹 데이터만 반환
            return ranking_df if not ranking_df.empty else detailed_df
            
        except Exception as e:
            print(f"JSON 로드 실패: {e}. 랭킹 데이터만 사용합니다.")
            return ranking_df if not ranking_df.empty else pd.DataFrame()
            
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

def categorize_fashion_items(df):
    """패션 아이템을 상세 카테고리로 분류"""
    # 확장된 제품 카테고리 사전
    categories = {
        '상의': ['티셔츠', '니트', '셔츠', '맨투맨', '후드', '블라우스', '탑', '스웨터', '폴로', '크롭티'],
        '하의': ['팬츠', '진', '청바지', '슬랙스', '스커트', '쇼츠', '레깅스', '조거', '트랙팬츠', '카고팬츠', '와이드팬츠', '데님'],
        '아우터': ['자켓', '코트', '패딩', '집업', '점퍼', '가디건', '베스트', '플리스', '파카', '무스탕', '트렌치코트', '블레이저'],
        '원피스': ['원피스', '드레스', '점프수트', '롬퍼'],
        '신발': ['스니커즈', '구두', '로퍼', '슬리퍼', '샌들', '힐', '부츠', '워커', '러닝화', '슬립온', '운동화', '첼시부츠'],
        '액세서리': ['모자', '가방', '벨트', '양말', '주얼리', '팔찌', '목걸이', '귀걸이', '반지', '백팩', '크로스백', '토트백', '지갑']
    }
    
    # 제품명 기준으로 카테고리 분류
    def classify_item(row):
        if 'productName' in row and pd.notna(row['productName']):
            name = str(row['productName']).lower()
            
            # 카테고리 키워드 매칭
            for category, keywords in categories.items():
                for keyword in keywords:
                    if keyword.lower() in name:
                        return category
            
            # 브랜드별 주력 카테고리 (일부 브랜드 예시)
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
    
    # 카테고리 컬럼 추가
    df['category'] = df.apply(classify_item, axis=1)
    
    return df

def extract_item_color(df):
    """상품명이나 이미지에서 색상 정보 추출"""
    # 색상 키워드
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
    
    # 제품명에서 색상 추출
    def find_color(name):
        if pd.isna(name):
            return None
        
        name = str(name).lower()
        for color, keywords in colors.items():
            for keyword in keywords:
                if keyword in name:
                    return color
        return None
    
    # 제품명 컬럼 찾기
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

def generate_outfit(fashion_df, style=None, base_color=None):
    """스타일과 색상을 기반으로 코디 생성"""
    if fashion_df.empty:
        return {}
    
    # 카테고리별 필터링
    categorized_df = categorize_fashion_items(fashion_df)
    
    # 색상 추출
    color_df = extract_item_color(categorized_df)
    
    # 색상 필터링 (지정된 경우)
    if base_color:
        # 색상 정보가 없는 경우 제외하지 않음
        filtered_df = color_df[(color_df['color'] == base_color) | (color_df['color'].isna())]
        if filtered_df.empty:
            filtered_df = color_df  # 결과가 없으면 원래 데이터 사용
    else:
        filtered_df = color_df
    
    # 필터링된 데이터가 없으면 빈 결과 반환
    if filtered_df.empty:
        return {}
        
    # 카테고리별로 상품 선택
    outfit = {}
    categories = ['상의', '하의', '아우터', '신발', '액세서리']
    
    # 최소 2개 카테고리 이상 있는지 확인하기 위한 변수
    found_categories = 0
    
    for category in categories:
        category_items = filtered_df[filtered_df['category'] == category]
        if not category_items.empty:
            found_categories += 1
            # 랜덤으로 아이템 선택
            selected_item = category_items.sample(1).iloc[0]
            
            # 이미지 URL 찾기
            img_url = None
            for url_col in ['url', 'image_url', 'imageUrl']:
                if url_col in selected_item and pd.notna(selected_item[url_col]):
                    img_url = selected_item[url_col]
                    break
            
            # 이미지 URL이 딕셔너리인 경우 처리
            if isinstance(selected_item.get('image'), dict):
                img_url = selected_item['image'].get('url')
            
            # 상품명 찾기
            name = None
            for name_col in ['productName', '제품명', 'name']:
                if name_col in selected_item and pd.notna(selected_item[name_col]):
                    name = selected_item[name_col]
                    break
            
            # 브랜드명 찾기
            brand = None
            for brand_col in ['brandName', '브랜드', 'brand']:
                if brand_col in selected_item and pd.notna(selected_item[brand_col]):
                    brand = selected_item[brand_col]
                    break
            
            # 가격 찾기
            price = None
            for price_col in ['finalPrice', '가격', 'price']:
                if price_col in selected_item and pd.notna(selected_item[price_col]):
                    price = selected_item[price_col]
                    break
            
            outfit[category] = {
                'name': name,
                'brand': brand,
                'price': price,
                'image_url': img_url,
                'id': selected_item.get('id')
            }

    # 최소 2개 카테고리 이상 없으면 빈 결과 반환
    if found_categories < 2:
        return {}
        
    return outfit

def display_outfit(outfit):
    """코디 결과 표시"""
    if not outfit:
        st.warning("코디를 생성할 수 있는 충분한 데이터가 없습니다.")
        return
    
    st.subheader("🎨 AI가 추천하는 코디")
    total_price = 0
    
    # 카테고리별로 정렬된 순서로 표시
    category_order = ['상의', '하의', '아우터', '원피스', '신발', '액세서리']
    outfit_items = []
    
    for category in category_order:
        if category in outfit:
            outfit_items.append((category, outfit[category]))
    
    # 항목들을 3개씩 행으로 표시
    for i in range(0, len(outfit_items), 3):
        cols = st.columns(3)
        for j, (category, item) in enumerate(outfit_items[i:i+3]):
            with cols[j]:
                st.subheader(f"👕 {category}")
                st.write(f"**{item['name']}**")
                st.write(f"브랜드: {item['brand']}")
                
                if 'price' in item and item['price']:
                    try:
                        price = int(item['price'])
                        st.write(f"가격: {price:,}원")
                        total_price += price
                    except:
                        st.write(f"가격: {item['price']}")
                
                if item['image_url']:
                    try:
                        st.image(item['image_url'], use_container_width=True)
                    except:
                        st.write("이미지를 불러올 수 없습니다.")
                else:
                    st.write("이미지 없음")
    
    st.subheader(f"총 예상 가격: {total_price:,}원")

def color_harmony_check(main_color, sub_color):
    """색상 조화 체크 함수"""
    # 색상 조합 호환성 매핑
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
    
    # 색상 정보가 없으면 호환된다고 간주
    if not main_color or not sub_color:
        return True
    
    if main_color in compatible_colors and sub_color in compatible_colors[main_color]:
        return True
    
    return False

def seasonal_recommendation(outfit, season):
    """계절에 맞는 코디 추천 함수"""
    season_mapping = {
        '봄': ['얇은 자켓', '셔츠', '맨투맨', '데님', '치노'],
        '여름': ['반팔', '반바지', '린넨', '샌들', '슬리퍼'],
        '가을': ['가디건', '맨투맨', '후드', '청자켓', '트렌치코트'],
        '겨울': ['패딩', '코트', '니트', '목도리', '부츠']
    }
    
    # 현재 계절의 키워드
    if season not in season_mapping:
        season = '봄'  # 기본값
    
    seasonal_keywords = season_mapping[season]
    
    # 코디 아이템에 계절 키워드가 있는지 체크
    for category, item in outfit.items():
        if 'name' in item:
            for keyword in seasonal_keywords:
                if keyword in str(item['name']).lower():
                    return True
    
    return False

# RGB 값을 기반으로 가장 가까운 색상 이름 찾기
def find_closest_color(rgb):
    min_distance = float('inf')
    closest_color = None
    for color_name, color_rgb in COLOR_MAP.items():
        distance = sum([(a - b) ** 2 for a, b in zip(rgb, color_rgb)])
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name
    return closest_color

# 색상 추출 함수
def extract_colors(image_path, color_count=3):
    try:
        color_thief = ColorThief(image_path)
        palette = color_thief.get_palette(color_count=color_count)
        # RGB 값을 색상 이름으로 변환
        color_names = [find_closest_color(rgb) for rgb in palette]
        return palette, color_names
    except Exception as e:
        st.error(f"색상 추출 중 오류가 발생했습니다: {e}")
        return [], []

# 모델 로드 부분을 더 강화된 예외 처리로 수정
try:
    # 모델과 데이터 로드
    if os.path.exists('features_list_for_prods.pkl'):
        feature_list = np.array(pickle.load(open('features_list_for_prods.pkl', 'rb')))
    else:
        feature_list = np.array([])
        
    if os.path.exists('filenames_products.pkl'):
        filenames = pickle.load(open('filenames_products.pkl', 'rb'))
    else:
        filenames = []

    # ResNet50 모델 로드
    model = ResNet50(weights='imagenet', include_top=False, input_shape=(244, 244, 3))
    model.trainable = False
    model = tensorflow.keras.Sequential([
        model,
        GlobalMaxPooling2D()
    ])
    print("모델 로드 완료!")
except Exception as e:
    st.error(f"모델 로드 중 오류가 발생했습니다: {str(e)}")
    # 오류 처리를 위한 빈 모델 설정
    model = None
    feature_list = np.array([])
    filenames = []
    print(f"모델 로드 오류: {str(e)}")


st.title('FashionGPT')

# 문자열 배열 수정
quotes = [
    "We are thrilled with the accuracy and personal touch this fashion recommendation engine brings to our business. It's a game changer! — Crunch Restaurant",
    "The ease with which we are now able to match products with customer's preferences is revolutionary! This tool is saving us time and helping us increase sales. — Ajio",
    "Customer personalization is the future of retail. This fashion recommendation engine is leading the way with its sophisticated yet user-friendly features. — Crunch Restaurant",
    "The recommendations have truly transformed the way we interact with our customers. We're noticing higher customer satisfaction and return rates. — Ajio",
    "It's an innovative tool that delivers exactly what it promises - precise fashion recommendations tailored to individual tastes. Our customers love it. — Nike, South Delhi",
    "Fashion retail will never be the same again. This engine has provided an enhanced shopping experience for our customers. — H&M, DLF Mall of India"
]

page_route = ["Home", "AI 태그 추출", "Data 관리", "About"]

choice = st.sidebar.selectbox("Select Activity", page_route)
st.sidebar.markdown(
    """Developed by an ML enthusiast himself:
    
    Rohit Tiwari 
    Email : knowrohit.07@gmail.com
    """)

quote = st.sidebar.selectbox("Feedback From Beta Testers ", quotes)

# ------------------------------------------------
# 1) Home 탭
# ------------------------------------------------
if choice == "Home":
    html_temp_home1 = """<div style="background-color:#0a2342;padding:10px">
                                        <h4 style="color:white;text-align:center;">
                                        Product recommender system using Transfer learning and Unsupervised learning.</h4>
                                        </div>
                                        </br>"""
    st.markdown(html_temp_home1, unsafe_allow_html=True)

    def save_uploaded_file(uploaded_file):
        try:
            with open(os.path.join('uploads', uploaded_file.name), 'wb') as f:
                f.write(uploaded_file.getbuffer())
            return 1
        except:
            return 0

    def feature_extraction(img_path, model):
        img = image.load_img(img_path, target_size=(244, 244))
        img_array = image.img_to_array(img)
        expanded_img_array = np.expand_dims(img_array, axis=0)
        preprocessed_img = preprocess_input(expanded_img_array)
        result = model.predict(preprocessed_img).flatten()
        normalized_result = result / norm(result)
        return normalized_result

    def display_color_palette(img_path, num_colors=5):
        color_thief = ColorThief(img_path)
        palette = color_thief.get_palette(color_count=num_colors)
        plt.figure(figsize=(5, 1))
        plt.bar(range(num_colors), [1] * num_colors,
                color=[f'#{c[0]:02x}{c[1]:02x}{c[2]:02x}' for c in palette], width=1)
        plt.axis('off')
        st.pyplot(plt.gcf())
        plt.close()

    def recommend(features, feature_list, n_recommendations=8):
        neighbors = NearestNeighbors(n_neighbors=n_recommendations + 1, algorithm='brute', metric='cosine')
        neighbors.fit(feature_list)
        distances, indices = neighbors.kneighbors([features])
        return indices, distances

    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    option = st.selectbox('Choose how you want to upload an image', ('Please select', 'Upload image', 'Camera input'))

    uploaded_file = None
    if option == 'Upload image':
        uploaded_file = st.file_uploader("Choose an image")
    elif option == 'Camera input':
        uploaded_file = st.camera_input("Take a picture")

    if uploaded_file is not None:
        if save_uploaded_file(uploaded_file):
            # display the file
            display_image = Image.open(uploaded_file).convert("RGB")
            st.image(display_image)
            show_original_image = st.checkbox('Show original image alongside recommendations')

            # feature extract
            features = feature_extraction(os.path.join("uploads", uploaded_file.name), model)
            number_of_recommendations = st.slider('Number of recommendations:', min_value=1, max_value=10, value=5, step=1)
            indices, distances = recommend(features, feature_list, number_of_recommendations)

            show_stats = st.button("STATS FOR NERDS")

            # display recommendations
            columns = st.columns(number_of_recommendations)
            image_width = 550
            image_height = 700

            for i in range(number_of_recommendations):
                if i == 0 and show_original_image:
                    display_image = display_image.resize((image_width, image_height))
                    columns[i].image(display_image)
                else:
                    image_index = i - 1 if show_original_image else i
                    if image_index + 1 < len(indices[0]):
                        image_path = filenames[indices[0][image_index + 1]]
                        img = Image.open(image_path)
                        img = img.resize((image_width, image_height))
                        columns[i].image(img)

            if show_stats:
                st.write("Detailed information for the recommended products:")
                for i, distance in enumerate(distances[0][1:1 + number_of_recommendations]):
                    with st.expander(f"Product {i + 1}"):
                        st.write(f"Product {i + 1}:")
                        st.write(f"Similarity score: {1 - distance:.4f}")
                        st.write(f"Filename: {filenames[indices[0][i]]}")

                        img = Image.open(filenames[indices[0][i]])
                        img_dimensions = img.size
                        st.write(f"Image dimensions: {img_dimensions}")

                        aspect_ratio = img_dimensions[0] / img_dimensions[1]
                        st.write(f"Aspect ratio: {aspect_ratio:.2f}")

                        st.write(f"Index in feature list: {indices[0][i]}")
                        st.write(f"Raw distance score: {distance:.4f}")
                        st.write("Color palette:")
                        display_color_palette(filenames[indices[0][i]])
                        st.write("")
        else:
            st.header("Some error occurred in file upload")

# ------------------------------------------------
# 2) 공통 함수(태그 저장, 패턴 감지, 계절 추천 등)
# ------------------------------------------------
def save_tags(image_path, tags):
    """태그를 저장하는 함수"""
    if not os.path.exists('saved_tags'):
        os.makedirs('saved_tags')

    # 이미지 파일명 추출
    filename = os.path.basename(image_path)
    base_name = os.path.splitext(filename)[0]

    # 태그 정보를 JSON으로 저장
    import json
    with open(f'saved_tags/{base_name}_tags.json', 'w', encoding='utf-8') as f:
        json.dump({'image': filename, 'tags': tags}, f, ensure_ascii=False)

    return f'saved_tags/{base_name}_tags.json'

def detect_pattern(image_path):
    """이미지에서 패턴 유형을 감지하는 함수 (모델 없이 단순 예시)"""
    import random
    patterns = ["단색", "스트라이프", "체크", "도트", "플로럴", "기하학적", "그래픽", "카무플라주"]
    return random.choice(patterns)

def recommend_season(color_name, clothing_type):
    """색상과 의류 종류를 기반으로 계절 추천"""
    summer_colors = ["빨강", "주황", "노랑", "하얀"]
    winter_colors = ["검정", "남색", "회색"]
    spring_fall_colors = ["초록", "파랑", "보라", "핑크", "갈색"]

    if color_name in summer_colors:
        return "여름"
    elif color_name in winter_colors:
        return "겨울"
    else:
        # 간단 예시 로직
        if clothing_type in ["아우터", "하의"]:
            return "가을"
        else:
            return "봄"

def crawl_fashion_data(url, max_items=10):
    """패션 웹사이트에서 이미지와 정보를 크롤링하는 기본 함수"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import time

        st.info("크롤링을 시작합니다. 이 작업은 몇 분 정도 소요될 수 있습니다.")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 예시: img 태그, product-name 클래스 등 (실제 사이트 구조에 맞게 수정)
            image_elements = soup.select('img.product-image')
            product_names = soup.select('div.product-name')

            results = []
            for i, (img, name) in enumerate(zip(image_elements, product_names)):
                if i >= max_items:
                    break

                img_url = img.get('src', '')
                product_name = name.text.strip()

                # 이미지 다운로드
                if img_url and img_url.startswith('http'):
                    img_response = requests.get(img_url, headers=headers)
                    if img_response.status_code == 200:
                        # 이미지 저장
                        if not os.path.exists('crawled_images'):
                            os.makedirs('crawled_images')
                        img_filename = f"crawled_images/{i}_{product_name.replace(' ', '_')}.jpg"
                        with open(img_filename, 'wb') as f:
                            f.write(img_response.content)

                        results.append({
                            'name': product_name,
                            'image_path': img_filename,
                            'source_url': img_url
                        })
                time.sleep(1)
            return results
        else:
            st.error(f"웹사이트 접근 오류: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {str(e)}")
        return []

# ------------------------------------------------
# 3) 무신사/에이블리/쉬인/코코블랙 등 사이트별 크롤링 함수
# ------------------------------------------------
def crawl_musinsa(url, max_items=10):
    """무신사 웹사이트 크롤링 함수"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import time

        st.info("무신사 데이터 크롤링을 시작합니다...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('li.li_box')

            results = []
            for i, item in enumerate(items):
                if i >= max_items:
                    break
                img_element = item.select_one('img.lazyload')
                title_element = item.select_one('p.list_info')

                if img_element and title_element:
                    img_url = img_element.get('data-original', '') or img_element.get('src', '')
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://www.musinsa.com' + img_url

                    product_name = title_element.text.strip()

                    if img_url:
                        img_response = requests.get(img_url, headers=headers)
                        if img_response.status_code == 200:
                            if not os.path.exists('crawled_images'):
                                os.makedirs('crawled_images')
                            img_filename = f"crawled_images/musinsa_{i}_{product_name[:20].replace(' ', '_')}.jpg"
                            with open(img_filename, 'wb') as f:
                                f.write(img_response.content)

                            results.append({
                                'name': product_name,
                                'image_path': img_filename,
                                'source_url': img_url
                            })
                time.sleep(1)
            return results
        else:
            st.error(f"웹사이트 접근 오류: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {str(e)}")
        return []

def crawl_ably(url, max_items=10):
    """A-BLY 웹사이트 크롤링 함수"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import time

        st.info("A-BLY 데이터 크롤링을 시작합니다...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('div.product-wrapper')

            results = []
            for i, item in enumerate(items):
                if i >= max_items:
                    break
                img_element = item.select_one('img.product-img')
                title_element = item.select_one('p.product-name')

                if img_element and title_element:
                    img_url = img_element.get('data-src', '') or img_element.get('src', '')
                    if not img_url.startswith('http'):
                        img_url = 'https://m.a-bly.com' + img_url

                    product_name = title_element.text.strip()

                    if img_url:
                        img_response = requests.get(img_url, headers=headers)
                        if img_response.status_code == 200:
                            if not os.path.exists('crawled_images'):
                                os.makedirs('crawled_images')
                            img_filename = f"crawled_images/ably_{i}_{product_name[:20].replace(' ', '_')}.jpg"
                            with open(img_filename, 'wb') as f:
                                f.write(img_response.content)

                            results.append({
                                'name': product_name,
                                'image_path': img_filename,
                                'source_url': img_url
                            })
                time.sleep(1)
            return results
        else:
            st.error(f"웹사이트 접근 오류: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {str(e)}")
        return []

def crawl_shein(url, max_items=10):
    """SHEIN 웹사이트 크롤링 함수"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import time

        st.info("SHEIN 데이터 크롤링을 시작합니다...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('div.S-product-item')

            results = []
            for i, item in enumerate(items):
                if i >= max_items:
                    break
                img_element = item.select_one('img.S-product-item__img')
                title_element = item.select_one('div.S-product-item__name')

                if img_element and title_element:
                    img_url = img_element.get('data-src', '') or img_element.get('src', '')
                    product_name = title_element.text.strip()

                    if img_url:
                        img_response = requests.get(img_url, headers=headers)
                        if img_response.status_code == 200:
                            if not os.path.exists('crawled_images'):
                                os.makedirs('crawled_images')
                            img_filename = f"crawled_images/shein_{i}_{product_name[:20].replace(' ', '_')}.jpg"
                            with open(img_filename, 'wb') as f:
                                f.write(img_response.content)

                            results.append({
                                'name': product_name,
                                'image_path': img_filename,
                                'source_url': img_url
                            })
                time.sleep(1)
            return results
        else:
            st.error(f"웹사이트 접근 오류: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {str(e)}")
        return []

def crawl_cocoblack(url, max_items=10):
    """COCOBLACK 웹사이트 크롤링 함수"""
    try:
        import requests
        from bs4 import BeautifulSoup
        import time

        st.info("COCOBLACK 데이터 크롤링을 시작합니다...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('li.prdList')

            results = []
            for i, item in enumerate(items):
                if i >= max_items:
                    break
                img_element = item.select_one('img.thumbImage')
                title_element = item.select_one('p.name span')

                if img_element and title_element:
                    img_url = img_element.get('src', '')
                    product_name = title_element.text.strip()

                    if img_url:
                        img_response = requests.get(img_url, headers=headers)
                        if img_response.status_code == 200:
                            if not os.path.exists('crawled_images'):
                                os.makedirs('crawled_images')
                            img_filename = f"crawled_images/cocoblack_{i}_{product_name[:20].replace(' ', '_')}.jpg"
                            with open(img_filename, 'wb') as f:
                                f.write(img_response.content)

                            results.append({
                                'name': product_name,
                                'image_path': img_filename,
                                'source_url': img_url
                            })
                time.sleep(1)
            return results
        else:
            st.error(f"웹사이트 접근 오류: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {str(e)}")
        return []

# 사이드바 디스클레이머
st.sidebar.markdown("""
<div style="background-color: #ffcccc; padding: 10px; border-radius: 5px; margin-top: 20px;">
<b>⚠️ 디스클레이머</b>: 웹 크롤링은 해당 웹사이트의 이용약관에 위배될 수 있으며, 교육 목적으로만 사용해야 합니다.
상업적 용도로 사용 시 법적 문제가 발생할 수 있습니다.
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------
# 4) "AI 태그 추출" 탭
# ------------------------------------------------
if choice == "AI 태그 추출":
    st.header("AI 옷 태그 추출")
    
    # 탭 정의를 변수에 저장
    tabs = st.tabs(["이미지 업로드", "웹 크롤링", "AI 코디 추천"])
    
    # 첫 번째 탭 - 이미지 업로드
    with tabs[0]:
        st.subheader("이미지 업로드")
        uploaded_file = st.file_uploader("의류 이미지를 업로드하세요", type=["png", "jpg", "jpeg", "bmp", "gif", "tiff", "webp"])

        if uploaded_file is not None:
            # RGBA -> RGB로 변환
            image = Image.open(uploaded_file).convert("RGB")
            st.image(image, caption="업로드된 이미지", use_container_width=True)
            temp_path = "temp_image.jpg"
            image.save(temp_path, format="JPEG")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("색상 선택")
                color_options = list(COLOR_MAP.keys())
                selected_colors = st.multiselect("색상 선택 (복수 선택 가능)", color_options)

                # 자동 추출된 색상
                palette, color_names = extract_colors(temp_path, color_count=3)
                if (palette):
                    st.subheader("AI 추출 색상")
                    color_cols = st.columns(len(palette))
                    for i, (rgb, color_name) in enumerate(zip(palette, color_names)):
                        with color_cols[i]:
                            st.markdown(
                                f'<div style="background-color:rgb{rgb};width:50px;height:50px;border-radius:5px;"></div>',
                                unsafe_allow_html=True
                            )
                            st.write(color_name)

                # 패턴 감지
                pattern = detect_pattern(temp_path)
                st.subheader("패턴")
                patterns = ["단색", "스트라이프", "체크", "도트", "플로럴", "기하학적", "그래픽", "카무플라주"]
                selected_pattern = st.selectbox("패턴 선택", patterns, index=patterns.index(pattern) if pattern in patterns else 0)

            with col2:
                st.subheader("의류 종류")
                clothing_type = st.radio(
                    "의류 종류 선택",
                    ["상의", "하의", "아우터", "원피스", "신발", "액세서리"]
                )

                st.subheader("스타일")
                selected_style = st.selectbox("스타일 선택", STYLE_OPTIONS)

                st.subheader("계절")
                seasons = ["봄", "여름", "가을", "겨울", "사계절"]
                if color_names:
                    recommended_season = recommend_season(color_names[0], clothing_type)
                    season_index = seasons.index(recommended_season) if recommended_season in seasons else 4
                else:
                    season_index = 4
                selected_season = st.selectbox("계절 선택", seasons, index=season_index)

            # 태그 구성
            st.subheader("선택된 태그")
            tags = []

            if selected_colors:
                tags.extend(selected_colors)
            elif color_names:
                # 사용자가 직접 색상을 고르지 않았다면, 자동 추출된 첫 번째 색상
                tags.append(color_names[0])

            tags.append(selected_pattern)
            tags.append(clothing_type)
            tags.append(selected_style)
            tags.append(selected_season)

            tag_html = ""
            for tag in tags:
                tag_html += f'<span style="background-color:#f0f0f0;padding:5px 10px;margin:5px;border-radius:20px;display:inline-block;">{tag}</span>'
            st.markdown(f"<div style='margin-top:10px;'>{tag_html}</div>", unsafe_allow_html=True)

            st.subheader("추천 코디")
            if st.button("코디 추천받기", key="tab1_recommend_button"):
                st.info("선택한 태그를 바탕으로 코디를 추천합니다...")
                st.success("추천이 완료되었습니다!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.image("https://via.placeholder.com/200x300/f0f0f0?text=추천코디1", caption="추천 코디 1")
                with col2:
                    st.image("https://via.placeholder.com/200x300/f0f0f0?text=추천코디2", caption="추천 코디 2")
                with col3:
                    st.image("https://via.placeholder.com/200x300/f0f0f0?text=추천코디3", caption="추천 코디 3")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("확인", key="tab1_confirm_btn", use_container_width=True):
                    # 무신사 태그 자동 추천
                    try:
                        fashion_data = load_fashion_data()
                        if not fashion_data.empty:
                            # 색상과 카테고리로 유사 제품 찾기
                            filtered_data = fashion_data[fashion_data['category'] == clothing_type] if 'category' in fashion_data.columns else fashion_data
                            
                            # 색상 필터링
                            if selected_colors:
                                color_match = filtered_data['productName'].str.contains('|'.join(selected_colors), case=False, na=False)
                                filtered_data = filtered_data[color_match]
                            
                            # 추천 태그 추출
                            if not filtered_data.empty:
                                sample_product = filtered_data.sample(1).iloc[0]
                                musinsa_tags = extract_musinsa_tags(sample_product)
                                
                                # 기존 태그와 병합
                                all_tags = list(set(tags + musinsa_tags))
                                st.info(f"무신사 데이터에서 {len(musinsa_tags)}개의 태그가 추가되었습니다.")
                                tags = all_tags
                    except Exception as e:
                        st.warning(f"무신사 태그 추가 중 오류: {e}")
                    
                    # 태그 저장
                    saved_path = save_tags(temp_path, tags)
                    st.success(f"태그가 성공적으로 저장되었습니다! 저장 경로: {saved_path}")
                    
                    # 학습 데이터에 추가 옵션
                    add_to_training = st.checkbox("이 이미지와 태그를 학습 데이터에 추가하기")
                    if add_to_training:
                        with st.spinner("학습 데이터에 추가 중..."):
                            if add_user_data_to_training(temp_path, tags):
                                st.success("이미지와 태그가 학습 데이터에 성공적으로 추가되었습니다!")
                            else:
                                st.error("학습 데이터 추가에 실패했습니다.")
                                
            with col2:
                if st.button("수정", key="tab1_edit_btn", use_container_width=True):
                    st.info("태그를 수정해주세요.")

            # 임시 파일 제거
            if os.path.exists(temp_path):
                os.remove(temp_path)

    with tabs[1]:
        st.subheader("패션 웹사이트 크롤링")
        st.write("패션 웹사이트에서 이미지와 정보를 가져옵니다.")
        
        site_option = st.radio(
            "크롤링할 사이트 선택",
            ["무신사", "A-BLY", "SHEIN", "COCOBLACK", "기타 사이트"]
        )

        if site_option == "무신사":
            default_url = "https://www.musinsa.com/main/musinsa/recommend"
        elif site_option == "A-BLY":
            default_url = "https://m.a-bly.com/"
        elif site_option == "SHEIN":
            default_url = "https://kr.shein.com/"
        elif site_option == "COCOBLACK":
            default_url = "https://www.cocoblack.kr/"
        else:
            default_url = "https://www.example.com/fashion"

        website_url = st.text_input("웹사이트 URL", default_url)
        max_items = st.slider("최대 아이템 수", 1, 50, 10)
        auto_tag = st.checkbox("크롤링한 이미지에서 태그 자동 생성", value=True)

        if st.button("크롤링 시작"):
            if website_url and not website_url == "https://www.example.com/fashion":
                with st.spinner("데이터를 크롤링 중입니다..."):
                    if site_option == "무신사":
                        results = crawl_musinsa(website_url, max_items)
                    elif site_option == "A-BLY":
                        results = crawl_ably(website_url, max_items)
                    elif site_option == "SHEIN":
                        results = crawl_shein(website_url, max_items)
                    elif site_option == "COCOBLACK":
                        results = crawl_cocoblack(website_url, max_items)
                    else:
                        results = crawl_fashion_data(website_url, max_items)

                    if results:
                        st.success(f"{len(results)}개의 아이템을 성공적으로 크롤링했습니다.")
                        st.subheader("크롤링 결과")

                        cols = st.columns(3)  # 3열 갤러리
                        for i, item in enumerate(results):
                            with cols[i % 3]:
                                if os.path.exists(item['image_path']):
                                    st.image(item['image_path'], caption=item['name'], use_container_width=True)

                                    if auto_tag:
                                        try:
                                            palette, color_names = extract_colors(item['image_path'], color_count=3)
                                            pattern = detect_pattern(item['image_path'])

                                            tag_html = ""
                                            if color_names:
                                                tag_html += f'<span style="background-color:#f0f0f0;padding:5px 10px;margin:2px;border-radius:20px;font-size:12px;">{color_names[0]}</span>'
                                            tag_html += f'<span style="background-color:#f0f0f0;padding:5px 10px;margin:2px;border-radius:20px;font-size:12px;">{pattern}</span>'

                                            st.markdown(f"자동 태그: {tag_html}", unsafe_allow_html=True)
                                        except:
                                            st.write("태그 추출 실패")

                                    if st.button(f"상세 정보 #{i+1}", key=f"detail_{i}"):
                                        with st.expander(f"제품 상세 정보 - {item['name']}"):
                                            st.write(f"제품명: {item['name']}")
                                            st.write(f"출처 URL: {item['source_url']}")

                                            if st.button(f"이 제품 태그 저장", key=f"save_{i}"):
                                                tags = []
                                                if 'color_names' in locals() and color_names:
                                                    tags.append(color_names[0])
                                                if 'pattern' in locals():
                                                    tags.append(pattern)
                                                import random
                                                categories = ["상의", "하의", "아우터", "원피스", "신발", "액세서리"]
                                                tags.append(random.choice(categories))
                                                saved_path = save_tags(item['image_path'], tags)
                                                st.success(f"태그가 저장되었습니다: {saved_path}")
                    else:
                        st.warning("크롤링된 데이터가 없습니다. 웹사이트 구조가 변경되었거나 크롤링이 차단되었을 수 있습니다.")
            else:
                st.error("유효한 URL을 입력해주세요.")

        with st.expander("크롤링이란?"):
            st.write("""
            웹 크롤링은 웹사이트에서 정보를 자동으로 수집하는 프로세스입니다. 
            이 기능은 패션 사이트에서 제품 이미지와 정보를 수집하여 분석하거나 추천에 활용할 수 있게 해줍니다.

            **주의사항**:
            - 웹 크롤링은 해당 사이트의 이용약관에 위배될 수 있습니다.
            - 데이터는 개인적인 학습과 연구 목적으로만 사용하세요.
            - 과도한 요청은 대상 서버에 부담을 줄 수 있으니 적절한 간격을 두고 크롤링하세요.
            """)
    
    # AI 코디 추천 탭
    with tabs[2]:
        st.subheader("AI 코디 추천")
        st.write("무신사 데이터를 활용한 스타일 및 색상 기반 코디 추천 시스템입니다.")
        
        # 데이터 로드
        with st.spinner("데이터 로드 중..."):
            fashion_data = load_fashion_data()
            
            if not fashion_data.empty:
                st.success(f"{len(fashion_data)} 개의 패션 아이템 데이터를 로드했습니다.")
                
                # 사용자 입력 옵션
                col1, col2 = st.columns(2)
                
                with col1:
                    # 스타일 선택 - 고유 키 추가
                    selected_style = st.selectbox(
                        "스타일 선택",
                        STYLE_OPTIONS,
                        key="tab3_style_select"  # 고유 키 추가
                    )
                    
                    # 계절 선택 - 고유 키 추가
                    season = st.radio(
                        "계절 선택",
                        ["봄", "여름", "가을", "겨울"],
                        key="tab3_season_radio"  # 고유 키 추가
                    )
                
                with col2:
                    # 기본 색상 선택 - 고유 키 추가
                    base_color = st.selectbox(
                        "메인 컬러 선택",
                        [None] + list(COLOR_MAP.keys()),
                        key="tab3_color_select"  # 고유 키 추가
                    )
                    
                    # 성별 선택 - 고유 키 추가
                    gender = st.radio(
                        "성별",
                        ["남성", "여성", "공용"],
                        key="tab3_gender_radio"  # 고유 키 추가
                    )
                
                # 코디 생성 버튼 부분 수정
                if st.button("코디 추천받기", key="tab3_recommend_button"):
                    st.info("선택한 태그를 바탕으로 코디를 추천합니다...")
    
    # DB에서 유사한 코디 가져오기
    try:
        outfits = db.get_all_outfits()  # DB에서 코디 정보 가져오기
        if outfits is None:  # 반환값이 None인 경우 대비
            outfits = []
    except Exception as e:
        print(f"DB에서 코디 정보를 가져오는 중 오류 발생: {e}")
        outfits = []  # 오류 발생 시 빈 리스트로 초기화

if outfits:
        # 태그와 유사한 코디 필터링
        selected_outfits = []
        for outfit in outfits:
            outfit_id, style, season, base_color, outfit_json, created_at = outfit
            outfit_data = json.loads(outfit_json)
            
            # 태그 매칭 점수 계산
            match_score = 0
            if selected_style in style:
                match_score += 2
                selected_season = st.session_state.get('selected_season', '봄')  # 기본값 설정
                if selected_season in season:  # 여기에 콜론(:)이 빠져있었습니다
                    match_score += 2
            selected_colors = []  # 또는 적절한 초기값
            if any(color in base_color for color in selected_colors):
                match_score += 2
            if clothing_type in str(outfit_json):
                match_score += 1
                
            if match_score >= 3:  # 일정 점수 이상만 선택
                selected_outfits.append((outfit_data, match_score))
        
        # 점수 기준 정렬
        selected_outfits.sort(key=lambda x: x[1], reverse=True)
        top_outfits = selected_outfits[:3] if len(selected_outfits) >= 3 else selected_outfits
        
        if top_outfits:
            st.success("추천이 완료되었습니다!")
            col1, col2, col3 = st.columns(3)
            
            for i, (outfit_data, score) in enumerate(top_outfits):
                with [col1, col2, col3][i]:
                    # 대표 이미지 찾기
                    representative_image = None
                    for category, item in outfit_data.items():
                        if 'image_url' in item and item['image_url']:
                            representative_image = item['image_url']
                            break
                    
                    if representative_image:
                        st.image(representative_image, caption=f"추천 코디 {i+1}")
                    else:
                        st.image("https://via.placeholder.com/200x300/f0f0f0?text=추천코디", 
                                caption=f"추천 코디 {i+1}")
                    
                    # 코디 구성 정보
                    outfit_info = "".join([f"- {category}: {item['name']}<br>" 
                                           for category, item in outfit_data.items()])
                    st.markdown(f"<div style='font-size:small'>{outfit_info}</div>", 
                               unsafe_allow_html=True)
        else:
            st.info("조건에 맞는 코디를 찾을 수 없습니다. 새로운 코디를 생성합니다.")
            with st.spinner("새로운 코디 생성 중..."):
                new_outfit = generate_outfit_from_tags(tags)
                if new_outfit:
                    st.success("새로운 코디가 생성되었습니다!")
                    st.json(new_outfit)
                else:
                    st.warning("저장된 코디가 없습니다.")

# "저장된 코디" 탭의 샘플 코디 생성 부분 개선
# 이 함수를 기존 함수 영역 (예: color_harmony_check 함수 아래)에 추가

def generate_multiple_outfits(count=50):
    """무신사 데이터를 활용한 다수의 샘플 코디 자동 생성 함수"""
    # 패션 데이터 로드
    fashion_data = load_fashion_data()
    if fashion_data.empty:
        st.error("패션 데이터를 불러올 수 없습니다.")
        return 0
    
    # 데이터 전처리
    fashion_data = categorize_fashion_items(fashion_data)
    fashion_data = extract_item_color(fashion_data)
    
    import random
    created_count = 0
    
    # 프로그레스바 추가
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 스타일/계절 가중치 설정 (인기있는 스타일과 현재 계절에 더 높은 가중치)
    style_weights = {
        "미니멀룩": 0.3, 
        "스트릿패션": 0.2, 
        "보헤미안룩": 0.05, 
        "럭셔리룩": 0.1, 
        "아방가르드룩": 0.05, 
        "러블리룩": 0.05, 
        "빈티지룩": 0.1, 
        "스포티룩": 0.15, 
        "모던룩": 0.2, 
        "그런지룩": 0.05,
        "프레피룩": 0.05
    }
    
    # 현재 월에 따른 계절 가중치
    import datetime
    current_month = datetime.datetime.now().month
    season_weights = {
        "봄": 0.1,  # 3-5월
        "여름": 0.1,  # 6-8월
        "가을": 0.1,  # 9-11월
        "겨울": 0.1   # 12-2월
    }
    
    # 현재 계절에 더 높은 가중치 부여
    if 3 <= current_month <= 5:
        season_weights["봄"] = 0.7
    elif 6 <= current_month <= 8:
        season_weights["여름"] = 0.7
    elif 9 <= current_month <= 11:
        season_weights["가을"] = 0.7
    else:  # 12, 1, 2월
        season_weights["겨울"] = 0.7
    
    for i in range(count):
        try:
            # 가중치에 따른 랜덤 스타일 선택
            style = random.choices(
                list(style_weights.keys()), 
                weights=list(style_weights.values()), 
                k=1
            )[0]
            
            # 가중치에 따른 랜덤 계절 선택
            season = random.choices(
                list(season_weights.keys()), 
                weights=list(season_weights.values()), 
                k=1
            )[0]
            
            # 랜덤 색상 선택 (기본 색상에 더 높은 가중치)
            basic_colors = ["검정", "흰색", "회색", "베이지", None]
            vibrant_colors = ["빨강", "파랑", "초록", "노랑", "보라", "핑크"]
            
            color_options = basic_colors + vibrant_colors
            color_weights = [0.15, 0.15, 0.1, 0.1, 0.1] + [0.05] * len(vibrant_colors)
            color = random.choices(color_options, weights=color_weights, k=1)[0]
            
            # 코디 생성
            outfit = generate_outfit(fashion_data, style=style, base_color=color)
            
            if outfit and len(outfit) >= 2:  # 최소 2개 이상의 아이템이 있어야 코디로 인정
                # DB에 저장
                outfit_id = db.save_outfit(style, season, color, outfit)
                if outfit_id:
                    created_count += 1
                    status_text.text(f"{i+1}/{count} 생성 중... 성공: {created_count}")
            
            # 프로그레스바 업데이트        
            progress_bar.progress((i + 1) / count)
            
        except Exception as e:
            print(f"코디 생성 오류: {e}")
            continue
            
    return created_count

# 코디 생성 버튼을 "저장된 코디" 탭에서 수정
if st.button("샘플 코디 50개 자동 생성", key="data_sample_outfit_btn"):
    with st.spinner("샘플 코디를 생성 중입니다. 잠시 기다려주세요..."):
        created = generate_multiple_outfits(50)
        if created > 0:
            st.success(f"총 {created}개의 샘플 코디가 생성되었습니다.")
        else:
            st.warning("코디 생성에 실패했습니다. 데이터를 확인해주세요.")

# 모델 관련 함수 영역에 추가

def feature_extraction(img_path, model):
    """이미지에서 특징 추출"""
    try:
        img = image.load_img(img_path, target_size=(244, 244))
        img_array = image.img_to_array(img)
        expanded_img_array = np.expand_dims(img_array, axis=0)
        preprocessed_img = preprocess_input(expanded_img_array)
        result = model.predict(preprocessed_img).flatten()
        normalized_result = result / norm(result)
        return normalized_result
    except Exception as e:
        st.error(f"특징 추출 중 오류: {e}")
        return None

def add_user_data_to_training(user_image_path, user_tags):
    """사용자가 업로드한 이미지와 태그를 학습 데이터에 추가"""
    try:
        global model, feature_list, filenames
        
        if model is None:
            st.warning("모델이 로드되지 않아 학습 데이터에 추가할 수 없습니다.")
            return False
            
        # 이미지 특성 추출
        features = feature_extraction(user_image_path, model)
        
        if features is None:
            return False
        
        # 기존 데이터가 있는 경우에만 추가
        if len(feature_list) > 0:
            new_feature_list = np.vstack([feature_list, features.reshape(1, -1)])
            filenames.append(user_image_path)
        else:
            # 초기 데이터가 없는 경우 새로 생성
            new_feature_list = features.reshape(1, -1) 
            filenames = [user_image_path]
            
        # 업데이트된 데이터 저장
        with open('features_list_for_prods.pkl', 'wb') as f:
            pickle.dump(new_feature_list, f)
            
        with open('filenames_products.pkl', 'wb') as f:
            pickle.dump(filenames, f)
            
        # 전역 변수 업데이트
        feature_list = new_feature_list
        
        # 태그 정보도 DB에 저장
        db.save_tags(user_image_path, user_tags)
        
        return True
            
    except Exception as e:
        st.error(f"학습 데이터 추가 중 오류: {e}")
        return False

# 무신사 데이터를 활용한 향상된 태그 추출 함수
def extract_musinsa_tags(product_data):
    """무신사 데이터에서 상세 태그 추출"""
    tags = []
    
    # 브랜드 태그
    if 'brandName' in product_data and pd.notna(product_data['brandName']):
        tags.append(product_data['brandName'])
    
    # 색상 태그 추출
    color_matched = False
    if 'productName' in product_data and pd.notna(product_data['productName']):
        product_name = product_data['productName'].lower()
        for color_name in COLOR_MAP.keys():
            color_keywords = [color_name]
            if color_name == '빨강': color_keywords.extend(['레드', 'red'])
            elif color_name == '파랑': color_keywords.extend(['블루', 'blue'])
            elif color_name == '초록': color_keywords.extend(['그린', 'green'])
            elif color_name == '노랑': color_keywords.extend(['옐로우', 'yellow'])
            elif color_name == '검정': color_keywords.extend(['블랙', 'black'])
            elif color_name == '흰색': color_keywords.extend(['화이트', 'white'])
            
            for keyword in color_keywords:
                if keyword.lower() in product_name:
                    tags.append(color_name)
                    color_matched = True
                    break
            if color_matched:
                break
    
    # 카테고리 태그
    categories = {
        '상의': ['티셔츠', '니트', '셔츠', '맨투맨', '후드', '블라우스', '탑'],
        '하의': ['팬츠', '진', '청바지', '슬랙스', '스커트', '쇼츠', '레깅스', 'pants'],
        '아우터': ['자켓', '코트', '패딩', '집업', '점퍼', '가디건', '베스트', 'jacket'],
        '원피스': ['원피스', '드레스', 'dress'],
        '신발': ['스니커즈', '구두', '로퍼', '슬리퍼', '샌들', '힐', '부츠', 'shoes'],
        '액세서리': ['모자', '가방', '벨트', '양말', '주얼리', '팔찌', '목걸이', 'cap', 'bag']
    }
    
    if 'productName' in product_data and pd.notna(product_data['productName']):
        product_name = product_data['productName'].lower()
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword.lower() in product_name:
                    tags.append(category)
                    tags.append(keyword)
                    break
    
    # 스타일 태그
    style_keywords = {
        '미니멀룩': ['미니멀', '심플', '베이직'],
        '스트릿패션': ['스트릿', '캐주얼', '힙합', '어반'],
        '럭셔리룩': ['럭셔리', '포멀', '엘레강스'],
        '빈티지룩': ['빈티지', '레트로', '올드스쿨'],
        '스포티룩': ['스포티', '애슬레저', '액티브'],
        '모던룩': ['모던', '컨템포러리']
    }
    
    if 'productName' in product_data and pd.notna(product_data['productName']):
        product_name = product_data['productName'].lower()
        for style, keywords in style_keywords.items():
            for keyword in keywords:
                if keyword.lower() in product_name:
                    tags.append(style)
                    break
    
    # 중복 제거 및 공백 제거
    tags = [tag.strip() for tag in tags if tag.strip()]
    return list(set(tags))

# app.py에 추가
def extract_hashtags(text):
    """상품 설명에서 해시태그 추출"""
    return re.findall(r"#(\w+)", text)

def enrich_tags_with_hashtags(tags, product_name):
    """해시태그를 통한 태그 보강"""
    hashtags = extract_hashtags(product_name)
    if hashtags:
        # 해시태그를 태그 목록에 추가
        return list(set(tags + hashtags))
    return tags


# 태그 추천 시스템에 학습된 모델 활용
def recommend_tags_from_model(image_tags):
    try:
        # 모델 로딩
        with open('tag_vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)
        
        with open('fashion_dataset.json', 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        # 유사한 아이템 찾기
        input_vec = vectorizer.transform([" ".join(image_tags)])
        
        with open('tag_matrix.pkl', 'rb') as f:
            tfidf_matrix = pickle.load(f)
        
        similarities = cosine_similarity(input_vec, tfidf_matrix).flatten()
        top_indices = similarities.argsort()[-5:][::-1]  # 상위 5개
        
        # 태그 수집
        recommended_tags = []
        for idx in top_indices:
            if idx < len(dataset):
                recommended_tags.extend(dataset[idx].get('tags', []))
        
        # 중복 제거 및 기존 태그 제외
        recommended_tags = list(set(recommended_tags) - set(image_tags))
        return recommended_tags[:10]  # 최대 10개 태그 제안
    
    except Exception as e:
        print(f"태그 추천 오류: {e}")
        return []

# AI 코디 추천 탭
    with tabs[2]:
        st.subheader("AI 코디 추천")
        st.write("무신사 데이터를 활용한 스타일 및 색상 기반 코디 추천 시스템입니다.")
        
        # 데이터 로드
        with st.spinner("데이터 로드 중..."):
            fashion_data = load_fashion_data()
            
            if not fashion_data.empty:
                st.success(f"{len(fashion_data)} 개의 패션 아이템 데이터를 로드했습니다.")
                
                # 사용자 입력 옵션
                col1, col2 = st.columns(2)
                
                with col1:
                    # 스타일 선택 - 고유 키 추가
                    selected_style = st.selectbox(
                        "스타일 선택",
                        STYLE_OPTIONS,
                        key="tab3_style_select"
                    )
                    
                    # 계절 선택 - 고유 키 추가
                    selected_season = st.radio(
                        "계절 선택",
                        ["봄", "여름", "가을", "겨울"],
                        key="tab3_season_radio"
                    )
                
                with col2:
                    # 기본 색상 선택 - 고유 키 추가
                    base_color = st.selectbox(
                        "메인 컬러 선택",
                        [None] + list(COLOR_MAP.keys()),
                        key="tab3_color_select"
                    )
                    
                    # 성별 선택 - 고유 키 추가
                    gender = st.radio(
                        "성별",
                        ["남성", "여성", "공용"],
                        key="tab3_gender_radio"
                    )
                
                # 코디 생성 버튼
                if st.button("코디 추천받기", key="tab3_recommend_button"):
                    st.info("선택한 태그를 바탕으로 코디를 추천합니다...")
                    
                    # clothing_type 초기화 (기본값 설정)
                    clothing_type = st.session_state.get('clothing_type', '상의')
                    
                    # 태그 초기화
                    tags = [selected_style, selected_season]
                    if base_color:
                        tags.append(base_color)
                    
                    # DB에서 유사한 코디 가져오기
                    try:
                        outfits = db.get_all_outfits()
                        if outfits is None:
                            outfits = []
                    except Exception as e:
                        print(f"DB에서 코디 정보를 가져오는 중 오류 발생: {e}")
                        outfits = []
                    
                    if outfits:
                        # 태그와 유사한 코디 필터링
                        selected_outfits = []
                        for outfit in outfits:
                            outfit_id, style, season, base_color, outfit_json, created_at = outfit
                            outfit_data = json.loads(outfit_json)
                            
                            # 태그 매칭 점수 계산
                            match_score = 0
                            if selected_style in style:
                                match_score += 2
                                if selected_season in season:
                                    match_score += 2
                            selected_colors = tags
                            if any(color in base_color for color in selected_colors if color in COLOR_MAP):
                                match_score += 2
                            if clothing_type in str(outfit_json):
                                match_score += 1
                                
                            if match_score >= 3:  # 일정 점수 이상만 선택
                                selected_outfits.append((outfit_data, match_score))
                        
                        # 점수 기준 정렬
                        selected_outfits.sort(key=lambda x: x[1], reverse=True)
                        top_outfits = selected_outfits[:3] if len(selected_outfits) >= 3 else selected_outfits
                        
                        if top_outfits:
                            st.success("추천이 완료되었습니다!")
                            col1, col2, col3 = st.columns(3)
                            
                            for i, (outfit_data, score) in enumerate(top_outfits):
                                with [col1, col2, col3][i]:
                                    # 대표 이미지 찾기
                                    representative_image = None
                                    for category, item in outfit_data.items():
                                        if 'image_url' in item and item['image_url']:
                                            representative_image = item['image_url']
                                            break
                                    
                                    if representative_image:
                                        st.image(representative_image, caption=f"추천 코디 {i+1}")
                                    else:
                                        st.image("https://via.placeholder.com/200x300/f0f0f0?text=추천코디", 
                                                caption=f"추천 코디 {i+1}")
                                    
                                    # 코디 구성 정보
                                    outfit_info = "".join([f"- {category}: {item['name']}<br>" 
                                                        for category, item in outfit_data.items()])
                                    st.markdown(f"<div style='font-size:small'>{outfit_info}</div>", 
                                              unsafe_allow_html=True)
                        else:
                            st.info("조건에 맞는 코디를 찾을 수 없습니다. 새로운 코디를 생성합니다.")
                            with st.spinner("새로운 코디 생성 중..."):
                                # generate_outfit_from_tags 함수 정의 필요
                                new_outfit = generate_outfit(fashion_data, style=selected_style, base_color=base_color)
                                if new_outfit:
                                    st.success("새로운 코디가 생성되었습니다!")
                                    display_outfit(new_outfit)
                                else:
                                    st.warning("저장된 코디가 없습니다.")



