"""제품 상세정보 텍스트 통합 및 정리 시스템"""
import os
import json
from typing import List, Optional
from loguru import logger
from openai import AsyncOpenAI
from dotenv import load_dotenv

from .database import get_product_image_texts, save_product_summary

# 환경변수 로드
load_dotenv()

class ProductSummarizer:
    """제품 이미지 텍스트를 통합하여 구조화된 상세정보로 정리하는 클래스"""
    
    def __init__(self):
        """ProductSummarizer 초기화"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("ProductSummarizer 초기화 완료")
    
    async def summarize_product_texts(self, product_id: int) -> Optional[str]:
        """
        제품 ID에 해당하는 모든 이미지 텍스트를 통합하여 구조화된 상세정보 생성
        
        Args:
            product_id: 처리할 제품 ID
            
        Returns:
            구조화된 제품 상세정보 (JSON 형태의 문자열) 또는 None
        """
        try:
            logger.info(f"제품 ID {product_id}의 텍스트 통합 시작")
            
            # 제품의 모든 이미지 텍스트 가져오기
            image_texts = get_product_image_texts(product_id)
            
            if not image_texts:
                logger.warning(f"제품 ID {product_id}에 대한 이미지 텍스트가 없습니다.")
                return None
            
            logger.info(f"총 {len(image_texts)}개의 이미지 텍스트 발견")
            
            # 모든 텍스트를 하나로 합치기
            combined_text = "\n\n".join(image_texts)
            
            # OpenAI API로 구조화된 정보 생성
            structured_info = await self._create_structured_summary(combined_text)
            
            if structured_info:
                # 데이터베이스에 저장
                success = save_product_summary(product_id, structured_info)
                if success:
                    logger.info(f"제품 ID {product_id}의 통합 정보가 성공적으로 저장되었습니다.")
                    return structured_info
                else:
                    logger.error(f"제품 ID {product_id}의 통합 정보 저장에 실패했습니다.")
                    return None
            else:
                logger.error(f"제품 ID {product_id}의 구조화된 정보 생성에 실패했습니다.")
                return None
            
        except Exception as e:
            logger.error(f"제품 텍스트 통합 중 오류: {e}")
            return None
    
    async def _create_structured_summary(self, combined_text: str) -> Optional[str]:
        """
        통합된 텍스트로부터 구조화된 제품 상세정보 생성
        
        Args:
            combined_text: 모든 이미지에서 추출된 텍스트들을 합친 문자열
            
        Returns:
            구조화된 제품 정보 (JSON 문자열) 또는 None
        """
        try:
            prompt = self._get_summarization_prompt()
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"다음은 제품의 모든 상세 이미지에서 추출된 텍스트들입니다:\n\n{combined_text}"}
                ],
                temperature=0.0,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content.strip()
            
            # JSON 형태인지 확인
            try:
                json.loads(result)
                logger.info("구조화된 제품 정보 생성 완료")
                return result
            except json.JSONDecodeError:
                logger.warning("응답이 유효한 JSON 형태가 아닙니다. 원본 텍스트 반환")
                return result
            
        except Exception as e:
            logger.error(f"구조화된 요약 생성 중 오류: {e}")
            return None
    
    def _get_summarization_prompt(self) -> str:
        """텍스트 통합 및 구조화를 위한 프롬프트 반환"""
        return """당신은 화장품 및 건강기능식품 전문 정보 정리 전문가입니다. 
제품의 여러 이미지에서 추출된 텍스트들을 분석하여 구체적이고 상세한 제품 정보로 통합해주세요.

다음 JSON 형태로 정리하되, 모든 구체적인 정보를 보존해주세요:

