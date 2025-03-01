import time
import pandas as pd
import sqlite3
import re
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

def get_driver():
    """
    웹드라이버 설정 및 생성
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # 웹드라이버 탐지 방지
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # 랜덤 사용자 에이전트 설정
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # 웹드라이버 탐지 방지를 위한 자바스크립트 실행
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def scroll_down(driver, pause_time=None):
    """
    스크롤 다운하여 더 많은 상품을 로딩하는 함수
    """
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
        max_scrolls = 5  # 최대 스크롤 횟수 제한
        scrolls = 0
        
        while scrolls < max_scrolls:
            driver.execute_script("window.scrollBy(0, window.innerHeight/2);")  # 부드럽게 스크롤
            if pause_time is None:  # 랜덤 대기 시간
                time.sleep(random.uniform(1.0, 3.0))
            else:
                time.sleep(pause_time)
            
            driver.execute_script("window.scrollBy(0, window.innerHeight/2);")  # 부드럽게 스크롤
            if pause_time is None:
                time.sleep(random.uniform(1.0, 3.0))
            else:
                time.sleep(pause_time)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scrolls += 1
    except Exception as e:
        print(f"스크롤 중 오류: {str(e)}")

def extract_musinsa_tags(product_url, driver=None):
    """
    무신사 제품 페이지에서 태그 정보 추출
    """
    should_quit = False
    if driver is None:
        driver = get_driver()
        should_quit = True
    
    try:
        driver.get(product_url)
        wait = WebDriverWait(driver, 10)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        except TimeoutException:
            print(f"태그 페이지 로딩 시간 초과: {product_url}")
            return []
        
        # 태그 정보 추출 시도
        tags = []
        try:
            # 여러 태그 선택자 시도
            selectors = [
                "p.product_article_contents > a.listItem",
                "div.product_tags > a",
                "div.article_info_content > a",
                "div.product_info_section > div.article_info_content > a"
            ]
            
            for selector in selectors:
                tag_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if tag_elements:
                    for tag_el in tag_elements:
                        tag_text = tag_el.text.strip()
                        if tag_text:
                            tags.append(tag_text)
                    if tags:  # 태그를 찾았으면 반복 중단
                        break
        except Exception as e:
            print(f"태그 추출 중 오류: {e}")
        
        return tags
    except Exception as e:
        print(f"URL 처리 중 오류 ({product_url}): {e}")
        return []
    finally:
        if should_quit and driver:
            driver.quit()

def crawl_category_selenium(url, category_name, max_retries=3):
    """
    무신사 상품을 크롤링하는 함수
    """
    for attempt in range(max_retries):
        try:
            driver = get_driver()
            
            # 페이지 로드
            driver.get(url)
            
            # 쿠키 배너 닫기 시도
            try:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.close"))
                ).click()
                print("쿠키 배너 닫기 성공")
            except:
                pass  # 쿠키 배너가 없거나, 닫기 버튼이 다른 형태일 수 있음
            
            # 페이지 로드 대기
            try:
                wait = WebDriverWait(driver, 20)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-list div.list-box, ul.list-box, div.list-box > div.item")))
            except TimeoutException:
                print(f"[{category_name}] 항목 로드 시간 초과 (시도 {attempt+1}/{max_retries})")
                driver.quit()
                if attempt < max_retries - 1:
                    delay = random.uniform(5, 10)
                    print(f"{delay:.1f}초 후 재시도...")
                    time.sleep(delay)
                    continue
                else:
                    return []
                
            # 스크롤 다운
            scroll_down(driver)
            
            # 항목 가져오기
            items = []
            
            # 다양한 CSS 선택자 시도
            selectors = [
                "div.search-list div.list-box div.item",
                "div.list-box div.item",
                "ul.list-box li.li_box",
                "div.list-box > div.item"
            ]
            
            for selector in selectors:
                items = driver.find_elements(By.CSS_SELECTOR, selector)
                if items:
                    break
            
            if not items:
                print(f"[{category_name}] 항목을 찾을 수 없음 (시도 {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    driver.quit()
                    delay = random.uniform(5, 10)
                    print(f"{delay:.1f}초 후 재시도...")
                    time.sleep(delay)
                    continue
                else:
                    driver.quit()
                    return []
                
            print(f"[{category_name}] {len(items)}개 상품 발견")
            
            products = []
            for it in items:
                product_data = extract_product_data(it, category_name, url)
                if product_data:
                    products.append(product_data)
                
                # 크롤링 속도 제한 (랜덤 딜레이)
                time.sleep(random.uniform(0.1, 0.5))
            
            driver.quit()
            return products
            
        except KeyboardInterrupt:
            print("사용자에 의해 중단됨")
            raise
        except Exception as e:
            print(f"[{category_name}] 크롤링 중 오류 (시도 {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                if 'driver' in locals() and driver:
                    driver.quit()
                delay = random.uniform(5, 10)
                print(f"{delay:.1f}초 후 재시도...")
                time.sleep(delay)
            else:
                if 'driver' in locals() and driver:
                    driver.quit()
                print(f"[{category_name}] 최대 재시도 횟수 초과, 건너뜁니다.")
                return []
    
    return []  # 기본 반환값

def extract_product_data(item_element, category_name, url):
    """
    상품 요소에서 데이터 추출
    """
    try:
        # 브랜드 추출
        brand = "N/A"
        brand_selectors = [
            "span.text-etc_11px_semibold",
            "p.item_title", 
            "p.brand_name",
            "div.brand > a"
        ]
        
        for selector in brand_selectors:
            try:
                brand_el = item_element.find_element(By.CSS_SELECTOR, selector)
                brand = brand_el.text.strip()
                if brand:
                    break
            except:
                continue
        
        # 상품명 추출
        product_name = "N/A"
        name_selectors = [
            "span.text-body_13px_reg",
            "p.list_info", 
            "p.item_title > a",
            "p.item_name"
        ]
        
        for selector in name_selectors:
            try:
                product_el = item_element.find_element(By.CSS_SELECTOR, selector)
                product_name = product_el.text.strip()
                if product_name:
                    break
            except:
                continue
        
        # 이미지 URL 추출
        img_url = "N/A"
        img_selectors = [
            "img.max-w-full", 
            "img.lazyload", 
            "img"
        ]
        
        for selector in img_selectors:
            try:
                img_el = item_element.find_element(By.CSS_SELECTOR, selector)
                img_url = img_el.get_attribute("data-original") or img_el.get_attribute("src") or img_el.get_attribute("data-src")
                if img_url:
                    break
            except:
                continue
        
        # 상품 URL 추출
        product_url = "N/A"
        url_selectors = [
            "a.img-block",
            "a.list_img",
            "p.item_title > a", 
            "a"
        ]
        
        for selector in url_selectors:
            try:
                link_el = item_element.find_element(By.CSS_SELECTOR, selector)
                product_url = link_el.get_attribute("href")
                if product_url:
                    break
            except:
                continue
        
        # 태그 추출 (필요한 경우 활성화)
        tags = []
        # if product_url != "N/A":
        #     tags = extract_musinsa_tags(product_url)
        
        return {
            "category": category_name,
            "brand": brand,
            "product": product_name,
            "img_url": img_url,
            "product_url": product_url,
            "category_url": url,
            "tags": ",".join(tags) if tags else ""
        }
    
    except Exception as e:
        print(f"상품 데이터 추출 중 오류: {str(e)}")
        return None

def main():
    """
    카테고리별 크롤링 실행 및 저장
    """
    category_urls = [
        ("티셔츠", "https://www.musinsa.com/category/001001?gf=A"),
        ("셔츠", "https://www.musinsa.com/category/001002?gf=A"),
        ("니트/스웨터", "https://www.musinsa.com/category/001005?gf=A"),
        ("맨투맨/스웨트셔츠", "https://www.musinsa.com/category/001010?gf=A"),
        ("후드 티셔츠", "https://www.musinsa.com/category/001011?gf=A"),
        ("블라우스", "https://www.musinsa.com/category/001013?gf=A"),
        
        ("청바지", "https://www.musinsa.com/category/003001?gf=A"),
        ("슬랙스", "https://www.musinsa.com/category/003002?gf=A"),
        ("면바지", "https://www.musinsa.com/category/003003?gf=A"),
        ("숏 팬츠", "https://www.musinsa.com/category/003004?gf=A"),
        ("트레이닝 팬츠", "https://www.musinsa.com/category/003005?gf=A"),
        
        ("코트", "https://www.musinsa.com/category/002001?gf=A"),
        ("재킷/블레이저", "https://www.musinsa.com/category/002002?gf=A"),
        ("패딩/다운점퍼", "https://www.musinsa.com/category/002003?gf=A"),
        ("후드 집업", "https://www.musinsa.com/category/002004?gf=A"),
        
        ("스니커즈", "https://www.musinsa.com/category/004001?gf=A"),
        ("구두", "https://www.musinsa.com/category/004002?gf=A"),
        ("부츠", "https://www.musinsa.com/category/004003?gf=A"),
        ("로퍼", "https://www.musinsa.com/category/004004?gf=A"),
        ("샌들", "https://www.musinsa.com/category/004005?gf=A"),
        
        ("가방", "https://www.musinsa.com/category/005001?gf=A"),
        ("지갑", "https://www.musinsa.com/category/005002?gf=A"),
        ("모자", "https://www.musinsa.com/category/005003?gf=A"),
        ("벨트", "https://www.musinsa.com/category/005004?gf=A"),
        ("시계", "https://www.musinsa.com/category/005005?gf=A"),
        ("장갑", "https://www.musinsa.com/category/005006?gf=A"),
    ]
    
    all_products = []
    success_count = 0
    fail_count = 0
    
    try:
        for cat, link in category_urls:
            print(f"\n[{cat}] 크롤링 시작: {link}")
            result = crawl_category_selenium(link, cat)
            
            if result:
                print(f"[{cat}] {len(result)}개 상품 성공적으로 수집")
                all_products.extend(result)
                success_count += 1
                
                # 진행 상황 저장 (중간 백업)
                if len(all_products) > 0 and len(all_products) % 100 == 0:
                    temp_df = pd.DataFrame(all_products)
                    temp_df.to_csv(f"musinsa_products_temp_{len(all_products)}.csv", 
                                  index=False, encoding="utf-8-sig")
                    print(f"임시 데이터 {len(all_products)}개 저장 완료")
            else:
                print(f"[{cat}] 상품 수집 실패")
                fail_count += 1
            
            # 카테고리 사이의 지연 시간 추가 (봇 감지 방지)
            delay = random.uniform(3, 8)
            print(f"다음 카테고리까지 {delay:.1f}초 대기...")
            time.sleep(delay)
    
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨. 지금까지 수집한 데이터를 저장합니다.")
    
    finally:
        # 결과 저장
        if all_products:
            print(f"\n총 {len(all_products)}개 상품 데이터 수집 완료")
            print(f"성공: {success_count}개 카테고리, 실패: {fail_count}개 카테고리")
            
            df = pd.DataFrame(all_products)
            df.to_csv("musinsa_products_selenium.csv", index=False, encoding="utf-8-sig")
            print("CSV 저장 완료: musinsa_products_selenium.csv")
            
            try:
                conn = sqlite3.connect("fashion_ai.db")
                df.to_sql("products", conn, if_exists="replace", index=False)
                conn.commit()
                conn.close()
                print("DB 저장 완료: fashion_ai.db")
            except Exception as e:
                print(f"DB 저장 중 오류: {str(e)}")
        else:
            print("수집된 데이터가 없습니다.")

if __name__ == "__main__":
    main()