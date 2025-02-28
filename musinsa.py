import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

def crawl_musinsa_ranking():
    # 무신사 랭킹 페이지 URL
    url = "https://www.musinsa.com/main/musinsa/ranking?storeCode=musinsa&sectionId=200&contentsId=&categoryCode=000"
    headers = {'User-Agent': 'Mozilla/5.0'}

    # 페이지 요청
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"HTTP 오류 발생: {response.status_code}")
        return None

    # HTML 파싱
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 랭킹 아이템 추출 (예: ul.list 안의 li)
    # 실제 구조에 맞춰 조정 필요
    items = soup.select('ul.list li')
    data = []

    for item in items:
        # 순위
        rank_tag = item.select_one('span.num')
        
        # 브랜드
        brand_tag = item.select_one('p.list_brand')
        
        # 제품명
        product_tag = item.select_one('p.list_info')
        
        # 이미지 (예시: p.list_img > a > img)
        # 개발자 도구에서 실제 태그 구조 확인 후 수정 필요
        img_tag = item.select_one('p.list_img img')

        if rank_tag and product_tag and brand_tag and img_tag:
            rank = rank_tag.get_text(strip=True)
            brand = brand_tag.get_text(strip=True)
            product = product_tag.get_text(strip=True)
            
            # 이미지 URL 가져오기
            # 무신사 사이트에서는 data-original 속성에 실제 이미지 경로가 있을 수도 있으니 확인
            img_url = img_tag.get('data-original') or img_tag.get('src')
            
            data.append({
                '순위': rank,
                '브랜드': brand,
                '제품명': product,
                '이미지URL': img_url
            })

    return data

def download_images(data, save_folder="musinsa_images"):
    """data 리스트에서 '이미지URL' 키를 읽어와 로컬에 저장"""
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    
    for i, item in enumerate(data):
        img_url = item.get('이미지URL')
        if not img_url:
            continue
        # 확장자 추출(단순 예시)
        ext = img_url.split('?')[0].split('.')[-1]
        if len(ext) > 4:
            ext = 'jpg'
        
        filename = f"image_{i}.{ext}"
        filepath = os.path.join(save_folder, filename)
        
        try:
            response = requests.get(img_url, stream=True)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                # 데이터에 로컬 저장 경로도 넣어줌
                item['이미지파일'] = filepath
                print(f"[{i}] 이미지 다운로드 완료: {filepath}")
            else:
                print(f"[{i}] 이미지 다운로드 실패 (HTTP {response.status_code}): {img_url}")
        except Exception as e:
            print(f"[{i}] 오류 발생: {e} (URL: {img_url})")

if __name__ == "__main__":
    ranking_data = crawl_musinsa_ranking()
    if ranking_data:
        df = pd.DataFrame(ranking_data)
        
        # CSV 저장
        df.to_csv("musinsa_ranking_with_images.csv", index=False, encoding='utf-8-sig')
        print("무신사 랭킹 데이터를 musinsa_ranking_with_images.csv 파일로 저장했습니다.")

        # 이미지 다운로드
        download_images(ranking_data, save_folder="musinsa_images")

        # 이미지 다운로드 후 로컬 파일 경로까지 포함한 내용을 다시 CSV에 저장
        df = pd.DataFrame(ranking_data)
        df.to_csv("musinsa_ranking_with_images_local.csv", index=False, encoding='utf-8-sig')
        print("이미지 파일 경로를 포함하여 musinsa_ranking_with_images_local.csv 파일로 저장했습니다.")
    else:
        print("데이터를 가져오지 못했습니다.")
