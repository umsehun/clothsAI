# musinsa_data_collector.py 파일 생성
from fashion_db import FashionDB
from utils.musinsa_api import fetch_api
from modules.tag_utils import extract_musinsa_tags
import json

db = FashionDB()

# 무신사 API URL
api_urls = [
    "https://api.musinsa.com/api2/hm/v4/pans/recommend?storeCode=musinsa",
    "https://api.musinsa.com/api2/hm/v4/pans/ranking?storeCode=musinsa",
    "https://api.musinsa.com/api2/hm/v2/pans/sale?storeCode=musinsa",
    # 더 많은 카테고리 URL 추가 가능
]

def collect_musinsa_data():
    """무신사 API에서 데이터를 수집하고 DB에 저장"""
    total_saved = 0
    
    for url in api_urls:
        print(f"URL 처리 중: {url}")
        data = fetch_api(url)
        
        if not data:
            print(f"URL에서 데이터를 가져오지 못했습니다: {url}")
            continue
            
        # 상품 데이터 추출 및 저장
        if isinstance(data, dict) and "data" in data and "modules" in data["data"]:
            modules = data["data"]["modules"]
            
            for module in modules:
                # 상품 데이터 찾기
                product_keys = ["items", "products", "list", "goods"]
                for key in product_keys:
                    if key in module and isinstance(module[key], list):
                        products = module[key]
                        
                        for product in products:
                            try:
                                # 상품 정보 추출
                                name = product.get("productName", "")
                                brand = product.get("brandName", "")
                                img_url = ""
                                
                                # 이미지 URL 찾기 
                                if "image" in product and isinstance(product["image"], dict):
                                    img_url = product["image"].get("url", "")
                                elif "image" in product and isinstance(product["image"], str):
                                    img_url = product["image"]
                                else:
                                    img_url = product.get("imageUrl", "")
                                
                                if name and img_url:
                                    # 태그 추출
                                    product_data = {
                                        "productName": name,
                                        "brandName": brand
                                    }
                                    tags = extract_musinsa_tags(product_data)
                                    
                                    # DB에 저장
                                    db.save_crawled_item(
                                        name=name,
                                        image_path=img_url,  # 이미지 URL만 저장
                                        source_url="",
                                        source_site="musinsa_api",
                                        tags=tags
                                    )
                                    total_saved += 1
                                    
                            except Exception as e:
                                print(f"상품 처리 중 오류: {e}")
    
    print(f"총 {total_saved}개의 상품 데이터를 저장했습니다.")
    return total_saved

if __name__ == "__main__":
    collect_musinsa_data()