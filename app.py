# app.py
import streamlit as st
import os
import numpy as np
import pandas as pd
import json
import pickle
import tensorflow
from PIL import Image
import re
import matplotlib.pyplot as plt
from gtts import gTTS
from tempfile import NamedTemporaryFile
import sqlite3

# Import DB 관련 모듈
from fashion_db import FashionDB

# 모듈별 import
from modules.constants import COLOR_MAP, STYLE_OPTIONS
from modules.data_loader import load_fashion_data, categorize_fashion_items, extract_item_color
from modules.color_utils import extract_colors, seasonal_recommendation, color_harmony_check
from modules.recommendation import generate_outfit, display_outfit
from modules.tag_utils import save_tags, detect_pattern, recommend_season, extract_musinsa_tags, extract_hashtags, enrich_tags_with_hashtags, recommend_tags_from_model
from modules.crawling import crawl_fashion_data, crawl_musinsa, crawl_ably, crawl_shein, crawl_cocoblack
from modules.model_utils import load_model_and_features, feature_extraction, add_user_data_to_training
from modules.outfit_generator import generate_multiple_outfits

# DB 인스턴스 생성
db = FashionDB()

# 모델 로드
load_model_and_features()

st.title('FashionGPT')

# 문자열 배열 (피드백)
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
    """
)
quote = st.sidebar.selectbox("Feedback From Beta Testers ", quotes)

# ------------------------ Home 탭 ------------------------
if choice == "Home":
    html_temp_home1 = """<div style="background-color:#0a2342;padding:10px">
                           <h4 style="color:white;text-align:center;">
                           Product recommender system using Transfer learning and Unsupervised learning.
                           </h4>
                           </div><br>"""
    st.markdown(html_temp_home1, unsafe_allow_html=True)
    
    # 파일 업로드 및 추천 관련 내부 함수들
    def save_uploaded_file(uploaded_file):
        try:
            if not os.path.exists('uploads'):
                os.makedirs('uploads')
            with open(os.path.join('uploads', uploaded_file.name), 'wb') as f:
                f.write(uploaded_file.getbuffer())
            return 1
        except Exception as e:
            st.error(f"파일 업로드 오류: {e}")
            return 0

    def local_feature_extraction(img_path, model):
        # 동일 기능, model_utils.feature_extraction과 유사
        img = Image.open(img_path)
        img = img.resize((244, 244))
        from tensorflow.keras.preprocessing import image as keras_image
        img = keras_image.img_to_array(img)
        import numpy as np
        expanded_img_array = np.expand_dims(img, axis=0)
        from tensorflow.keras.applications.resnet50 import preprocess_input
        preprocessed_img = preprocess_input(expanded_img_array)
        result = model.predict(preprocessed_img).flatten()
        from numpy.linalg import norm
        normalized_result = result / norm(result)
        return normalized_result

    def recommend(features, feature_list, n_recommendations=8):
        from sklearn.neighbors import NearestNeighbors
        neighbors = NearestNeighbors(n_neighbors=n_recommendations + 1, algorithm='brute', metric='cosine')
        neighbors.fit(feature_list)
        distances, indices = neighbors.kneighbors([features])
        return indices, distances

    option = st.selectbox('Choose how you want to upload an image', ('Please select', 'Upload image', 'Camera input'))
    uploaded_file = None
    if option == 'Upload image':
        uploaded_file = st.file_uploader("Choose an image")
    elif option == 'Camera input':
        uploaded_file = st.camera_input("Take a picture")
    
    if uploaded_file is not None:
        if save_uploaded_file(uploaded_file):
            display_image = Image.open(uploaded_file).convert("RGB")
            st.image(display_image, caption="업로드된 이미지", use_container_width=True)
            show_original_image = st.checkbox('Show original image alongside recommendations')
            features = local_feature_extraction(os.path.join("uploads", uploaded_file.name), model)
            number_of_recommendations = st.slider('Number of recommendations:', 1, 10, 5, 1)
            indices, distances = recommend(features, db.feature_list, number_of_recommendations)
            show_stats = st.button("STATS FOR NERDS")
            columns = st.columns(number_of_recommendations)
            image_width = 550
            image_height = 700
            for i in range(number_of_recommendations):
                if i == 0 and show_original_image:
                    display_img = display_image.resize((image_width, image_height))
                    columns[i].image(display_img)
                else:
                    image_index = i - 1 if show_original_image else i
                    if image_index + 1 < len(indices[0]):
                        image_path = db.filenames[indices[0][image_index + 1]]
                        img = Image.open(image_path)
                        img = img.resize((image_width, image_height))
                        columns[i].image(img)
            if show_stats:
                st.write("Detailed information for the recommended products:")
                for i, distance in enumerate(distances[0][1:1+number_of_recommendations]):
                    with st.expander(f"Product {i+1}"):
                        st.write(f"Similarity score: {1-distance:.4f}")
                        st.write(f"Filename: {db.filenames[indices[0][i]]}")
                        img = Image.open(db.filenames[indices[0][i]])
                        st.write(f"Image dimensions: {img.size}")
                        st.write(f"Aspect ratio: {img.size[0]/img.size[1]:.2f}")
                        st.write(f"Index in feature list: {indices[0][i]}")
                        st.write(f"Raw distance score: {distance:.4f}")
                        st.write("Color palette:")
                        display_colors, _ = extract_colors(db.filenames[indices[0][i]])
                        plt.figure(figsize=(5,1))
                        plt.bar(range(len(display_colors)), [1]*len(display_colors),
                                color=[f'#{c[0]:02x}{c[1]:02x}{c[2]:02x}' for c in display_colors], width=1)
                        plt.axis('off')
                        st.pyplot(plt.gcf())
                        plt.close()
        else:
            st.header("파일 업로드 중 오류 발생")

# ------------------------ AI 태그 추출 탭 ------------------------
if choice == "AI 태그 추출":
    tabs = st.tabs(["이미지 업로드", "웹 크롤링", "AI 코디 추천"])
    with tabs[0]:
        st.subheader("이미지 업로드")
        uploaded_file = st.file_uploader("의류 이미지를 업로드하세요", type=["png","jpg","jpeg","bmp","gif","tiff","webp"])
        if uploaded_file is not None:
            image_obj = Image.open(uploaded_file).convert("RGB")
            st.image(image_obj, caption="업로드된 이미지", use_container_width=True)
            temp_path = "temp_image.jpg"
            image_obj.save(temp_path, format="JPEG")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("색상 선택")
                color_options = list(COLOR_MAP.keys())
                selected_colors = st.multiselect("색상 선택 (복수 선택 가능)", color_options)
                palette, color_names = extract_colors(temp_path, color_count=3)
                if palette:
                    st.subheader("AI 추출 색상")
                    color_cols = st.columns(len(palette))
                    for i, (rgb, cname) in enumerate(zip(palette, color_names)):
                        with color_cols[i]:
                            st.markdown(f'<div style="background-color:rgb{rgb};width:50px;height:50px;border-radius:5px;"></div>', unsafe_allow_html=True)
                            st.write(cname)
                pattern = detect_pattern(temp_path)
                st.subheader("패턴")
                patterns = ["단색", "스트라이프", "체크", "도트", "플로럴", "기하학적", "그래픽", "카무플라주"]
                selected_pattern = st.selectbox("패턴 선택", patterns, index=patterns.index(pattern) if pattern in patterns else 0)
            with col2:
                st.subheader("의류 종류")
                clothing_type = st.radio("의류 종류 선택", ["상의","하의","아우터","원피스","신발","액세서리"])
                st.subheader("스타일")
                selected_style = st.selectbox("스타일 선택", STYLE_OPTIONS)
                st.subheader("계절")
                seasons = ["봄","여름","가을","겨울","사계절"]
                if color_names:
                    rec_season = recommend_season(color_names[0], clothing_type)
                    season_index = seasons.index(rec_season) if rec_season in seasons else 4
                else:
                    season_index = 4
                selected_season = st.selectbox("계절 선택", seasons, index=season_index)
            st.subheader("선택된 태그")
            tags = []
            if selected_colors:
                tags.extend(selected_colors)
            elif color_names:
                tags.append(color_names[0])
            tags.extend([selected_pattern, clothing_type, selected_style, selected_season])
            tag_html = "".join([f'<span style="background-color:#f0f0f0;padding:5px 10px;margin:5px;border-radius:20px;display:inline-block;">{tag}</span>' for tag in tags])
            st.markdown(f"<div style='margin-top:10px;'>{tag_html}</div>", unsafe_allow_html=True)
            st.subheader("추천 코디")
            if st.button("코디 추천받기", key="tab1_recommend_button"):
                st.info("선택한 태그 기반 코디 추천...")
                st.success("추천 완료!")
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
                    try:
                        fashion_data = load_fashion_data()
                        if not fashion_data.empty:
                            filtered_data = fashion_data[fashion_data['category'] == clothing_type] if 'category' in fashion_data.columns else fashion_data
                            if selected_colors:
                                color_match = filtered_data['productName'].str.contains('|'.join(selected_colors), case=False, na=False)
                                filtered_data = filtered_data[color_match]
                            if not filtered_data.empty:
                                sample_product = filtered_data.sample(1).iloc[0]
                                musinsa_tags = extract_musinsa_tags(sample_product)
                                all_tags = list(set(tags + musinsa_tags))
                                st.info(f"무신사 데이터에서 {len(musinsa_tags)}개의 태그 추가됨.")
                                tags = all_tags
                    except Exception as e:
                        st.warning(f"무신사 태그 추가 중 오류: {e}")
                    saved_path = save_tags(temp_path, tags)
                    st.success(f"태그 저장 성공! 경로: {saved_path}")
                    add_to_training = st.checkbox("이 이미지와 태그를 학습 데이터에 추가하기")
                    if add_to_training:
                        with st.spinner("학습 데이터 추가 중..."):
                            if add_user_data_to_training(temp_path, tags):
                                st.success("학습 데이터 추가 성공!")
                            else:
                                st.error("학습 데이터 추가 실패!")
            with col2:
                if st.button("수정", key="tab1_edit_btn", use_container_width=True):
                    st.info("태그를 수정해주세요.")
            if os.path.exists(temp_path):
                os.remove(temp_path)
    with tabs[1]:
        st.subheader("패션 웹사이트 크롤링")
        st.write("웹사이트에서 제품 이미지 및 정보를 가져옵니다.")
        site_option = st.radio("크롤링할 사이트 선택", ["무신사","A-BLY","SHEIN","COCOBLACK","기타 사이트"])
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
            if website_url and website_url != "https://www.example.com/fashion":
                with st.spinner("데이터 크롤링 중..."):
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
                        st.success(f"{len(results)}개의 아이템 크롤링 성공!")
                        st.subheader("크롤링 결과")
                        cols = st.columns(3)
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
                                                cats = ["상의","하의","아우터","원피스","신발","액세서리"]
                                                tags.append(random.choice(cats))
                                                saved_path = save_tags(item['image_path'], tags)
                                                st.success(f"태그 저장됨: {saved_path}")
                    else:
                        st.warning("크롤링된 데이터 없음. 사이트 구조 변경 또는 크롤링 차단 가능성 있음.")
            else:
                st.error("유효한 URL을 입력해주세요.")
        with st.expander("크롤링이란?"):
            st.write("""
            웹 크롤링은 웹사이트에서 정보를 자동으로 수집하는 프로세스입니다.
            이 기능은 제품 이미지와 정보를 수집하여 분석 및 추천에 활용합니다.
            **주의:** 사이트 이용약관 확인 및 과도한 요청 주의.
            """)
    with tabs[2]:
        st.subheader("AI 코디 추천")
        st.write("무신사 데이터를 활용한 스타일 및 색상 기반 코디 추천 시스템입니다.")
        with st.spinner("데이터 로드 중..."):
            fashion_data = load_fashion_data()
            if not fashion_data.empty:
                st.success(f"{len(fashion_data)} 개의 패션 아이템 로드 완료!")
                col1, col2 = st.columns(2)
                with col1:
                    selected_style = st.selectbox("스타일 선택", STYLE_OPTIONS, key="tab3_style_select")
                    selected_season = st.radio("계절 선택", ["봄","여름","가을","겨울"], key="tab3_season_radio")
                with col2:
                    base_color = st.selectbox("메인 컬러 선택", [None] + list(COLOR_MAP.keys()), key="tab3_color_select")
                    gender = st.radio("성별", ["남성","여성","공용"], key="tab3_gender_radio")
                if st.button("코디 추천받기", key="tab3_recommend_button"):
                    st.info("코디 추천 중...")
                    clothing_type = "상의"
                    tags = [selected_style, selected_season]
                    if base_color:
                        tags.append(base_color)
                    try:
                        outfits = db.get_all_outfits()
                        if outfits is None:
                            outfits = []
                    except Exception as e:
                        print(f"DB 코디 로드 오류: {e}")
                        outfits = []
                    if outfits:
                        selected_outfits = []
                        for outfit in outfits:
                            outfit_id, style, season, outfit_base_color, outfit_json, created_at = outfit
                            outfit_data = json.loads(outfit_json)
                            match_score = 0
                            if selected_style in style:
                                match_score += 2
                                if selected_season in season:
                                    match_score += 2
                            selected_colors = tags
                            if any(color in outfit_base_color for color in selected_colors if color in COLOR_MAP):
                                match_score += 2
                            if clothing_type in str(outfit_json):
                                match_score += 1
                            if match_score >= 3:
                                selected_outfits.append((outfit_data, match_score))
                        selected_outfits.sort(key=lambda x: x[1], reverse=True)
                        top_outfits = selected_outfits[:3] if len(selected_outfits) >= 3 else selected_outfits
                        if top_outfits:
                            st.success("추천 완료!")
                            col1, col2, col3 = st.columns(3)
                            for i, (outfit_data, score) in enumerate(top_outfits):
                                with [col1, col2, col3][i]:
                                    representative_image = None
                                    for category, item in outfit_data.items():
                                        if 'image_url' in item and item['image_url']:
                                            representative_image = item['image_url']
                                            break
                                    if representative_image:
                                        st.image(representative_image, caption=f"추천 코디 {i+1}")
                                    else:
                                        st.image("https://via.placeholder.com/200x300/f0f0f0?text=추천코디", caption=f"추천 코디 {i+1}")
                                    outfit_info = "".join([f"- {category}: {item['name']}<br>" for category, item in outfit_data.items()])
                                    st.markdown(f"<div style='font-size:small'>{outfit_info}</div>", unsafe_allow_html=True)
                        else:
                            st.info("조건에 맞는 코디 없음. 새로운 코디 생성 중...")
                            new_outfit = generate_outfit(fashion_data, style=selected_style, base_color=base_color)
                            if new_outfit:
                                st.success("새 코디 생성 완료!")
                                display_outfit(new_outfit)
                            else:
                                st.warning("저장된 코디 없음.")
    # "저장된 코디" 탭: 샘플 코디 자동 생성
    if st.button("샘플 코디 50개 자동 생성", key="data_sample_outfit_btn"):
        with st.spinner("샘플 코디 생성 중..."):
            created = generate_multiple_outfits(50)
            if created > 0:
                st.success(f"총 {created}개의 샘플 코디 생성 완료!")
            else:
                st.warning("코디 생성 실패. 데이터 확인 요망.")

# ------------------------ 모델 관련 기능 ------------------------
if st.sidebar.checkbox("학습 데이터에 추가 (이미지 업로드 시)"):
    st.subheader("학습 데이터 추가")
    user_uploaded = st.file_uploader("학습 데이터용 이미지 업로드", type=["png","jpg","jpeg"])
    if user_uploaded:
        user_img = Image.open(user_uploaded).convert("RGB")
        st.image(user_img, caption="학습용 이미지", use_container_width=True)
        temp_user_path = "temp_user_image.jpg"
        user_img.save(temp_user_path, format="JPEG")
        user_tags_input = st.text_input("태그 입력 (쉼표로 구분)")
        if st.button("학습 데이터에 추가"):
            tags_list = [t.strip() for t in user_tags_input.split(",") if t.strip()]
            if add_user_data_to_training(temp_user_path, tags_list):
                st.success("학습 데이터 추가 성공!")
            else:
                st.error("학습 데이터 추가 실패!")
            if os.path.exists(temp_user_path):
                os.remove(temp_user_path)
