import time
import pandas as pd
import re
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from bs4 import BeautifulSoup
import os

def get_driver():
    """웹드라이버 설정 및 생성"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # 웹드라이버 탐지 방지
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # 랜덤 사용자 에이전트 설정 (Googlebot으로)
    user_agents = [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    # 브라우저 실행
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # 웹드라이버 탐지 방지를 위한 자바스크립트 실행
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def scroll_down(driver, pause_time=1.5):
    """스크롤 다운하여 동적 로딩된 상품을 로드하는 함수"""
    try:
        # 초기 높이
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # 스크롤 다운
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 페이지 로딩 대기
            time.sleep(pause_time)
            
            # 새 스크롤 높이 계산 
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # 스크롤이 더 이상 내려가지 않으면 종료
            if new_height == last_height:
                break
                
            last_height = new_height
            print("스크롤 다운 중...")
    except Exception as e:
        print(f"스크롤 중 오류 발생: {e}")

def crawl_musinsa_category(category_url, max_items=20):
    """무신사 카테고리 페이지에서 상품 정보를 크롤링"""
    print(f"크롤링 시작: {category_url}")
    
    try:
        # 웹드라이버 초기화
        driver = get_driver()
        
        # URL 접속
        driver.get(category_url)
        print("페이지 접속 완료")
        
        # 쿠키 수락 버튼이 있으면 클릭
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.accept-button"))
            ).click()
            print("쿠키 수락 버튼 클릭")
        except:
            pass
        
        # 스크롤 다운하여 더 많은 상품 로드
        scroll_down(driver)
        
        # 페이지 소스 가져와서 BeautifulSoup으로 파싱
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # 디버그: 페이지 제목 출력
        title = soup.find('title')
        print(f"페이지 제목: {title.text if title else 'N/A'}")
        
        # 최신 구조에 맞는 상품 요소 찾기
        # 1. 상품 리스트 컨테이너 찾기
        product_list = soup.select('div.list-box') or soup.select('ul.list-box') or soup.select('div.search-result')
        
        if not product_list:
            print("상품 리스트 컨테이너를 찾을 수 없습니다. HTML 구조 확인 필요")
            # HTML 확인용 파일 저장
            with open("musinsa_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("디버깅용 HTML 저장됨: musinsa_debug.html")
            driver.quit()
            return []
            
        print(f"상품 리스트 컨테이너 찾음: {len(product_list)}개")
        
        # 2. 각 상품 요소 찾기
        items = []
        for container in product_list:
            # 사용자가 제공한 클래스 정보 기반으로 요소 선택
            # 여러 형태의 요소를 시도
            container_items = (
                container.select('li.li_box') or
                container.select('li.list-item') or
                container.select('li')  # 마지막 시도
            )
            items.extend(container_items)
        
        print(f"상품 요소 찾음: {len(items)}개")
        
        results = []
        for i, item in enumerate(items[:max_items]):
            try:
                # 상품명 찾기
                product_name_elem = (
                    item.select_one('.text-body_13px_reg') or
                    item.select_one('.article_info') or
                    item.select_one('p.list_info')
                )
                
                # 브랜드명 찾기
                brand_name_elem = (
                    item.select_one('.text-etc_11px_semibold') or
                    item.select_one('.brand') or
                    item.select_one('p.item_title')
                )
                
                # 이미지 URL 찾기
                img_element = (
                    item.select_one('img') or
                    item.select_one('img.lazyload') or
                    item.select_one('img.lazy')
                )
                
                # 데이터 추출
                product_name = product_name_elem.text.strip() if product_name_elem else f"상품 {i+1}"
                brand_name = brand_name_elem.text.strip() if brand_name_elem else ""
                
                img_url = None
                if img_element:
                    # 다양한 속성 시도
                    for attr in ['src', 'data-original', 'data-src', 'data-lazy-src']:
                        if img_element.has_attr(attr):
                            img_url = img_element[attr]
                            break
                    
                    # URL이 상대경로인 경우 절대경로로 변환
                    if img_url and img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url and img_url.startswith('/'):
                        img_url = 'https://www.musinsa.com' + img_url
                
                if img_url:
                    product_info = {
                        'name': product_name,
                        'brand': brand_name,
                        'image_url': img_url,
                        'category': category_url.split('/')[-1]
                    }
                    
                    print(f"상품 추가: {product_name} ({img_url[:50]}...)")
                    results.append(product_info)
                
            except Exception as e:
                print(f"상품 처리 중 오류: {e}")
        
        driver.quit()
        print(f"총 {len(results)}개 상품 수집 완료")
        return results
        
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        try:
            driver.quit()
        except:
            pass
        return []   

# 테스트 코드
if __name__ == "__main__":
    # 예시: 상의 카테고리 URL
    category_url = "https://www.musinsa.com/categories/item/001"
    products = crawl_musinsa_category(category_url, max_items=5)
    for idx, product in enumerate(products):
        print(f"{idx+1}. {product['name']} - {product['image_url']}")

if __name__ == "__main__":
    # 디버깅용: 예시 카테고리와 URL (실제 URL을 확인 후 수정)
    category_name = "티셔츠"
    url = "https://www.musinsa.com/category/001?gf=A"
    products = crawl_category_selenium(url, category_name)
    if products:
        print(f"총 {len(products)}개 상품 수집됨")
        df = pd.DataFrame(products)
        df.to_csv("musinsa_products_selenium.csv", index=False, encoding="utf-8-sig")
        print("CSV 저장 완료")
    else:
        print("상품 데이터 수집 실패")