{
    "product_info": {
        "brand_name": "브랜드명",
        "product_name": "정확한 제품명",
        "volume_amount": "용량/수량 정보",
        "form": "제형 (캡슐/정제/크림/액상 등)",
        "manufacturing_info": "제조사/제조국 정보"
    },
    "detailed_ingredients": {
        "main_ingredients": ["주성분1 (함량)", "주성분2 (함량)", "..."],
        "full_ingredient_list": "전체 원료명 및 함량 (있는 경우 모두 포함)",
        "functional_ingredients": ["기능성 원료명과 기능성 내용"]
    },
    "benefits_and_effects": {
        "primary_functions": ["주요 기능성 내용 (상세하게)"],
        "detailed_benefits": ["모든 효능/효과 정보를 구체적으로"],
        "clinical_data": "임상시험이나 연구결과 정보 (있는 경우)"
    },
    "usage_instructions": {
        "dosage": "복용량/사용량",
        "frequency": "복용횟수/사용빈도", 
        "timing": "복용시기/사용시기",
        "detailed_method": "구체적인 사용방법"
    },
    "safety_and_precautions": {
        "contraindications": ["복용금지 대상자"],
        "side_effects": ["부작용 정보"],
        "storage_instructions": "보관방법",
        "warnings": ["모든 주의사항을 구체적으로"]
    },
    "certifications_and_approvals": {
        "health_functional_food": "건강기능식품 인증정보",
        "manufacturing_standards": ["GMP, ISO 등 제조기준"],
        "safety_certifications": ["안전성 인증"],
        "other_certifications": ["기타 인증정보"]
    },
    "additional_details": {
        "manufacturing_process": "제조공법이나 특별한 기술",
        "packaging_info": "포장 정보",
        "expiry_info": "유통기한 정보",
        "other_important_info": "기타 중요한 모든 정보"
    }
}

중요사항:
1. 요약하지 말고 추출된 텍스트의 모든 구체적인 정보를 보존하여 포함하세요
2. 성분명, 함량, 수치 등은 정확히 기록하세요
3. 빈 정보는 null로 표시하되, 가능한 모든 정보를 찾아 기록하세요
4. 중복된 정보는 가장 상세하고 정확한 것으로 통합하세요
5. 원문의 표현을 최대한 살려서 정보 손실을 방지하세요
6. 한국어로 정리하되 원료명 등 전문용어는 원문 그대로 유지하세요
7. 반드시 유효한 JSON 형태로 응답하세요"""

    async def get_product_summary_stats(self) -> dict:
        """제품 요약 통계 정보 반환"""
        try:
            from .database import DB_FILE
            import sqlite3
            
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            
            # 전체 제품 수
            cur.execute("SELECT COUNT(*) FROM products")
            total_products = cur.fetchone()[0]
            
            # 요약이 완료된 제품 수
            cur.execute("SELECT COUNT(*) FROM products WHERE detailed_summary IS NOT NULL")
            summarized_products = cur.fetchone()[0]
            
            # 이미지 텍스트가 있는 제품 수
            cur.execute("""
                SELECT COUNT(DISTINCT product_id) 
                FROM product_image_texts
            """)
            products_with_texts = cur.fetchone()[0]
            
            con.close()
            
            completion_rate = (summarized_products / total_products * 100) if total_products > 0 else 0
            
            return {
                "total_products": total_products,
                "summarized_products": summarized_products,
                "products_with_texts": products_with_texts,
                "completion_rate": f"{completion_rate:.1f}%"
            }
            
        except Exception as e:
            logger.error(f"통계 정보 조회 중 오류: {e}")
            return {}

    async def process_pending_summaries(self) -> dict:
        """요약이 아직 되지 않은 제품들을 일괄 처리"""
        try:
            from .database import DB_FILE
            import sqlite3
            
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            
            # 이미지 텍스트는 있지만 요약이 없는 제품들 찾기
            cur.execute("""
                SELECT DISTINCT p.id, p.name
                FROM products p
                JOIN product_image_texts pit ON p.id = pit.product_id
                WHERE p.detailed_summary IS NULL
            """)
            
            pending_products = cur.fetchall()
            con.close()
            
            if not pending_products:
                logger.info("처리할 대기중인 제품이 없습니다.")
                return {"processed": 0, "failed": 0, "total": 0}
            
            logger.info(f"총 {len(pending_products)}개 제품의 요약을 생성합니다.")
            
            processed = 0
            failed = 0
            
            for product_id, product_name in pending_products:
                logger.info(f"제품 처리 중: {product_name} (ID: {product_id})")
                
                result = await self.summarize_product_texts(product_id)
                if result:
                    processed += 1
                    logger.info(f"✅ 완료: {product_name}")
                else:
                    failed += 1
                    logger.error(f"❌ 실패: {product_name}")
                
                # API 제한을 위한 대기
                import asyncio
                await asyncio.sleep(2)
            
            return {
                "processed": processed,
                "failed": failed,
                "total": len(pending_products)
            }
            
        except Exception as e:
            logger.error(f"일괄 처리 중 오류: {e}")
            return {"processed": 0, "failed": 0, "total": 0, "error": str(e)}