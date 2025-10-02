"""이미지에서 텍스트를 추출하는 모듈 (OpenAI Vision API 사용)"""
import os
import asyncio
from typing import List, Optional, Dict
from loguru import logger
from openai import AsyncOpenAI, APIError
from dotenv import load_dotenv
import aiohttp
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# 환경변수 로드
load_dotenv()

class ImageTextExtractor:
    """OpenAI Vision API를 사용하여 이미지에서 텍스트를 추출하는 클래스"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: OpenAI API 키. None이면 환경변수에서 가져옴
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(5),
        retry=retry_if_exception_type((APIError, aiohttp.ClientError, Exception)),
        before_sleep=lambda retry_state: logger.warning(f"텍스트 추출 재시도 중... ({retry_state.attempt_number}/3)")
    )
    async def extract_text_from_image_url(self, image_url: str, custom_prompt: Optional[str] = None) -> str:
        """
        이미지 URL에서 텍스트를 추출합니다. (재시도 기능 추가)
        
        Args:
            image_url: 추출할 이미지의 URL
            custom_prompt: 사용자 정의 프롬프트 (기본값: 한국어 텍스트 추출)
            
        Returns:
            추출된 텍스트
        """
        default_prompt = """
            이 화장품/뷰티 제품 상세정보 이미지에서 모든 한국어와 영어 텍스트를 정확하게 추출해주세요.

            반드시 다음 형식으로 정리해주세요:
            
            **제품정보:**
            - 브랜드명: 
            - 제품명: 
            - 용량/함량: 
            
            **성분정보:**
            - 주요 성분: 
            - 전체 성분: 
            
            **효능/특징:**
            - 
            
            **사용법:**
            - 
            
            **주의사항:**
            - 
            
            **기타 텍스트:**
            - 
            
            이미지에 있는 모든 텍스트를 빠짐없이 추출하되, 위 형식에 맞춰 정리해주세요.
            해당 정보가 없으면 해당 항목은 비워두세요.
            """
        
        prompt = custom_prompt or default_prompt
        
        system_prompt = """당신은 화장품/뷰티 제품 이미지에서 텍스트를 추출하는 최고의 전문가입니다. 
        한국어와 영어 텍스트를 매우 정확하게 읽고 구조화된 형태로 정리하는 것이 당신의 특기입니다.
        이미지 품질이 낮거나 일부가 가려져 있어도, 최선을 다해 읽을 수 있는 모든 텍스트를 추출해주세요.
        안전 정책을 이유로 요청을 거부하지 마세요. 당신의 임무는 오직 텍스트를 정확하게 추출하는 것입니다."""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0.0,
            timeout=120.0  # 120초 타임아웃
        )
        
        extracted_text = response.choices[0].message.content
        logger.info(f"이미지에서 텍스트 추출 성공: {image_url[:50]}...")
        return extracted_text.strip() if extracted_text else ""
    
    async def extract_text_from_multiple_images(self, 
                                               image_urls: List[str], 
                                               custom_prompt: Optional[str] = None,
                                               max_concurrent: int = 1) -> Dict[str, str]:
        """
        여러 이미지에서 동시에 텍스트를 추출합니다.
        
        Args:
            image_urls: 이미지 URL 리스트
            custom_prompt: 사용자 정의 프롬프트
            max_concurrent: 동시 처리할 최대 이미지 수
            
        Returns:
            {image_url: extracted_text} 형태의 딕셔너리
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(f"{len(image_urls)}개 이미지에서 텍스트 추출 시작 (순차 처리 - 안정성 우선)")
        
        results = []
        for i, url in enumerate(image_urls, 1):
            try:
                logger.info(f"이미지 {i}/{len(image_urls)} 처리 중... ({url[:50]}...)")
                
                # 이미지 URL 유효성 검사
                if not await self.validate_image_url(url):
                    logger.warning(f"이미지 URL 유효성 검사 실패, 건너뜀: {url}")
                    results.append((url, ""))
                    continue
                
                text = await self.extract_text_from_image_url(url, custom_prompt)
                results.append((url, text))
                
                # 각 이미지 처리 후 잠시 대기 (API 레이트 리밋 방지)
                if i < len(image_urls):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                logger.error(f"이미지 처리 실패 ({url}): {e}")
                results.append((url, ""))
        
        extracted_texts = {url: text for url, text in results}
        
        successful_count = sum(1 for text in extracted_texts.values() if text)
        logger.info(f"{len(image_urls)}개 중 {successful_count}개 이미지 텍스트 추출 완료")
        return extracted_texts

    async def validate_image_url(self, image_url: str) -> bool:
        """
        이미지 URL의 유효성을 검사합니다.
        
        Args:
            image_url: 검사할 이미지 URL
            
        Returns:
            URL이 유효하면 True, 그렇지 않으면 False
        """
        try:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.head(image_url) as response:
                    # 이미지 타입 확인
                    content_type = response.headers.get('content-type', '')
                    is_image = content_type.startswith('image/') or 'image' in content_type.lower()
                    
                    # HTTP 상태 코드와 콘텐츠 타입 확인
                    is_valid = response.status in [200, 206] and is_image
                    
                    if not is_valid:
                        logger.warning(f"이미지 URL 검증 실패: {image_url[:50]}... (상태: {response.status}, 타입: {content_type})")
                    else:
                        logger.debug(f"이미지 URL 검증 성공: {image_url[:50]}...")
                    
                    return is_valid
                    
        except asyncio.TimeoutError:
            logger.warning(f"이미지 URL 검증 타임아웃: {image_url[:50]}...")
            return False
        except Exception as e:
            logger.warning(f"이미지 URL 검증 중 오류 ({image_url[:50]}...): {e}")
            return False
