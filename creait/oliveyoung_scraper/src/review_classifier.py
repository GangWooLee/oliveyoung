"""리뷰 분류 및 장단점 추출 시스템"""
import os
import json
from typing import Dict, List, Optional
from loguru import logger
from openai import AsyncOpenAI
from dotenv import load_dotenv

from .database import get_product_reviews_by_rating, save_review_analysis, get_review_analysis_results

load_dotenv()

class ReviewClassifier:
    """리뷰를 별점별로 분류하고 소비자 근거를 보존하며 장단점을 추출하는 클래스"""
    
    def __init__(self):
        """ReviewClassifier 초기화"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("ReviewClassifier 초기화 완료")
    
    def classify_reviews_by_rating(self, product_id: int) -> Dict[str, List[str]]:
        """
        제품의 리뷰를 별점 기준으로 3그룹으로 분류
        
        Args:
            product_id: 분류할 제품 ID
            
        Returns:
            분류된 리뷰 딕셔너리 {'positive_5': [...], 'neutral_4_3': [...], 'negative_2_1': [...]}
        """
        try:
            logger.info(f"제품 ID {product_id}의 리뷰 분류 시작")
            classified_reviews = get_product_reviews_by_rating(product_id)
            
            logger.info(f"분류 결과: 긍정 {len(classified_reviews['positive_5'])}개, "
                       f"중립 {len(classified_reviews['neutral_4_3'])}개, "
                       f"부정 {len(classified_reviews['negative_2_1'])}개")
            
            return classified_reviews
            
        except Exception as e:
            logger.error(f"리뷰 분류 중 오류: {e}")
            return {'positive_5': [], 'neutral_4_3': [], 'negative_2_1': []}
    
    async def extract_insights_with_evidence(self, reviews: List[str], sentiment_group: str) -> Dict[str, any]:
        """
        소비자 근거를 보존하며 장단점 추출 (토큰 제한을 고려한 청크 기반 처리)
        
        Args:
            reviews: 분석할 리뷰 텍스트 리스트
            sentiment_group: 감정 그룹 ('positive_5', 'neutral_4_3', 'negative_2_1')
            
        Returns:
            장단점과 근거가 포함된 분석 결과
        """
        if not reviews:
            logger.warning(f"{sentiment_group} 그룹에 분석할 리뷰가 없습니다.")
            return {"advantages": [], "disadvantages": []}
        
        try:
            logger.info(f"{sentiment_group} 그룹 {len(reviews)}개 리뷰 분석 시작")
            
            # 토큰 제한 고려: 리뷰가 100개 이상이면 청크로 나누어 처리
            if len(reviews) > 100:
                logger.info(f"{sentiment_group} 그룹: 리뷰가 {len(reviews)}개로 많아 청크 단위로 분할 처리합니다.")
                return await self._process_reviews_in_chunks(reviews, sentiment_group)
            else:
                # 기존 방식: 모든 리뷰를 한 번에 처리
                return await self._process_single_chunk(reviews, sentiment_group, 0)
            
        except Exception as e:
            logger.error(f"{sentiment_group} 그룹 장단점 추출 중 오류: {e}")
            return {"advantages": [], "disadvantages": []}
    
    async def _process_reviews_in_chunks(self, reviews: List[str], sentiment_group: str) -> Dict[str, any]:
        """
        리뷰를 청크 단위로 나누어 처리하고 결과를 통합
        
        Args:
            reviews: 분석할 리뷰 텍스트 리스트
            sentiment_group: 감정 그룹
            
        Returns:
            통합된 분석 결과
        """
        chunk_size = 80  # 청크당 리뷰 개수 (토큰 제한 고려)
        chunks = [reviews[i:i+chunk_size] for i in range(0, len(reviews), chunk_size)]
        
        logger.info(f"{sentiment_group} 그룹: {len(chunks)}개 청크로 분할하여 처리")
        
        all_advantages = []
        all_disadvantages = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"{sentiment_group} 그룹: 청크 {i+1}/{len(chunks)} 처리 중... ({len(chunk)}개 리뷰)")
            
            try:
                chunk_result = await self._process_single_chunk(chunk, sentiment_group, i * chunk_size)
                
                # 각 청크의 결과를 통합
                if chunk_result.get("advantages"):
                    all_advantages.extend(chunk_result["advantages"])
                if chunk_result.get("disadvantages"):
                    all_disadvantages.extend(chunk_result["disadvantages"])
                    
                logger.info(f"{sentiment_group} 그룹: 청크 {i+1} 완료 - 장점 {len(chunk_result.get('advantages', []))}개, 단점 {len(chunk_result.get('disadvantages', []))}개")
                
            except Exception as e:
                logger.error(f"{sentiment_group} 그룹: 청크 {i+1} 처리 중 오류: {e}")
                continue
        
        # 최종 통합 결과
        final_result = {
            "advantages": all_advantages,
            "disadvantages": all_disadvantages
        }
        
        logger.info(f"{sentiment_group} 그룹: 청크 처리 완료 - 최종 장점 {len(all_advantages)}개, 단점 {len(all_disadvantages)}개")
        return final_result
    
    async def _process_single_chunk(self, reviews: List[str], sentiment_group: str, offset: int = 0) -> Dict[str, any]:
        """
        단일 청크의 리뷰들을 처리
        
        Args:
            reviews: 처리할 리뷰 리스트
            sentiment_group: 감정 그룹
            offset: 리뷰 번호 오프셋 (청크 처리 시 전체 번호 유지용)
            
        Returns:
            분석 결과
        """
        # 모든 리뷰를 하나로 합치기 (번호 매기기)
        numbered_reviews = []
        for i, review in enumerate(reviews, 1 + offset):
            numbered_reviews.append(f"[리뷰 {i}] {review}")
        
        combined_reviews = "\n\n".join(numbered_reviews)
        
        prompt = self._get_analysis_prompt(sentiment_group)
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"다음은 {sentiment_group} 그룹의 리뷰입니다:\n\n{combined_reviews}"}
            ],
            temperature=0.0,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content.strip()
        
        # JSON 추출 및 파싱 시도
        try:
            # 1차: 직접 JSON 파싱 시도
            parsed_result = json.loads(result)
            return parsed_result
        except json.JSONDecodeError:
            # 2차: JSON 블록 추출 시도
            try:
                # ```json 블록에서 추출
                if "```json" in result:
                    json_start = result.find("```json") + 7
                    json_end = result.find("```", json_start)
                    if json_end != -1:
                        json_content = result[json_start:json_end].strip()
                        parsed_result = json.loads(json_content)
                        return parsed_result
                
                # { 와 } 사이의 JSON 추출
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_content = result[json_start:json_end]
                    parsed_result = json.loads(json_content)
                    return parsed_result
                    
                logger.warning(f"{sentiment_group} 청크: JSON 추출 실패, 원본 내용 일부: {result[:200]}...")
                return {"advantages": [], "disadvantages": []}
                    
            except json.JSONDecodeError as e:
                logger.warning(f"{sentiment_group} 청크: JSON 파싱 실패 - {e}")
                logger.warning(f"추출 시도한 내용: {result[:500]}...")
                return {"advantages": [], "disadvantages": []}
    
    def _get_analysis_prompt(self, sentiment_group: str) -> str:
        """감정 그룹에 맞는 분석 프롬프트 반환"""
        
        base_instruction = """당신은 화장품 및 건강기능식품 리뷰 분석 전문가입니다. 
