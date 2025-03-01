# modules/crawling.py
import os
import time
import requests
import streamlit as st
from bs4 import BeautifulSoup

def crawl_fashion_data(url: str, max_items: int = 10) -> list:
    """패션 웹사이트에서 이미지와 정보를 크롤링하는 기본 함수"""
    try:
        st.info("크롤링을 시작합니다. 이 작업은 몇 분 정도 소요될 수 있습니다.")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            image_elements = soup.select('img.product-image')
            product_names = soup.select('div.product-name')
            results = []
            for i, (img, name) in enumerate(zip(image_elements, product_names)):
                if i >= max_items:
                    break
                img_url = img.get('src', '')
                product_name = name.text.strip()
                if img_url and img_url.startswith('http'):
                    img_response = requests.get(img_url, headers=headers)
                    if img_response.status_code == 200:
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
        st.error(f"크롤링 중 오류 발생: {e}")
        return []

def crawl_musinsa(url: str, max_items: int = 10) -> list:
    """무신사 웹사이트 크롤링 함수"""
    try:
        st.info("무신사 데이터 크롤링을 시작합니다...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36'
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
        st.error(f"크롤링 중 오류 발생: {e}")
        return []

def crawl_ably(url: str, max_items: int = 10) -> list:
    """A-BLY 웹사이트 크롤링 함수"""
    try:
        st.info("A-BLY 데이터 크롤링을 시작합니다...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36'
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
        st.error(f"크롤링 중 오류 발생: {e}")
        return []

def crawl_shein(url: str, max_items: int = 10) -> list:
    """SHEIN 웹사이트 크롤링 함수"""
    try:
        st.info("SHEIN 데이터 크롤링을 시작합니다...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36'
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
        st.error(f"크롤링 중 오류 발생: {e}")
        return []

def crawl_cocoblack(url: str, max_items: int = 10) -> list:
    """COCOBLACK 웹사이트 크롤링 함수"""
    try:
        st.info("COCOBLACK 데이터 크롤링을 시작합니다...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36'
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
        st.error(f"크롤링 중 오류 발생: {e}")
        return []
