"""제품 평가 시스템 - 가중평균 + 모순 탐지 기반 점수 차감"""
import os
import json
from typing import Dict, List, Optional, Tuple
from loguru import logger
from openai import AsyncOpenAI
from dotenv import load_dotenv

from .database import (
    get_product_review_ratings, 
    get_review_analysis_results,
    save_product_evaluation,
    get_product_evaluation,
    get_all_product_evaluations
)

load_dotenv()

class ProductEvaluator:
    """제품을 가중평균과 모순 탐지를 통해 종합 평가하는 클래스"""
    
    def __init__(self):
        """ProductEvaluator 초기화"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        self.client = AsyncOpenAI(api_key=api_key)
        
        # 가중치 설정 (부정 리뷰 강화)
        self.rating_weights = {
            5: 1.0,   # 5점: 기본 가중치
            4: 0.8,   # 4점: 약간 감소
            3: 0.6,   # 3점: 더 감소
            2: 2.0,   # 2점: 부정 리뷰 강화 (2배)
            1: 2.0,   # 1점: 부정 리뷰 강화 (2배)
        }
        
        logger.info("ProductEvaluator 초기화 완료")
    
    def calculate_weighted_score(self, product_id: int) -> Tuple[float, Dict]:
        """
        제품의 가중평균 점수 계산 (부정 리뷰 강화)
        
        Args:
            product_id: 평가할 제품 ID
            
        Returns:
            (가중평균 점수, 계산 상세정보)
        """
        try:
            logger.info(f"제품 ID {product_id}의 가중평균 점수 계산 시작")
            
            # 리뷰 별점 분포 가져오기
            rating_distribution = get_product_review_ratings(product_id)
            
            if not rating_distribution:
                logger.warning(f"제품 ID {product_id}에 대한 리뷰 별점이 없습니다.")
                return 0.0, {"error": "리뷰 데이터 없음"}
            
            weighted_sum = 0.0
            weight_sum = 0.0
            calculation_details = {
                "rating_distribution": {},
                "calculations": [],
                "total_reviews": 0
            }
            
            total_reviews = 0
            
            for rating_str, count in rating_distribution:
                try:
                    rating = int(rating_str)
                    weight = self.rating_weights.get(rating, 1.0)
                    
                    contribution = rating * count * weight
                    weighted_sum += contribution
                    weight_sum += count * weight
                    total_reviews += count
                    
                    calculation_details["rating_distribution"][rating] = count
                    calculation_details["calculations"].append({
                        "rating": rating,
                        "count": count,
                        "weight": weight,
                        "contribution": contribution
                    })
                    
                    logger.debug(f"{rating}점 x {count}개 x {weight} = {contribution}")
                    
                except (ValueError, TypeError):
                    logger.warning(f"유효하지 않은 별점: {rating_str}")
                    continue
            
            if weight_sum == 0:
                logger.error(f"제품 ID {product_id}의 가중치 합이 0입니다.")
                return 0.0, {"error": "가중치 계산 오류"}
            
            weighted_average = weighted_sum / weight_sum
            
            calculation_details["total_reviews"] = total_reviews
            calculation_details["weighted_sum"] = weighted_sum
            calculation_details["weight_sum"] = weight_sum
            calculation_details["weighted_average"] = weighted_average
            
            logger.info(f"제품 ID {product_id} 가중평균: {weighted_average:.2f}/5.0 (총 {total_reviews}개 리뷰)")
            
            return weighted_average, calculation_details
            
        except Exception as e:
            logger.error(f"가중평균 계산 중 오류: {e}")
            return 0.0, {"error": str(e)}
    
    async def detect_contradictions(self, product_id: int) -> Tuple[List[Dict], float]:
        """
        상세정보와 리뷰 간 모순 탐지 및 점수 차감 계산
        
        Args:
            product_id: 분석할 제품 ID
            
        Returns:
            (모순 목록, 차감 점수)
        """
        try:
            logger.info(f"제품 ID {product_id}의 모순 탐지 시작")
            
            # 상세정보 가져오기
            from .database import DB_FILE
            import sqlite3
            
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            
            cur.execute("SELECT detailed_summary FROM products WHERE id = ?", (product_id,))
            summary_result = cur.fetchone()
            
            if not summary_result or not summary_result[0]:
                con.close()
                logger.warning(f"제품 ID {product_id}의 상세정보가 없습니다.")
                return [], 0.0
            
            detailed_summary = summary_result[0]
            con.close()
            
            # 리뷰 분석 결과 가져오기
            review_analysis = get_review_analysis_results(product_id)
            
            if not review_analysis:
                logger.warning(f"제품 ID {product_id}의 리뷰 분석 결과가 없습니다.")
                return [], 0.0
            
            # 리뷰 분석 데이터를 그룹별로 정리
            review_groups = {}
            for result in review_analysis:
                _, _, sentiment_group, advantages, disadvantages, review_count, _ = result
                
                try:
                    advantages_parsed = json.loads(advantages) if advantages else []
                    disadvantages_parsed = json.loads(disadvantages) if disadvantages else []
                except json.JSONDecodeError:
                    advantages_parsed = []
                    disadvantages_parsed = []
                
                review_groups[sentiment_group] = {
                    "advantages": advantages_parsed,
                    "disadvantages": disadvantages_parsed,
                    "review_count": review_count
                }
            
            # AI를 통한 모순 탐지
            contradictions = await self._analyze_contradictions_with_ai(detailed_summary, review_groups)
            
            # 차감 점수 계산
            penalty_score = self._calculate_penalty_score(contradictions)
            
            logger.info(f"제품 ID {product_id} 모순 탐지 완료: {len(contradictions)}개 모순, -{penalty_score:.2f}점 차감")
            
            return contradictions, penalty_score
            
        except Exception as e:
            logger.error(f"모순 탐지 중 오류: {e}")
            return [], 0.0
    
    async def _analyze_contradictions_with_ai(self, detailed_summary: str, review_groups: Dict) -> List[Dict]:
        """AI를 통한 상세정보-리뷰 간 모순 분석"""
        try:
            prompt = self._get_contradiction_analysis_prompt()
            
            # 리뷰 그룹 데이터를 텍스트로 변환
            review_summary = self._format_review_groups_for_analysis(review_groups)
            
            user_message = f"""