소비자 리뷰들을 분석하여 제품의 구체적인 장점과 단점을 정리해주세요.

🔴 중요 요구사항:
1. 모든 리뷰 내용이 분석 결과에 반영되어야 합니다 (정보 손실 방지)
2. 각 장점/단점마다 해당 내용을 언급한 리뷰 번호를 정확히 기록해주세요
3. 소비자들의 원문 표현을 최대한 보존해주세요
4. 요약하지 말고 구체적인 내용을 모두 포함해주세요

💡 응답 형식: 반드시 유효한 JSON 형태로만 응답하세요. 다른 설명 텍스트는 포함하지 마세요."""
        
        if sentiment_group == "positive_5":
            specific_instruction = """
이 그룹은 5점 만점 리뷰들입니다. 주로 장점을 찾되, 아쉬운 점이나 개선점도 놓치지 마세요."""
        elif sentiment_group == "neutral_4_3":
            specific_instruction = """
이 그룹은 4-3점 리뷰들입니다. 장점과 단점이 균형있게 언급될 가능성이 높습니다."""
        else:  # negative_2_1
            specific_instruction = """
이 그룹은 2-1점 리뷰들입니다. 주로 단점을 찾되, 긍정적인 측면도 놓치지 마세요."""
        
        json_format = """{
    "advantages": [
        {
            "point": "구체적인 장점 (소비자 표현 그대로)",
            "evidence": ["관련 리뷰 번호들"],
            "details": "해당 장점에 대한 모든 세부 내용"
        }
    ],
    "disadvantages": [
        {
            "point": "구체적인 단점 (소비자 표현 그대로)",
            "evidence": ["관련 리뷰 번호들"],
            "details": "해당 단점에 대한 모든 세부 내용"
        }
    ]
}"""
        
        return f"""{base_instruction}

{specific_instruction}

🔥 중요: 반드시 아래 JSON 형태로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요:
{json_format}

