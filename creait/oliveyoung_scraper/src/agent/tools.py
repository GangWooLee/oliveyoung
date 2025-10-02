"""LangChain 도구 정의"""
import asyncio
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from loguru import logger

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ..scraper.oliveyoung_scraper import OliveYoungScraper
from ..database import init_db, save_product_info, get_product_images_with_ids, save_image_text
from ..image_text_extractor import ImageTextExtractor
from ..product_summarizer import ProductSummarizer


class ScrapingInput(BaseModel):
    """스크래핑 도구 입력 스키마"""
    url: str = Field(description="스크래핑할 올리브영 제품 URL")


class ScrapingTool(BaseTool):
    """올리브영 제품 스크래핑 도구"""
    name: str = "scrape_oliveyoung_product"
    description: str = """올리브영 제품 URL을 입력받아 제품 정보, 리뷰, 이미지를 스크래핑합니다.
    URL은 반드시 oliveyoung.co.kr 도메인이어야 합니다.
    성공 시 제품 ID와 수집된 데이터 요약을 반환합니다."""
    args_schema: Type[BaseModel] = ScrapingInput

    def _run(self, url: str) -> str:
        """동기 실행 (비추천)"""
        return asyncio.run(self._arun(url))

    async def _arun(self, url: str) -> str:
        """비동기 실행"""
        try:
            # URL 유효성 검사
            if "oliveyoung.co.kr" not in url:
                return f"❌ 오류: 올리브영 URL이 아닙니다. (입력: {url})"

            logger.info(f"스크래핑 시작: {url}")
            
            # 데이터베이스 초기화
            init_db()

            # 스크래핑 실행
            async with OliveYoungScraper(headless=False) as scraper:
                product = await scraper.scrape(url, max_reviews=300)

                # 데이터베이스에 저장
                save_product_info(product, url)

                # 저장된 제품 ID 찾기
                DB_FILE = Path("creait.db")
                con = sqlite3.connect(DB_FILE)
                cur = con.cursor()
                cur.execute("SELECT id FROM products WHERE url = ?", (url,))
                result = cur.fetchone()
                con.close()

                if result:
                    product_id = result[0]
                    return f"""✅ 스크래핑 완료!
📊 제품 ID: {product_id}
📝 제품명: {product.name}
💰 가격: {product.price}
⭐ 평점: {product.rating}
📱 리뷰 수: {product.review_count}
🖼️ 상세 이미지: {len(product.detail_images)}개
📄 수집된 리뷰: {len(product.reviews)}개

다음 단계: 상세 이미지에서 텍스트 추출을 시작할 수 있습니다."""
                else:
                    return "❌ 오류: 제품 정보는 스크래핑되었지만 제품 ID를 찾을 수 없습니다."

        except Exception as e:
            logger.error(f"스크래핑 오류: {e}")
            return f"❌ 스크래핑 실패: {str(e)}"


class ImageExtractionInput(BaseModel):
    """이미지 텍스트 추출 도구 입력 스키마"""
    product_id: int = Field(description="텍스트를 추출할 제품의 ID")