상세정보:
{detailed_summary}

리뷰 분석 결과:
{review_summary}
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                parsed_result = json.loads(result)
                contradictions = parsed_result.get("contradictions", [])
                logger.info(f"AI 모순 분석 완료: {len(contradictions)}개 모순 발견")
                return contradictions
            except json.JSONDecodeError:
                logger.warning("AI 응답이 유효한 JSON 형태가 아닙니다.")
                return []
            
        except Exception as e:
            logger.error(f"AI 모순 분석 중 오류: {e}")
            return []
    
    def _format_review_groups_for_analysis(self, review_groups: Dict) -> str:
        """리뷰 그룹 데이터를 AI 분석용 텍스트로 포맷"""
        formatted_text = ""
        
        group_names = {
            'positive_5': '긍정 리뷰 (5점)',
            'neutral_4_3': '중립 리뷰 (4-3점)',
            'negative_2_1': '부정 리뷰 (2-1점)'
        }
        
        for group_key, group_data in review_groups.items():
            group_name = group_names.get(group_key, group_key)
            formatted_text += f"\n### {group_name} ({group_data['review_count']}개 리뷰)\n"
            
            # 장점
            if group_data['advantages']:
                formatted_text += "**장점:**\n"
                for adv in group_data['advantages']:
                    if isinstance(adv, dict) and 'point' in adv:
                        formatted_text += f"- {adv['point']}\n"
                        if 'details' in adv:
                            formatted_text += f"  상세: {adv['details']}\n"
            
            # 단점
            if group_data['disadvantages']:
                formatted_text += "**단점:**\n"
                for dis in group_data['disadvantages']:
                    if isinstance(dis, dict) and 'point' in dis:
                        formatted_text += f"- {dis['point']}\n"
                        if 'details' in dis:
                            formatted_text += f"  상세: {dis['details']}\n"
            
            formatted_text += "\n"
        
        return formatted_text
    
    def _get_contradiction_analysis_prompt(self) -> str:
        """모순 탐지용 AI 프롬프트"""
        return """당신은 제품 광고 신뢰성 평가 전문가입니다. 
제품의 상세정보(광고/마케팅 내용)와 실제 소비자 리뷰를 비교분석하여 모순점을 찾아주세요.

🎯 분석 목표: 과대광고 탐지
- 상세정보에서 주장한 효과/기능이 실제 리뷰에서 부정적으로 언급되는 경우
- 제품이 약속한 것과 소비자 경험 간의 격차

🔍 모순 탐지 기준:
1. **효능/효과 모순**: 상세정보 효과 주장 vs 리뷰 "효과 없음"
2. **사용감 모순**: 상세정보 사용감 주장 vs 리뷰 불만족
3. **품질 모순**: 상세정보 품질 주장 vs 리뷰 품질 문제
4. **기능 모순**: 상세정보 기능 주장 vs 리뷰 기능 불만

심각도 기준:
- **high**: 명확하고 직접적인 모순 (효과 주장 vs 효과 없음)
- **medium**: 간접적이지만 의미있는 모순
- **low**: 일부 불만이지만 심각하지 않은 모순

다음 JSON 형태로 분석해주세요:
{
    "contradictions": [
        {
            "claim": "상세정보에서 주장한 내용",
            "reality": "리뷰에서 언급된 실제 경험",
            "severity": "high/medium/low",
            "evidence": "근거가 되는 리뷰 내용",
            "type": "효능/사용감/품질/기능"
        }
    ]
}

⚠️ 중요: 명확한 모순만 보고하세요. 단순한 개인차이나 애매한 경우는 제외하세요."""
    
    def _calculate_penalty_score(self, contradictions: List[Dict]) -> float:
        """모순에 따른 점수 차감 계산 (100점 만점 기준)"""
        penalty_mapping = {
            "high": 16.0,    # 심각한 모순: 16점 차감 (5점 만점에서 0.8점 * 20)
            "medium": 8.0,   # 중간 모순: 8점 차감 (5점 만점에서 0.4점 * 20)
            "low": 4.0       # 경미한 모순: 4점 차감 (5점 만점에서 0.2점 * 20)
        }
        
        total_penalty = 0.0
        
        for contradiction in contradictions:
            severity = contradiction.get("severity", "low")
            penalty = penalty_mapping.get(severity, 4.0)
            total_penalty += penalty
            
            logger.debug(f"모순 발견: {contradiction.get('claim', 'N/A')} "
                        f"(심각도: {severity}, 차감: {penalty}점)")
        
        # 최대 차감 점수 제한 (50점)
        max_penalty = 50.0
        if total_penalty > max_penalty:
            logger.info(f"차감 점수가 최대값을 초과했습니다: {total_penalty:.2f} -> {max_penalty}")
            total_penalty = max_penalty
        
        return total_penalty
    
    async def evaluate_product(self, product_id: int) -> Dict:
        """
        제품 종합 평가 실행
        
        Args:
            product_id: 평가할 제품 ID
            
        Returns:
            전체 평가 결과
        """
        try:
            logger.info(f"제품 ID {product_id} 종합 평가 시작")
            
            # 1단계: 가중평균 점수 계산
            weighted_score, calculation_details = self.calculate_weighted_score(product_id)
            
            if weighted_score == 0.0:
                logger.error(f"제품 ID {product_id}의 기본 점수 계산 실패")
                return {"error": "기본 점수 계산 실패"}
            
            # 2단계: 모순 탐지 및 점수 차감
            contradictions, penalty_score = await self.detect_contradictions(product_id)
            
            # 3단계: 100점 만점으로 변환 및 최종 점수 계산
            weighted_score_100 = self._convert_to_100_scale(weighted_score)
            final_score_100 = max(0.0, weighted_score_100 - penalty_score)  # 최소 0점
            
            # 평가 결과 정리
            evaluation_result = {
                "product_id": product_id,
                "weighted_score_5": weighted_score,  # 5점 만점 점수 (참고용)
                "weighted_score": weighted_score_100,  # 100점 만점 점수
                "contradictions": contradictions,
                "penalty_score": penalty_score,
                "final_score": final_score_100,
                "calculation_details": calculation_details,
                "evaluation_summary": {
                    "total_contradictions": len(contradictions),
                    "score_improvement_from_base": final_score_100 - weighted_score_100,
                    "evaluation_grade": self._get_evaluation_grade(final_score_100)
                }
            }
            
            # 데이터베이스에 저장 (100점 만점으로 저장)
            evaluation_details_json = json.dumps(evaluation_result, ensure_ascii=False)
            save_success = save_product_evaluation(
                product_id=product_id,
                weighted_score=weighted_score_100,
                contradiction_penalties=penalty_score,
                final_score=final_score_100,
                evaluation_details=evaluation_details_json
            )
            
            if save_success:
                logger.info(f"제품 ID {product_id} 평가 결과 저장 완료")
            else:
                logger.error(f"제품 ID {product_id} 평가 결과 저장 실패")
            
            logger.info(f"제품 ID {product_id} 종합 평가 완료: {final_score_100:.1f}/100점")
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"제품 평가 중 오류: {e}")
            return {"error": str(e)}
    
    async def analyze_claims_vs_reality(self, product_id: int) -> Optional[Dict]:
        """
        제품 상세정보의 마케팅 주장과 실제 소비자 리뷰 간의 차이점 분석
        
        Args:
            product_id: 분석할 제품 ID
            
        Returns:
            분석 결과 딕셔너리 또는 None
        """
        try:
            logger.info(f"제품 ID {product_id}의 마케팅 주장 vs 실제 리뷰 분석 시작")
            
            # 1. 제품 상세정보 가져오기
            from .database import DB_FILE
            import sqlite3
            
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()
            cur.execute("SELECT detailed_summary FROM products WHERE id = ?", (product_id,))
            summary_result = cur.fetchone()
            con.close()
            
            if not summary_result or not summary_result[0]:
                logger.warning(f"제품 ID {product_id}의 상세정보를 찾을 수 없습니다.")
                return None
            
            product_summary = summary_result[0]
            
            # 2. 리뷰 분석 결과 가져오기
            from .database import get_review_analysis_results
            review_results = get_review_analysis_results(product_id)
            
            if not review_results:
                logger.warning(f"제품 ID {product_id}의 리뷰 분석 결과를 찾을 수 없습니다.")
                return None
            
            # 3. 상세정보에서 주요 주장 추출
            import json
            try:
                # product_summary는 문자열이므로 직접 사용
                # ```json 으로 감싸진 형태에서 JSON 부분만 추출
                summary_text = product_summary
                if summary_text.startswith('```json'):
                    # ```json과 ```를 제거하고 JSON 부분만 추출
                    start_idx = summary_text.find('{')
                    end_idx = summary_text.rfind('}') + 1
                    if start_idx != -1 and end_idx != 0:
                        json_text = summary_text[start_idx:end_idx]
                        detailed_info = json.loads(json_text)
                    else:
                        raise json.JSONDecodeError("JSON 구조를 찾을 수 없음", summary_text, 0)
                else:
                    # 일반 JSON 문자열로 시도
                    detailed_info = json.loads(summary_text)
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"제품 ID {product_id}의 상세정보 파싱 실패: {e}")
                logger.error(f"문제가 된 텍스트 (처음 200자): {product_summary[:200] if product_summary else 'None'}")
                return None
            
            # 4. 리뷰에서 장단점 통합
            all_advantages = []
            all_disadvantages = []
            
            for result in review_results:
                _, _, sentiment_group, advantages_json, disadvantages_json, _, _ = result
                
                try:
                    advantages = json.loads(advantages_json) if advantages_json else []
                    disadvantages = json.loads(disadvantages_json) if disadvantages_json else []
                    
                    all_advantages.extend(advantages)
                    all_disadvantages.extend(disadvantages)
                except json.JSONDecodeError:
                    continue
            
            # 5. AI를 사용한 모순 분석
            analysis_result = await self._analyze_claims_vs_reality_with_ai(
                detailed_info, all_advantages, all_disadvantages
            )
            
            # 분석 결과를 데이터베이스에 저장
            from .database import save_claims_vs_reality_analysis
            save_success = save_claims_vs_reality_analysis(product_id, analysis_result)
            
            if save_success:
                logger.info(f"제품 ID {product_id}의 마케팅 주장 vs 실제 리뷰 분석 결과가 데이터베이스에 저장되었습니다.")
            else:
                logger.warning(f"제품 ID {product_id}의 분석 결과 저장에 실패했지만 결과는 반환합니다.")
            
            logger.info(f"제품 ID {product_id}의 마케팅 주장 vs 실제 리뷰 분석 완료")
            return analysis_result
            
        except Exception as e:
            logger.error(f"마케팅 주장 vs 실제 리뷰 분석 중 오류: {e}")
            return None
    
    async def _analyze_claims_vs_reality_with_ai(self, detailed_info: Dict, advantages: List, disadvantages: List) -> Dict:
        """AI를 사용하여 마케팅 주장과 실제 리뷰 간의 차이점 분석"""
        try:
            # 상세정보에서 주요 주장 요약
            product_claims = {
                "summary": detailed_info.get("product_summary", ""),
                "key_ingredients": detailed_info.get("key_ingredients", []),
                "benefits_claims": detailed_info.get("benefits_claims", []),
                "usage_instructions": detailed_info.get("usage_instructions", ""),
                "specifications": detailed_info.get("specifications", {})
            }
            
            # 리뷰에서 주요 포인트 요약
            review_points = {
                "advantages": [item.get("point", "") + ": " + item.get("details", "") for item in advantages if isinstance(item, dict)],
                "disadvantages": [item.get("point", "") + ": " + item.get("details", "") for item in disadvantages if isinstance(item, dict)]
            }
            
            prompt = f"""당신은 제품 분석 전문가입니다. 제품의 마케팅 주장과 실제 소비자 리뷰를 비교하여 차이점을 분석해주세요.

📋 제품의 마케팅 주장:
- 제품 요약: {product_claims['summary']}
- 주요 성분: {', '.join(product_claims['key_ingredients']) if product_claims['key_ingredients'] else '정보 없음'}
- 효과 주장: {', '.join(product_claims['benefits_claims']) if product_claims['benefits_claims'] else '정보 없음'}
- 사용법: {product_claims['usage_instructions']}

🗣️ 실제 소비자 리뷰:
긍정적 피드백:
{chr(10).join('• ' + point for point in review_points['advantages'][:10]) if review_points['advantages'] else '• 없음'}

부정적 피드백:
{chr(10).join('• ' + point for point in review_points['disadvantages'][:10]) if review_points['disadvantages'] else '• 없음'}

다음 기준으로 분석해주세요:
1. 마케팅에서 강조한 효과와 실제 소비자 경험의 차이
2. 예상과 다른 부작용이나 문제점
3. 사용법이나 기대 효과의 현실성
4. 전반적인 신뢰도 평가

반드시 JSON 형태로만 응답하세요:
{{
    "contradictions": [
        {{
            "claim": "마케팅에서 주장한 내용",
            "reality": "실제 소비자 경험",
            "severity": "높음/보통/낮음",
            "description": "구체적인 차이점 설명"
        }}
    ],
    "consistency_points": [
        "마케팅 주장과 일치하는 점들"
    ],
    "overall_assessment": "전반적인 평가 (2-3문장)",
    "trust_level": "높음/보통/낮음"
}}"""

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 제품 분석 전문가입니다. 마케팅 주장과 실제 리뷰를 객관적으로 비교 분석합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                parsed_result = json.loads(result)
                logger.info("마케팅 주장 vs 실제 리뷰 분석 완료 (직접 파싱 성공)")
                return parsed_result
            except json.JSONDecodeError:
                # 백업 파싱 로직
                try:
                    if "```json" in result:
                        json_start = result.find("```json") + 7
                        json_end = result.find("```", json_start)
                        if json_end != -1:
                            json_content = result[json_start:json_end].strip()
                            parsed_result = json.loads(json_content)
                            logger.info("마케팅 주장 vs 실제 리뷰 분석 완료 (JSON 블록 추출 성공)")
                            return parsed_result
                    
                    # 중괄호 추출 시도
                    json_start = result.find("{")
                    json_end = result.rfind("}") + 1
                    if json_start != -1 and json_end > json_start:
                        json_content = result[json_start:json_end]
                        parsed_result = json.loads(json_content)
                        logger.info("마케팅 주장 vs 실제 리뷰 분석 완료 (중괄호 추출 성공)")
                        return parsed_result
                        
                except json.JSONDecodeError:
                    pass
                
                logger.warning("JSON 파싱 실패, 기본 구조 반환")
                return {
                    "contradictions": [],
                    "consistency_points": [],
                    "overall_assessment": "분석 중 오류가 발생했습니다.",
                    "trust_level": "보통",
                    "raw_response": result
                }
                
        except Exception as e:
            logger.error(f"AI 마케팅 주장 vs 실제 리뷰 분석 중 오류: {e}")
            return {
                "contradictions": [],
                "consistency_points": [],
                "overall_assessment": "분석 중 오류가 발생했습니다.",
                "trust_level": "보통",
                "error": str(e)
            }
    
    def _convert_to_100_scale(self, score_5: float) -> float:
        """5점 만점 점수를 100점 만점으로 변환"""
        return (score_5 / 5.0) * 100.0
    
    def _get_evaluation_grade(self, score_100: float) -> str:
        """점수에 따른 평가 등급 반환 (100점 만점 기준)"""
        if score_100 >= 90:
            return "A+ (우수)"
        elif score_100 >= 80:
            return "A (좋음)"
        elif score_100 >= 70:
            return "B+ (보통 이상)"
        elif score_100 >= 60:
            return "B (보통)"
        elif score_100 >= 50:
            return "C+ (미흡)"
        elif score_100 >= 40:
            return "C (부족)"
        else:
            return "D (매우 부족)"
    
    def get_evaluation_summary(self, product_id: int) -> Optional[Dict]:
        """특정 제품의 평가 요약 조회"""
        try:
            evaluation_result = get_product_evaluation(product_id)
            
            if not evaluation_result:
                return None
            
            product_id, name, weighted_score, penalty, final_score, details, evaluated_at = evaluation_result
            
            try:
                details_parsed = json.loads(details) if details else {}
            except json.JSONDecodeError:
                details_parsed = {}
            
            return {
                "product_id": product_id,
                "product_name": name,
                "weighted_score": weighted_score,
                "penalty_score": penalty,
                "final_score": final_score,
                "grade": self._get_evaluation_grade(final_score),
                "contradictions_count": len(details_parsed.get("contradictions", [])),
                "evaluated_at": evaluated_at
            }
            
        except Exception as e:
            logger.error(f"평가 요약 조회 중 오류: {e}")
            return None
    
    async def get_evaluation_stats(self) -> Dict:
        """전체 평가 통계 정보"""
        try:
            evaluations = get_all_product_evaluations()
            
            if not evaluations:
                return {"message": "평가된 제품이 없습니다."}
            
            scores = [eval_data[4] for eval_data in evaluations]  # final_score
            
            stats = {
                "total_evaluated": len(evaluations),
                "average_score": sum(scores) / len(scores),
                "highest_score": max(scores),
                "lowest_score": min(scores),
                "grade_distribution": {},
                "top_products": []
            }
            
            # 등급 분포 계산
            for _, name, weighted, penalty, final, evaluated_at in evaluations:
                grade = self._get_evaluation_grade(final)
                stats["grade_distribution"][grade] = stats["grade_distribution"].get(grade, 0) + 1
                
                stats["top_products"].append({
                    "name": name,
                    "final_score": final,
                    "grade": grade
                })
            
            # 상위 제품 정렬 (점수 높은 순)
            stats["top_products"].sort(key=lambda x: x["final_score"], reverse=True)
            stats["top_products"] = stats["top_products"][:5]  # 상위 5개만
            
            return stats
            
        except Exception as e:
            logger.error(f"평가 통계 조회 중 오류: {e}")
            return {"error": str(e)}