import json
import os
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
import numpy as np
from collections import Counter
from wordcloud import WordCloud
import sqlite3
from fashion_db import FashionDB

# 한글 폰트 설정 (Windows)
font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
font_name = font_manager.FontProperties(fname=font_path).get_name()
plt.rc('font', family=font_name)
plt.rc('axes', unicode_minus=False)

# DB 연결
db = FashionDB()

def analyze_tags():
    """저장된 태그 분석"""
    print("태그 분석 시작...")
    
    # 모든 태그 가져오기
    all_items = db.get_all_tags()
    crawled_items = db.get_crawled_items(limit=10000)
    
    if not all_items and not crawled_items:
        print("분석할 태그 데이터가 없습니다.")
        return
    
    # 모든 태그 수집
    all_tags = []
    
    # 태그 테이블에서 태그 추출
    for item in all_items:
        _, _, _, tags_json, _ = item
        if tags_json:
            tags = json.loads(tags_json)
            all_tags.extend(tags)
    
    # 크롤링 테이블에서 태그 추출
    for item in crawled_items:
        _, _, _, _, _, tags_json, _ = item
        if tags_json:
            tags = json.loads(tags_json)
            all_tags.extend(tags)
    
    # 태그 카운트
    tag_counts = Counter(all_tags)
    
    # 상위 30개 태그 추출
    top_tags = tag_counts.most_common(30)
    
    # 출력
    print("\n상위 30개 태그:")
    for tag, count in top_tags:
        print(f"{tag}: {count}회")
    
    # 카테고리 태그 분포 분석
    categories = ['상의', '하의', '아우터', '원피스', '신발', '액세서리']
    category_counts = {cat: tag_counts[cat] for cat in categories if cat in tag_counts}
    
    # 색상 태그 분포 분석
    colors = ['검정', '흰색', '회색', '베이지', '빨강', '파랑', '초록', '노랑', '보라', '핑크', '갈색', '주황']
    color_counts = {color: tag_counts[color] for color in colors if color in tag_counts}
    
    # 시각화 출력
    plt.figure(figsize=(12, 8))
    
    # 상위 20개 태그 막대 그래프
    plt.subplot(2, 2, 1)
    tags, counts = zip(*tag_counts.most_common(20))
    y_pos = np.arange(len(tags))
    plt.barh(y_pos, counts, align='center')
    plt.yticks(y_pos, tags)
    plt.xlabel('빈도수')
    plt.title('상위 20개 태그')
    
    # 카테고리 분포 파이 차트
    plt.subplot(2, 2, 2)
    plt.pie(list(category_counts.values()), labels=list(category_counts.keys()), autopct='%1.1f%%')
    plt.title('카테고리 분포')
    
    # 색상 분포 막대 그래프
    plt.subplot(2, 2, 3)
    plt.bar(list(color_counts.keys()), list(color_counts.values()))
    plt.xticks(rotation=45)
    plt.title('색상 분포')
    
    # 워드클라우드
    plt.subplot(2, 2, 4)
    try:
        wordcloud = WordCloud(
            font_path=font_path,
            width=800, height=400,
            background_color='white'
        ).generate_from_frequencies(tag_counts)
        
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('태그 워드클라우드')
    except Exception as e:
        print(f"워드클라우드 생성 실패: {e}")
    
    plt.tight_layout()
    plt.savefig('tag_analysis.png', dpi=300)
    print("\n분석 결과가 'tag_analysis.png' 파일로 저장되었습니다.")
    plt.close()
    
    # 태그 상관관계 분석
    print("\n태그 상관관계 분석...")
    tag_pairs = []
    
    # 크롤링된 아이템에서 태그 쌍 추출
    for item in crawled_items:
        _, _, _, _, _, tags_json, _ = item
        if tags_json:
            item_tags = json.loads(tags_json)
            
            # 모든 가능한 태그 쌍 추출 (순서 무관)
            for i in range(len(item_tags)):
                for j in range(i+1, len(item_tags)):
                    # 알파벳 순으로 정렬하여 저장
                    pair = tuple(sorted([item_tags[i], item_tags[j]]))
                    tag_pairs.append(pair)
    
    # 태그 쌍 카운트
    pair_counts = Counter(tag_pairs)
    
    # 상위 20개 태그 쌍 출력
    print("\n상위 20개 태그 쌍:")
    for pair, count in pair_counts.most_common(20):
        print(f"{pair[0]} + {pair[1]}: {count}회")
        
    # 상위 15개 태그 쌍 시각화
    top_pairs = pair_counts.most_common(15)
    plt.figure(figsize=(12, 6))
    
    pair_names = [f"{p[0][0]}\n+\n{p[0][1]}" for p in top_pairs]
    pair_values = [p[1] for p in top_pairs]
    
    plt.bar(range(len(top_pairs)), pair_values)
    plt.xticks(range(len(top_pairs)), pair_names, rotation=45)
    plt.title('상위 태그 조합')
    plt.xlabel('태그 조합')
    plt.ylabel('동시 출현 횟수')
    plt.tight_layout()
    plt.savefig('tag_pairs.png', dpi=300)
    print("태그 상관관계 분석 결과가 'tag_pairs.png' 파일로 저장되었습니다.")
    plt.close()
    
    # 카테고리별 색상 분석
    print("\n카테고리별 색상 분석...")
    category_color_map = {cat: {} for cat in categories}
    
    for item in crawled_items:
        _, _, _, _, _, tags_json, _ = item
        if tags_json:
            item_tags = json.loads(tags_json)
            item_categories = [tag for tag in item_tags if tag in categories]
            item_colors = [tag for tag in item_tags if tag in colors]
            
            # 카테고리별 색상 매핑
            for category in item_categories:
                for color in item_colors:
                    if color not in category_color_map[category]:
                        category_color_map[category][color] = 0
                    category_color_map[category][color] += 1
    
    # 시각화 (카테고리별 상위 4개 색상)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    for i, category in enumerate(categories):
        if i < len(axes):
            color_data = category_color_map[category]
            if color_data:
                # 상위 색상만 표시
                top_colors = dict(sorted(color_data.items(), key=lambda x: x[1], reverse=True)[:4])
                axes[i].pie(list(top_colors.values()), labels=list(top_colors.keys()), autopct='%1.1f%%')
                axes[i].set_title(f'{category} 주요 색상')
            else:
                axes[i].text(0.5, 0.5, '데이터 없음', ha='center', va='center')
                axes[i].axis('off')
    
    plt.tight_layout()
    plt.savefig('category_colors.png', dpi=300)
    print("카테고리별 색상 분석 결과가 'category_colors.png' 파일로 저장되었습니다.")
    plt.close()

    # 스타일별 인기 아이템 분석
    print("\n스타일별 인기 아이템 분석...")
    styles = ['미니멀', '캐주얼', '스트릿', '빈티지', '스포티', '모던', '럭셔리']
    style_items = {style: [] for style in styles}
    
    for item in crawled_items:
        item_id, name, image_path, _, _, tags_json, _ = item
        if tags_json:
            item_tags = json.loads(tags_json)
            for style in styles:
                if style in item_tags:
                    style_items[style].append({
                        'id': item_id,
                        'name': name,
                        'image_path': image_path
                    })
    
    # 각 스타일별 아이템 수 출력
    for style, items in style_items.items():
        print(f"{style}: {len(items)}개 아이템")
    
    # 결과를 JSON 파일로 저장
    with open('style_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(style_items, f, ensure_ascii=False, indent=2)
    print("스타일 분석 결과가 'style_analysis.json' 파일로 저장되었습니다.")

if __name__ == "__main__":
    analyze_tags()