class ImageTextExtractionTool(BaseTool):
    """이미지 텍스트 추출 도구"""
    name: str = "extract_image_text"
    description: str = """제품 ID를 입력받아 해당 제품의 모든 상세 이미지에서 텍스트를 추출합니다.
    OpenAI Vision API를 사용하여 이미지의 텍스트를 구조화된 형태로 추출합니다.
    처리 시간이 오래 걸릴 수 있으며, 진행상황과 최종 통계를 반환합니다."""
    args_schema: Type[BaseModel] = ImageExtractionInput

    def _run(self, product_id: int) -> str:
        """동기 실행 (비추천)"""
        return asyncio.run(self._arun(product_id))

    async def _arun(self, product_id: int) -> str:
        """비동기 실행"""
        try:
            logger.info(f"이미지 텍스트 추출 시작: 제품 ID {product_id}")

            # 제품 이미지 가져오기
            product_images = get_product_images_with_ids(product_id)
            
            if not product_images:
                return f"❌ 제품 ID {product_id}에 대한 이미지가 없습니다."

            total_images = len(product_images)
            logger.info(f"총 {total_images}개 이미지 발견")

            extractor = ImageTextExtractor()
            
            # 이미지 URL들만 추출
            image_urls = [img[3] for img in product_images]
            image_data = {img[3]: (img[0], img[1], img[2]) for img in product_images}  # URL -> (id, _, name)
            
            logger.info(f"배치 처리로 {total_images}개 이미지 텍스트 추출 시작...")
            
            # 배치 처리로 텍스트 추출 (순차 처리 - 최고 안정성)
            extracted_texts_map = await extractor.extract_text_from_multiple_images(
                image_urls, 
                max_concurrent=1
            )
            
            successful_count = 0
            failed_count = 0
            
            # 결과 처리 및 데이터베이스 저장
            for i, (image_url, extracted_text) in enumerate(extracted_texts_map.items(), 1):
                image_id, _, product_name = image_data[image_url]
                
                logger.info(f"결과 처리 {i}/{total_images}: 이미지 ID {image_id}")
                
                try:
                    # 성공적인 추출인지 확인
                    if extracted_text and extracted_text.strip() and len(extracted_text.strip()) > 20:
                        # 거부 응답 확인
                        invalid_responses = [
                            "i'm unable to", "i can't assist", "i'm sorry", "i cannot",
                            "unable to provide", "can't help", "죄송하지만", "추출할 수 없습니다"
                        ]
                        
                        if any(invalid in extracted_text.lower() for invalid in invalid_responses):
                            logger.warning(f"이미지 {i}: OpenAI가 텍스트 추출을 거부")
                            failed_count += 1
                            continue

                        # 데이터베이스에 저장
                        success = save_image_text(image_id, product_id, image_url, extracted_text)
                        
                        if success:
                            successful_count += 1
                            logger.info(f"✅ 이미지 {i}: 텍스트 저장 성공")
                        else:
                            failed_count += 1
                            logger.error(f"❌ 이미지 {i}: 데이터베이스 저장 실패")
                    else:
                        failed_count += 1
                        logger.warning(f"❌ 이미지 {i}: 빈 텍스트 또는 너무 짧은 텍스트")
                        
                except Exception as e:
                    logger.error(f"이미지 {i} 결과 처리 중 오류: {e}")
                    failed_count += 1
                    continue

            success_rate = (successful_count / total_images) * 100 if total_images > 0 else 0

            return f"""✅ 이미지 텍스트 추출 완료!

📊 처리 결과:
- 총 이미지: {total_images}개
- 성공: {successful_count}개
- 실패: {failed_count}개
- 성공률: {success_rate:.1f}%

🎯 추출된 텍스트는 데이터베이스에 저장되었습니다.
이제 제품 정보와 이미지 텍스트를 조회할 수 있습니다."""

        except Exception as e:
            logger.error(f"이미지 텍스트 추출 오류: {e}")
            return f"❌ 이미지 텍스트 추출 실패: {str(e)}"


class DatabaseQueryInput(BaseModel):
    """데이터베이스 조회 도구 입력 스키마"""
    product_id: Optional[int] = Field(default=None, description="조회할 제품 ID (선택사항)")
    query_type: str = Field(description="조회 유형: 'product_info', 'image_texts', 'reviews', 'statistics'")


