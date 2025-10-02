"""Creait - Instagram 광고 제품 신뢰도 분석 시스템 메인"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import asyncio
import pprint
from loguru import logger
# Playwright 스크래퍼 사용
from src.scraper.oliveyoung_scraper import OliveYoungScraper
from src.database import init_db, save_product_info, get_product_images_with_ids, save_image_text
from src.image_text_extractor import ImageTextExtractor


async def extract_image_texts(product_id: int):
    """제품의 상세 이미지에서 텍스트를 추출합니다."""
    logger.info(f"=== 제품 ID {product_id}의 이미지 텍스트 추출 시작 ===")
    
    try:
        # 해당 제품의 이미지들 가져오기
        product_images = get_product_images_with_ids(product_id)
        
        if not product_images:
            logger.warning(f"제품 ID {product_id}에 대한 이미지가 없습니다.")
            return
        
        logger.info(f"총 {len(product_images)}개의 이미지에서 텍스트 추출을 시작합니다.")
        
        extractor = ImageTextExtractor()
        image_urls = [img[3] for img in product_images]
        
        # 여러 이미지에서 텍스트 일괄 추출
        extracted_texts_map = await extractor.extract_text_from_multiple_images(image_urls)
        
        successful_count = 0
        
        # 결과를 순회하며 데이터베이스에 저장
        for i, (image_id, _, product_name, image_url) in enumerate(product_images, 1):
            logger.info(f"\n--- 이미지 {i}/{len(product_images)} 처리 ---")
            logger.info(f"이미지 ID: {image_id}, URL: {image_url}")

            extracted_text = extracted_texts_map.get(image_url, "")
            
            # 성공적인 추출인지 확인
            if extracted_text and extracted_text.strip() and len(extracted_text.strip()) > 5:
                # 거부 응답 확인
                invalid_responses = [
                    "i'm unable to", "i can't assist", "i'm sorry", "i cannot",
                    "unable to provide", "can't help", "죄송하지만", "추출할 수 없습니다"
                ]
                
                if any(invalid in extracted_text.lower() for invalid in invalid_responses):
                    logger.warning(f"이미지 {i}: OpenAI가 텍스트 추출을 거부")
                    continue
                
                # 데이터베이스에 저장
                success = save_image_text(image_id, product_id, image_url, extracted_text)
                
                if success:
                    logger.info(f"✅ 이미지 {i}: 텍스트 추출 및 저장 성공!")
                    logger.info(f"추출된 텍스트 (처음 100자): {extracted_text[:100]}...")
                    successful_count += 1
                else:
                    logger.error(f"❌ 이미지 {i}: 데이터베이스 저장 실패")
            else:
                logger.warning(f"❌ 이미지 {i}: 빈 텍스트 또는 너무 짧은 텍스트")

        logger.info(f"\n=== 이미지 텍스트 추출 완료 ===")
        logger.info(f"성공: {successful_count}/{len(product_images)}개")
        
    except Exception as e:
        logger.error(f"이미지 텍스트 추출 중 오류: {e}")

async def main():
    """메인 실행 함수"""
    # 데이터베이스 초기화 (테이블이 없으면 생성)
    init_db()

    # 사용자로부터 URL 입력받기
    url = input("스크래핑할 올리브영 제품 URL을 입력하세요: ")
    if not url or "oliveyoung.co.kr" not in url:
        logger.warning("유효한 올리브영 URL이 아닙니다. 프로그램을 종료합니다.")
        return

    logger.info(f"입력된 URL: {url}")
    logger.info("=== Olive Young 스크래퍼 시작 ===")

    product_id = None

    try:
        async with OliveYoungScraper(headless=False) as scraper:
            # 제품 정보 스크래핑
            product = await scraper.scrape(url, max_reviews=200)

            # 결과 출력
            logger.info("\n=== 스크래핑 결과 (화면 출력) ===")
            pprint.pprint(product.__dict__)

            # 데이터베이스에 저장
            logger.info("\n=== 데이터베이스에 결과 저장 시작 ===")
            
            # 저장 전 product_id 확인
            import sqlite3
            from pathlib import Path
            
            DB_FILE = Path("creait.db")
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            
            # URL로 기존 제품 확인
            cur.execute("SELECT id FROM products WHERE url = ?", (url,))
            result = cur.fetchone()
            con.close()
            
            save_product_info(product, url)
            
            # 저장 후 product_id 다시 확인
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            cur.execute("SELECT id FROM products WHERE url = ?", (url,))
            result = cur.fetchone()
            if result:
                product_id = result[0]
            con.close()

    except Exception as e:
        logger.error(f"스크래핑 과정에서 오류가 발생했습니다: {e}")
        return
    
    # 이미지 텍스트 추출 진행 여부 확인
    if product_id:
        extract_images = input("\n상세 이미지에서 텍스트를 추출하시겠습니까? (y/N): ").strip().lower()
        
        if extract_images == 'y':
            try:
                logger.info(f"총 {len(product.detail_images) if hasattr(product, 'detail_images') else '알 수 없는 수의'}개 이미지에서 텍스트 추출을 시작합니다.")
                logger.info("이 작업은 시간이 오래 걸릴 수 있습니다. (각 이미지당 약 3-5초)")
                
                await extract_image_texts(product_id)
            except Exception as e:
                logger.error(f"이미지 텍스트 추출 중 오류: {e}")
        else:
            logger.info("이미지 텍스트 추출을 건너뜁니다.")
            logger.info("나중에 텍스트 추출을 원하시면 process_product_images.py를 실행하세요.")
    else:
        logger.error("제품 ID를 찾을 수 없어 이미지 텍스트 추출을 수행할 수 없습니다.")


if __name__ == "__main__":
    asyncio.run(main())
