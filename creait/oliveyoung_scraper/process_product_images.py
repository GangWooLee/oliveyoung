"""모든 제품 이미지에 대해 텍스트 추출을 수행하는 배치 처리 스크립트"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from src.image_text_extractor import ImageTextExtractor
from src.database import (
    init_db, 
    get_product_images_with_ids, 
    get_unprocessed_images, 
    save_image_text
)

async def process_all_product_images(max_images: int = None, only_unprocessed: bool = True):
    """모든 제품 이미지에 대해 텍스트 추출을 수행합니다."""
    logger.info("=== 제품 이미지 텍스트 추출 배치 처리 시작 ===")
    
    try:
        # 데이터베이스 초기화
        init_db()
        
        # 처리할 이미지 목록 가져오기
        if only_unprocessed:
            images = get_unprocessed_images()
            logger.info(f"미처리 이미지 {len(images)}개를 가져왔습니다.")
        else:
            images = get_product_images_with_ids()
            logger.info(f"전체 이미지 {len(images)}개를 가져왔습니다.")
        
        if not images:
            logger.warning("처리할 이미지가 없습니다.")
            return
        
        # 최대 처리 개수 제한
        if max_images:
            images = images[:max_images]
            logger.info(f"최대 {max_images}개로 제한하여 처리합니다.")
        
        extractor = ImageTextExtractor()
        
        successful_count = 0
        failed_count = 0
        
        for i, (image_id, product_id, product_name, image_url) in enumerate(images, 1):
            logger.info(f"\n=== 이미지 {i}/{len(images)} ===")
            logger.info(f"이미지 ID: {image_id}")
            logger.info(f"제품: {product_name} (ID: {product_id})")
            logger.info(f"이미지 URL: {image_url}")
            
            try:
                # 이미지 URL 유효성 검사
                is_valid = await extractor.validate_image_url(image_url)
                
                if not is_valid:
                    logger.warning(f"이미지 {i}: 유효하지 않은 URL")
                    failed_count += 1
                    continue
                
                # 텍스트 추출
                extracted_text = await extractor.extract_text_from_image_url(image_url)
                
                # 텍스트가 의미있게 추출되었는지 확인
                if extracted_text and extracted_text.strip() and len(extracted_text.strip()) > 10:
                    # 성공적인 추출인지 추가 검증
                    invalid_responses = [
                        "i'm unable to",
                        "i can't assist",
                        "i'm sorry",
                        "i cannot",
                        "unable to provide",
                        "can't help"
                    ]
                    
                    if any(invalid in extracted_text.lower() for invalid in invalid_responses):
                        logger.warning(f"이미지 {i}: OpenAI가 텍스트 추출을 거부했습니다.")
                        failed_count += 1
                        continue
                    
                    # 데이터베이스에 저장
                    success = save_image_text(image_id, product_id, image_url, extracted_text)
                    
                    if success:
                        logger.info(f"이미지 {i}: 텍스트 추출 및 저장 성공")
                        logger.info(f"추출된 텍스트 (처음 100자): {extracted_text[:100]}...")
                        successful_count += 1
                    else:
                        logger.error(f"이미지 {i}: 데이터베이스 저장 실패")
                        failed_count += 1
                else:
                    logger.warning(f"이미지 {i}: 빈 텍스트 또는 너무 짧은 텍스트")
                    failed_count += 1
                
                # API 요청 제한을 위한 대기
                if i < len(images):
                    logger.info("다음 이미지 처리를 위해 2초 대기...")
                    await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"이미지 {i} 처리 중 오류: {e}")
                failed_count += 1
                continue
        
        logger.info(f"\n=== 배치 처리 완료 ===")
        logger.info(f"총 처리한 이미지: {len(images)}개")
        logger.info(f"성공: {successful_count}개")
        logger.info(f"실패: {failed_count}개")
        logger.info(f"성공률: {successful_count/len(images)*100:.1f}%")
        
    except Exception as e:
        logger.error(f"배치 처리 중 오류: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """메인 실행 함수"""
    logger.info("제품 이미지 텍스트 추출 배치 처리기")
    
    print("처리 옵션을 선택하세요:")
    print("1. 미처리 이미지만 처리 (권장)")
    print("2. 모든 이미지 재처리")
    print("3. 테스트 (미처리 이미지 5개만)")
    print("4. 특정 제품의 모든 이미지 처리")
    
    try:
        choice = input("선택 (1-4): ").strip()
        
        if choice == "1":
            await process_all_product_images(only_unprocessed=True)
        elif choice == "2":
            confirm = input("모든 이미지를 재처리하시겠습니까? (y/N): ").strip().lower()
            if confirm == 'y':
                await process_all_product_images(only_unprocessed=False)
            else:
                logger.info("처리를 취소했습니다.")
        elif choice == "3":
            await process_all_product_images(max_images=5, only_unprocessed=True)
        elif choice == "4":
            try:
                product_id = int(input("제품 ID를 입력하세요: ").strip())
                from src.database import get_product_images_with_ids
                product_images = get_product_images_with_ids(product_id)
                if product_images:
                    logger.info(f"제품 ID {product_id}에서 {len(product_images)}개 이미지 발견")
                    confirm = input(f"총 {len(product_images)}개 이미지를 처리하시겠습니까? (y/N): ").strip().lower()
                    if confirm == 'y':
                        await process_specific_product_images(product_id)
                    else:
                        logger.info("처리를 취소했습니다.")
                else:
                    logger.error(f"제품 ID {product_id}에 이미지가 없습니다.")
            except ValueError:
                logger.error("올바른 제품 ID를 입력하세요.")
        else:
            logger.error("잘못된 선택입니다.")
            return
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"처리 중 오류: {e}")

async def process_specific_product_images(product_id: int):
    """특정 제품의 모든 이미지 처리"""
    logger.info(f"=== 제품 ID {product_id}의 모든 이미지 텍스트 추출 ===")
    
    try:
        from src.database import get_product_images_with_ids
        images = get_product_images_with_ids(product_id)
        
        if not images:
            logger.warning(f"제품 ID {product_id}에 이미지가 없습니다.")
            return
        
        extractor = ImageTextExtractor()
        successful_count = 0
        failed_count = 0
        
        for i, (image_id, _, product_name, image_url) in enumerate(images, 1):
            logger.info(f"\n=== 이미지 {i}/{len(images)} ===")
            logger.info(f"이미지 ID: {image_id}")
            logger.info(f"제품: {product_name}")
            logger.info(f"이미지 URL: {image_url}")
            
            try:
                # 이미지 URL 유효성 검사
                is_valid = await extractor.validate_image_url(image_url)
                
                if not is_valid:
                    logger.warning(f"이미지 {i}: 유효하지 않은 URL")
                    failed_count += 1
                    continue
                
                # 텍스트 추출
                logger.info(f"이미지 {i}: 텍스트 추출 시작...")
                extracted_text = await extractor.extract_text_from_image_url(image_url)
                
                # 텍스트가 의미있게 추출되었는지 확인
                if extracted_text and extracted_text.strip() and len(extracted_text.strip()) > 10:
                    # 성공적인 추출인지 추가 검증
                    invalid_responses = [
                        "i'm unable to", "i can't assist", "i'm sorry", "i cannot",
                        "unable to provide", "can't help", "죄송하지만", "추출할 수 없습니다"
                    ]
                    
                    if any(invalid in extracted_text.lower() for invalid in invalid_responses):
                        logger.warning(f"이미지 {i}: OpenAI가 텍스트 추출을 거부했습니다.")
                        failed_count += 1
                        continue
                    
                    # 데이터베이스에 저장
                    success = save_image_text(image_id, product_id, image_url, extracted_text)
                    
                    if success:
                        logger.info(f"이미지 {i}: 텍스트 추출 및 저장 성공")
                        logger.info(f"추출된 텍스트 (처음 100자): {extracted_text[:100]}...")
                        successful_count += 1
                    else:
                        logger.error(f"이미지 {i}: 데이터베이스 저장 실패")
                        failed_count += 1
                else:
                    logger.warning(f"이미지 {i}: 빈 텍스트 또는 너무 짧은 텍스트")
                    failed_count += 1
                
                # API 요청 제한을 위한 대기
                if i < len(images):
                    logger.info("다음 이미지 처리를 위해 2초 대기...")
                    await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"이미지 {i} 처리 중 오류: {e}")
                failed_count += 1
                continue
        
        logger.info(f"\n=== 제품 ID {product_id} 이미지 텍스트 추출 완료 ===")
        logger.info(f"총 처리한 이미지: {len(images)}개")
        logger.info(f"성공: {successful_count}개")
        logger.info(f"실패: {failed_count}개")
        logger.info(f"성공률: {successful_count/len(images)*100:.1f}%")
        
    except Exception as e:
        logger.error(f"제품별 이미지 처리 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())