class DatabaseQueryTool(BaseTool):
    """데이터베이스 조회 도구"""
    name: str = "query_database"
    description: str = """데이터베이스에서 제품 정보, 이미지 텍스트, 리뷰 등을 조회합니다.
    query_type 옵션:
    - 'product_info': 제품 기본 정보
    - 'image_texts': 추출된 이미지 텍스트
    - 'reviews': 제품 리뷰
    - 'statistics': 전체 통계
    product_id가 제공되면 해당 제품만, 없으면 전체 데이터를 조회합니다."""
    args_schema: Type[BaseModel] = DatabaseQueryInput

    def _run(self, product_id: Optional[int] = None, query_type: str = "product_info") -> str:
        """동기 실행"""
        try:
            DB_FILE = Path("creait.db")
            con = sqlite3.connect(DB_FILE)
            cur = con.cursor()

            if query_type == "product_info":
                if product_id:
                    cur.execute("""
                        SELECT id, name, price, rating, review_count 
                        FROM products WHERE id = ?
                    """, (product_id,))
                    result = cur.fetchone()
                    if result:
                        return f"""📦 제품 정보 (ID: {result[0]}):
- 제품명: {result[1]}
- 가격: {result[2]}
- 평점: {result[3]}
- 리뷰 수: {result[4]}"""
                    else:
                        return f"❌ 제품 ID {product_id}를 찾을 수 없습니다."
                else:
                    cur.execute("SELECT id, name, price, rating FROM products ORDER BY id DESC LIMIT 5")
                    results = cur.fetchall()
                    if results:
                        output = "📦 최근 제품 목록 (최대 5개):\n"
                        for r in results:
                            output += f"- ID {r[0]}: {r[1]} (가격: {r[2]}, 평점: {r[3]})\n"
                        return output
                    else:
                        return "❌ 등록된 제품이 없습니다."

            elif query_type == "image_texts":
                if product_id:
                    cur.execute("""
                        SELECT COUNT(*), 
                               AVG(LENGTH(extracted_text)) as avg_length
                        FROM product_image_texts WHERE product_id = ?
                    """, (product_id,))
                    count_result = cur.fetchone()
                    
                    cur.execute("""
                        SELECT SUBSTR(extracted_text, 1, 200) || '...' as preview
                        FROM product_image_texts 
                        WHERE product_id = ? 
                        ORDER BY extracted_at DESC LIMIT 3
                    """, (product_id,))
                    preview_results = cur.fetchall()
                    
                    output = f"""🖼️ 이미지 텍스트 정보 (제품 ID: {product_id}):
- 추출된 텍스트 수: {count_result[0]}개
- 평균 텍스트 길이: {count_result[1]:.0f}자

📝 최근 추출 텍스트 미리보기:"""
                    for i, preview in enumerate(preview_results, 1):
                        output += f"\n{i}. {preview[0]}"
                    
                    return output
                else:
                    return "❌ 이미지 텍스트 조회에는 product_id가 필요합니다."

            elif query_type == "reviews":
                if product_id:
                    cur.execute("""
                        SELECT review_text, review_rating 
                        FROM product_reviews 
                        WHERE product_id = ? 
                        ORDER BY id DESC LIMIT 5
                    """, (product_id,))
                    results = cur.fetchall()
                    if results:
                        output = f"💬 제품 리뷰 (제품 ID: {product_id}, 최대 5개):\n"
                        for i, (text, rating) in enumerate(results, 1):
                            output += f"{i}. ⭐{rating}점: {text[:100]}...\n"
                        return output
                    else:
                        return f"❌ 제품 ID {product_id}의 리뷰가 없습니다."
                else:
                    return "❌ 리뷰 조회에는 product_id가 필요합니다."

            elif query_type == "statistics":
                cur.execute("SELECT COUNT(*) FROM products")
                product_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM product_images")
                image_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM product_image_texts")
                text_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM product_reviews")
                review_count = cur.fetchone()[0]
                
                extraction_rate = (text_count / image_count * 100) if image_count > 0 else 0
                
                return f"""📊 데이터베이스 통계:
- 총 제품 수: {product_count}개
- 총 이미지 수: {image_count}개
- 텍스트 추출 완료: {text_count}개
- 총 리뷰 수: {review_count}개
- 텍스트 추출 성공률: {extraction_rate:.1f}%"""

            else:
                return f"❌ 알 수 없는 조회 유형: {query_type}"

        except Exception as e:
            logger.error(f"데이터베이스 조회 오류: {e}")
            return f"❌ 데이터베이스 조회 실패: {str(e)}"
        finally:
            con.close()

    async def _arun(self, product_id: Optional[int] = None, query_type: str = "product_info") -> str:
        """비동기 실행"""
        return self._run(product_id, query_type)


class ProductSummaryInput(BaseModel):
    """제품 요약 도구 입력 스키마"""
    product_id: int = Field(description="요약을 생성할 제품의 ID")


