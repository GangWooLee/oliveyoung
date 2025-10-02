"""Playwright 스크래퍼 테스트 (headless=False)"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from src.scraper.oliveyoung_scraper import OliveYoungScraper

async def main():
    url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000203347"

    logger.info("=== Playwright 스크래퍼 테스트 (headless=False) ===")

    async with OliveYoungScraper(headless=False) as scraper:
        product = await scraper.scrape(url, max_reviews=10)

        logger.info("\n=== 스크래핑 결과 ===")
        logger.info(f"제품명: {product.name}")
        logger.info(f"가격: {product.price}")
        logger.info(f"평점: {product.rating}")
        logger.info(f"리뷰 개수: {product.review_count}")
        logger.info(f"상세 이미지 개수: {len(product.detail_images)}")
        logger.info(f"리뷰 개수: {len(product.reviews)}")

if __name__ == "__main__":
    asyncio.run(main())
