# modules/recommendation.py
import streamlit as st
import pandas as pd
from modules.data_loader import categorize_fashion_items, extract_item_color

def generate_outfit(fashion_df: pd.DataFrame, style: str = None, base_color: str = None) -> dict:
    """스타일과 색상을 기반으로 코디를 생성"""
    if fashion_df.empty:
        return {}
    
    categorized_df = categorize_fashion_items(fashion_df)
    color_df = extract_item_color(categorized_df)
    
    # base_color가 있을 때만 필터링
    if base_color:
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
            
            # 상품명, 브랜드, 가격 정보 추출
            name = None
            for name_col in ['productName', '제품명', 'name']:
                if name_col in selected_item and pd.notna(selected_item[name_col]):
                    name = selected_item[name_col]
                    break
            
            brand = None
            for brand_col in ['brandName', '브랜드', 'brand']:
                if brand_col in selected_item and pd.notna(selected_item[brand_col]):
                    brand = selected_item[brand_col]
                    break
            
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

def display_outfit(outfit: dict) -> None:
    """생성된 코디를 스트림릿으로 표시"""
    if not outfit:
        st.warning("코디를 생성할 수 있는 충분한 데이터가 없습니다.")
        return
    st.subheader("🎨 AI가 추천하는 코디")
    total_price = 0
    category_order = ['상의', '하의', '아우터', '원피스', '신발', '액세서리']
    outfit_items = [(cat, outfit[cat]) for cat in category_order if cat in outfit]
    for i in range(0, len(outfit_items), 3):
        cols = st.columns(3)
        for j, (category, item) in enumerate(outfit_items[i:i+3]):
            with cols[j]:
                st.subheader(f"👕 {category}")
                st.write(f"**{item['name']}**")
                st.write(f"브랜드: {item['brand']}")
                if 'price' in item and item['price']:
                    try:
                        price_int = int(item['price'])
                        st.write(f"가격: {price_int:,}원")
                        total_price += price_int
                    except:
                        st.write(f"가격: {item['price']}")
                if item.get('image_url'):
                    try:
                        st.image(item['image_url'], use_container_width=True)
                    except:
                        st.write("이미지를 불러올 수 없습니다.")
                else:
                    st.write("이미지 없음")
    st.subheader(f"총 예상 가격: {total_price:,}원")