⚠️ 모든 리뷰의 의미있는 내용이 advantages 또는 disadvantages에 포함되어야 합니다.

다시 한번 강조: 오직 JSON만 출력하세요. 설명이나 다른 텍스트는 포함하지 마세요."""
    
    async def analyze_product_reviews(self, product_id: int) -> Dict[str, any]:
        """
        제품의 전체 리뷰를 분석하여 감정별 장단점 추출
        
        Args:
            product_id: 분석할 제품 ID
            
        Returns:
            전체 분석 결과
        """
        try:
            logger.info(f"제품 ID {product_id} 전체 리뷰 분석 시작")
            
            # 1. 리뷰 분류
            classified_reviews = self.classify_reviews_by_rating(product_id)
            
            # 2. 각 그룹별 장단점 분석
            analysis_results = {}
            
            for group_name, reviews in classified_reviews.items():
                if reviews:  # 리뷰가 있는 경우에만 분석
                    logger.info(f"{group_name} 그룹 분석 중...")
                    group_analysis = await self.extract_insights_with_evidence(reviews, group_name)
                    analysis_results[group_name] = {
                        "review_count": len(reviews),
                        "analysis": group_analysis
                    }
                    
                    # 데이터베이스에 저장
                    advantages_json = json.dumps(group_analysis.get("advantages", []), ensure_ascii=False)
                    disadvantages_json = json.dumps(group_analysis.get("disadvantages", []), ensure_ascii=False)
                    
                    save_success = save_review_analysis(
                        product_id=product_id,
                        sentiment_group=group_name,
                        advantages=advantages_json,
                        disadvantages=disadvantages_json,
                        review_count=len(reviews)
                    )
                    
                    if save_success:
                        logger.info(f"{group_name} 그룹 분석 결과 저장 완료")
                    else:
                        logger.error(f"{group_name} 그룹 분석 결과 저장 실패")
                else:
                    logger.info(f"{group_name} 그룹에 리뷰가 없어 건너뜁니다.")
                    analysis_results[group_name] = {
                        "review_count": 0,
                        "analysis": {"advantages": [], "disadvantages": []}
                    }
            
            logger.info(f"제품 ID {product_id} 전체 리뷰 분석 완료")
            return analysis_results
            
        except Exception as e:
            logger.error(f"제품 리뷰 분석 중 오류: {e}")
            return {}
    
    async def get_analysis_stats(self) -> Dict[str, any]:
        """리뷰 분석 통계 정보 반환"""
        try:
            from .database import DB_FILE
            import sqlite3
            
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            
            # 전체 제품 수
            cur.execute("SELECT COUNT(*) FROM products")
            total_products = cur.fetchone()[0]
            
            # 분석 완료된 제품 수 (3개 그룹 모두 분석된 제품)
            cur.execute("""
                SELECT COUNT(DISTINCT product_id) 
                FROM review_analysis
            """)
            analyzed_products = cur.fetchone()[0]
            
            # 그룹별 분석 통계
            cur.execute("""
                SELECT sentiment_group, COUNT(*), SUM(review_count)
                FROM review_analysis
                GROUP BY sentiment_group
            """)
            group_stats = cur.fetchall()
            
            con.close()
            
            completion_rate = (analyzed_products / total_products * 100) if total_products > 0 else 0
            
            stats = {
                "total_products": total_products,
                "analyzed_products": analyzed_products,
                "completion_rate": f"{completion_rate:.1f}%",
                "group_analysis": {}
            }
            
            for group, count, total_reviews in group_stats:
                stats["group_analysis"][group] = {
                    "analyzed_products": count,
                    "total_reviews": total_reviews
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"분석 통계 조회 중 오류: {e}")
            return {}

    def get_product_analysis_summary(self, product_id: int) -> Optional[Dict]:
        """특정 제품의 분석 결과 요약 조회"""
        try:
            results = get_review_analysis_results(product_id)
            
            if not results:
                return None
            
            summary = {
                "product_id": product_id,
                "product_name": results[0][1],  # 첫 번째 결과에서 제품명 추출
                "analysis_groups": {}
            }
            
            for result in results:
                _, _, sentiment_group, advantages, disadvantages, review_count, analyzed_at = result
                
                try:
                    advantages_parsed = json.loads(advantages) if advantages else []
                    disadvantages_parsed = json.loads(disadvantages) if disadvantages else []
                except json.JSONDecodeError:
                    advantages_parsed = []
                    disadvantages_parsed = []
                
                summary["analysis_groups"][sentiment_group] = {
                    "review_count": review_count,
                    "advantages_count": len(advantages_parsed),
                    "disadvantages_count": len(disadvantages_parsed),
                    "analyzed_at": analyzed_at
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"제품 분석 요약 조회 중 오류: {e}")
            return None