class ProductSummaryTool(BaseTool):
    """제품 이미지 텍스트 통합 및 요약 도구"""
    name: str = "summarize_product_texts"
    description: str = """제품 ID를 입력받아 해당 제품의 모든 이미지 텍스트를 통합하고 구조화된 상세정보로 정리합니다.
    추출된 이미지 텍스트들을 분석하여 성분, 효능, 사용법, 주의사항 등으로 분류하고
    중복을 제거하여 체계적인 제품 정보를 생성합니다.
    OpenAI GPT-4를 사용하여 JSON 형태의 구조화된 정보를 생성하고 데이터베이스에 저장합니다."""
    args_schema: Type[BaseModel] = ProductSummaryInput

    def _run(self, product_id: int) -> str:
        """동기 실행 (비추천)"""
        return asyncio.run(self._arun(product_id))

    async def _arun(self, product_id: int) -> str:
        """비동기 실행"""
        try:
            logger.info(f"제품 요약 생성 시작: 제품 ID {product_id}")

            # ProductSummarizer 인스턴스 생성
            summarizer = ProductSummarizer()
            
            # 제품 텍스트 통합 및 요약
            result = await summarizer.summarize_product_texts(product_id)
            
            if result:
                # 결과를 JSON으로 파싱하여 예쁘게 출력
                try:
                    import json
                    parsed_result = json.loads(result)
                    
                    # 새로운 구조에 맞게 정보 출력
                    product_info = parsed_result.get('product_info', {})
                    ingredients = parsed_result.get('detailed_ingredients', {})
                    benefits = parsed_result.get('benefits_and_effects', {})
                    usage = parsed_result.get('usage_instructions', {})
                    safety = parsed_result.get('safety_and_precautions', {})
                    certs = parsed_result.get('certifications_and_approvals', {})
                    additional = parsed_result.get('additional_details', {})
                    
                    formatted_output = f"""✅ 제품 상세정보 통합 완료!

📦 제품 정보:
- 브랜드: {product_info.get('brand_name', 'N/A')}
- 제품명: {product_info.get('product_name', 'N/A')}
- 용량: {product_info.get('volume_amount', 'N/A')}
- 제형: {product_info.get('form', 'N/A')}
- 제조정보: {product_info.get('manufacturing_info', 'N/A')}

🧪 성분 정보:
- 주성분: {', '.join(ingredients.get('main_ingredients', []))}
- 기능성원료: {', '.join(ingredients.get('functional_ingredients', []))}
- 전체원료: {ingredients.get('full_ingredient_list', 'N/A')[:200]}{'...' if len(str(ingredients.get('full_ingredient_list', ''))) > 200 else ''}

💡 효능 및 효과:
- 주요기능: {', '.join(benefits.get('primary_functions', []))}
- 상세효능: {', '.join(benefits.get('detailed_benefits', []))}
- 임상데이터: {benefits.get('clinical_data', 'N/A')}

📖 사용법:
- 복용량: {usage.get('dosage', 'N/A')}
- 복용빈도: {usage.get('frequency', 'N/A')}
- 복용시기: {usage.get('timing', 'N/A')}
- 상세사용법: {usage.get('detailed_method', 'N/A')}

⚠️ 안전 및 주의사항:
- 복용금지대상: {', '.join(safety.get('contraindications', []))}
- 주의사항: {', '.join(safety.get('warnings', []))}
- 보관방법: {safety.get('storage_instructions', 'N/A')}

🏆 인증 정보:
- 건강기능식품: {certs.get('health_functional_food', 'N/A')}
- 제조기준: {', '.join(certs.get('manufacturing_standards', []))}
- 기타인증: {', '.join(certs.get('other_certifications', []))}

ℹ️ 추가 상세정보:
- 제조공법: {additional.get('manufacturing_process', 'N/A')}
- 기타정보: {additional.get('other_important_info', 'N/A')}

🎯 구체적이고 상세한 제품 정보가 데이터베이스에 저장되었습니다."""
                
                except json.JSONDecodeError:
                    formatted_output = f"""✅ 제품 상세정보 통합 완료!

📝 통합된 제품 정보:
{result}

🎯 제품 상세정보가 데이터베이스에 저장되었습니다."""
                
                return formatted_output
            else:
                return f"❌ 제품 ID {product_id}의 텍스트 통합에 실패했습니다."

        except Exception as e:
            logger.error(f"제품 요약 생성 오류: {e}")
            return f"❌ 제품 요약 생성 실패: {str(e)}"