"""LangChain ReAct 에이전트 구현"""
import os
from typing import List, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage
from loguru import logger
from dotenv import load_dotenv

from .tools import ScrapingTool, ImageTextExtractionTool, DatabaseQueryTool, ProductSummaryTool
from .prompts import REACT_PROMPT

# 환경변수 로드
load_dotenv()


class OliveYoungAgent:
    """올리브영 제품 분석 전문 에이전트"""
    
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.0):
        """
        에이전트 초기화
        
        Args:
            model_name: 사용할 OpenAI 모델명
            temperature: 응답의 창의성 수준 (0.0 = 일관적, 1.0 = 창의적)
        """
        self.model_name = model_name
        self.temperature = temperature
        
        # OpenAI API 키 확인
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        # LLM 초기화
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key
        )
        
        # 도구 초기화
        self.tools = self._initialize_tools()
        
        # 에이전트 초기화
        self.agent = self._create_agent()
        
        # 에이전트 실행기 초기화
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            max_execution_time=600,  # 10분 제한
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        logger.info(f"OliveYoungAgent 초기화 완료 (모델: {model_name})")
    
    def _initialize_tools(self) -> List[BaseTool]:
        """도구 목록 초기화"""
        tools = [
            ScrapingTool(),
            ImageTextExtractionTool(),
            ProductSummaryTool(),
            DatabaseQueryTool()
        ]
        
        logger.info(f"{len(tools)}개 도구 초기화 완료")
        return tools
    
    def _create_agent(self):
        """ReAct 에이전트 생성"""
        prompt = PromptTemplate.from_template(REACT_PROMPT)
        
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return agent
    
    async def process_url(self, url: str) -> str:
        """
        올리브영 URL을 처리하여 완전한 분석 수행
        
        Args:
            url: 올리브영 제품 URL
            
        Returns:
            처리 결과 요약
        """
        try:
            logger.info(f"URL 처리 시작: {url}")
            
            # 에이전트 실행
            result = await self.agent_executor.ainvoke({
                "input": f"다음 올리브영 제품 URL을 완전히 분석해주세요: {url}\n\n작업 순서:\n1. 제품 정보 스크래핑\n2. 모든 상세 이미지에서 텍스트 추출\n3. 추출된 텍스트들을 통합하여 구조화된 제품 상세정보 생성\n4. 최종 결과 요약"
            })
            
            return result["output"]
            
        except Exception as e:
            logger.error(f"URL 처리 오류: {e}")
            return f"❌ 처리 중 오류가 발생했습니다: {str(e)}"
    
    async def chat(self, message: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        """
        사용자와 대화형 상호작용
        
        Args:
            message: 사용자 메시지
            chat_history: 대화 기록 (선택사항)
            
        Returns:
            에이전트 응답
        """
        try:
            logger.info(f"사용자 메시지: {message}")
            
            # 에이전트 실행
            result = await self.agent_executor.ainvoke({
                "input": message,
                "chat_history": chat_history or []
            })
            
            return result["output"]
            
        except Exception as e:
            logger.error(f"채팅 처리 오류: {e}")
            return f"❌ 죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}"
    
    def get_tools_info(self) -> str:
        """사용 가능한 도구 정보 반환"""
        info = "🔧 사용 가능한 도구:\n\n"
        for tool in self.tools:
            info += f"• **{tool.name}**: {tool.description}\n\n"
        return info
    
    def get_stats(self) -> str:
        """에이전트 통계 정보 반환"""
        return f"""📊 에이전트 정보:
- 모델: {self.model_name}
- 온도: {self.temperature}
- 도구 개수: {len(self.tools)}개
- 최대 반복: 10회
- 최대 실행시간: 10분"""


class SimpleOliveYoungAgent:
    """간단한 올리브영 에이전트 (도구 체인 방식)"""
    
    def __init__(self):
        """간단한 에이전트 초기화"""
        # 도구들 초기화
        self.scraping_tool = ScrapingTool()
        self.extraction_tool = ImageTextExtractionTool()
        self.summary_tool = ProductSummaryTool()
        self.query_tool = DatabaseQueryTool()
        
        # 추가 컴포넌트 초기화 (완전한 플로우를 위해)
        from ..review_classifier import ReviewClassifier
        from ..product_evaluator import ProductEvaluator
        self.review_classifier = ReviewClassifier()
        self.product_evaluator = ProductEvaluator()
        
        logger.info("SimpleOliveYoungAgent 초기화 완료")
    
    async def process_url_simple(self, url: str) -> str:
        """
        URL을 완전하게 처리 (6단계 완전한 플로우)

        Args:
            url: 올리브영 제품 URL

        Returns:
            처리 결과
        """
        try:
            logger.info(f"완전한 플로우 처리 시작: {url}")

            # 1단계: 스크래핑
            logger.info("1단계: 제품 스크래핑 시작...")
            scraping_result = await self.scraping_tool._arun(url)
            print(f"✅ 1단계 완료 - 스크래핑 결과:\n{scraping_result}\n")

            # 제품 ID 추출 시도
            product_id = None
            import re
            import sqlite3
            from pathlib import Path

            if "제품 ID:" in scraping_result:
                product_id_match = re.search(r"제품 ID: (\d+)", scraping_result)
                if product_id_match:
                    product_id = int(product_id_match.group(1))
                    logger.info(f"✅ 스크래핑 성공 - 제품 ID: {product_id}")

            # 스크래핑 실패 시, 기존 DB에서 URL로 제품 찾기
            if not product_id:
                logger.warning("⚠️ 스크래핑 실패 - 기존 데이터베이스에서 제품 검색 중...")
                try:
                    DB_FILE = Path("creait.db")
                    con = sqlite3.connect(DB_FILE)
                    cur = con.cursor()
                    cur.execute("SELECT id FROM products WHERE url = ? ORDER BY id DESC LIMIT 1", (url,))
                    result = cur.fetchone()
                    con.close()

                    if result:
                        product_id = result[0]
                        logger.info(f"✅ 기존 데이터베이스에서 제품 발견 - 제품 ID: {product_id}")
                        scraping_result += f"\n\n⚠️ 주의: 새로운 스크래핑은 실패했으나, 기존 데이터베이스에서 제품 ID {product_id}를 찾았습니다.\n기존 데이터로 나머지 플로우를 진행합니다."
                    else:
                        logger.error("❌ 기존 데이터베이스에서도 제품을 찾을 수 없습니다.")
                except Exception as e:
                    logger.error(f"데이터베이스 조회 오류: {e}")

            # 제품 ID가 있는 경우에만 나머지 플로우 진행
            if product_id:
                # 2단계: 이미지 텍스트 추출
                logger.info("2단계: 이미지 텍스트 추출 시작...")
                extraction_result = await self.extraction_tool._arun(product_id)
                print(f"✅ 2단계 완료 - 텍스트 추출 결과:\n{extraction_result}\n")

                # 3단계: 텍스트 통합 및 구조화
                logger.info("3단계: 텍스트 통합 및 구조화 시작...")
                summary_result = await self.summary_tool._arun(product_id)
                print(f"✅ 3단계 완료 - 텍스트 통합 결과:\n{summary_result}\n")

                # 4단계: 리뷰 분류 및 장단점 추출
                logger.info("4단계: 리뷰 분류 및 장단점 추출 시작...")
                review_analysis = await self.review_classifier.analyze_product_reviews(product_id)

                if review_analysis:
                    review_result = "📊 리뷰 분류 및 장단점 분석 완료!\n"
                    for group_name, group_data in review_analysis.items():
                        review_count = group_data.get('review_count', 0)
                        analysis = group_data.get('analysis', {})
                        advantages = analysis.get('advantages', [])
                        disadvantages = analysis.get('disadvantages', [])

                        review_result += f"\n🏷️ {group_name} ({review_count}개 리뷰)\n"
                        review_result += f"  - 장점: {len(advantages)}개 항목\n"
                        review_result += f"  - 단점: {len(disadvantages)}개 항목\n"
                else:
                    review_result = "❌ 리뷰 분석에 실패했습니다."

                print(f"✅ 4단계 완료 - {review_result}\n")

                # 5단계: 제품 평가 및 점수 계산
                logger.info("5단계: 제품 평가 및 점수 계산 시작...")
                evaluation_result = await self.product_evaluator.evaluate_product(product_id)

                if evaluation_result:
                    eval_result = f"🎯 제품 평가 완료!\n"
                    eval_result += f"  - 최종 점수: {evaluation_result.get('final_score', 'N/A')}/100점\n"
                    eval_result += f"  - 등급: {evaluation_result.get('grade', 'N/A')}\n"

                    weighted_avg = evaluation_result.get('weighted_average', 'N/A')
                    if isinstance(weighted_avg, (int, float)):
                        eval_result += f"  - 가중 평균: {weighted_avg:.1f}/5.0\n"
                    else:
                        eval_result += f"  - 가중 평균: {weighted_avg}/5.0\n"

                    eval_result += f"  - 모순 탐지: {evaluation_result.get('contradiction_level', 'N/A')}\n"
                else:
                    eval_result = "❌ 제품 평가에 실패했습니다."

                print(f"✅ 5단계 완료 - {eval_result}\n")

                # 5-1단계: 마케팅 주장 vs 실제 리뷰 모순 분석
                logger.info("5-1단계: 마케팅 주장 vs 실제 리뷰 모순 분석 시작...")
                contradiction_analysis = await self.product_evaluator.analyze_claims_vs_reality(product_id)

                if contradiction_analysis:
                    contradiction_result = f"🔍 모순 분석 완료!\n"

                    # 모순점 표시
                    contradictions = contradiction_analysis.get('contradictions', [])
                    if contradictions:
                        contradiction_result += f"  - 발견된 모순: {len(contradictions)}개\n"
                        for i, contradiction in enumerate(contradictions[:3], 1):  # 최대 3개만 표시
                            point = contradiction.get('point', 'N/A')[:50]
                            contradiction_result += f"    {i}. {point}...\n"
                    else:
                        contradiction_result += "  - 발견된 모순: 없음\n"

                    # 신뢰도 수준 표시
                    trust_level = contradiction_analysis.get('trust_level', 'N/A')
                    contradiction_result += f"  - 신뢰도 수준: {trust_level}\n"

                    # 전체 평가 요약
                    overall = contradiction_analysis.get('overall_assessment', '')
                    if overall and len(overall) > 100:
                        contradiction_result += f"  - 종합 평가: {overall[:100]}...\n"
                    elif overall:
                        contradiction_result += f"  - 종합 평가: {overall}\n"
                else:
                    contradiction_result = "❌ 모순 분석에 실패했습니다."

                print(f"✅ 5-1단계 완료 - {contradiction_result}\n")

                # 6단계: 최종 통계
                logger.info("6단계: 최종 통계 조회...")
                stats_result = self.query_tool._run(product_id, "statistics")
                print(f"✅ 6단계 완료 - 통계 결과:\n{stats_result}\n")

                # 완전한 결과 반환
                return f"""🎉 완전한 올리브영 제품 분석 완료!

📋 === 1단계: 제품 스크래핑 ===
{scraping_result}

📸 === 2단계: 이미지 텍스트 추출 ===
{extraction_result}

📝 === 3단계: 텍스트 통합 및 구조화 ===
{summary_result}

📊 === 4단계: 리뷰 분류 및 장단점 분석 ===
{review_result}

🎯 === 5단계: 제품 평가 및 점수 계산 ===
{eval_result}

🔍 === 5-1단계: 마케팅 주장 vs 실제 리뷰 모순 분석 ===
{contradiction_result}

📈 === 6단계: 최종 통계 ===
{stats_result}

🚀 모든 단계가 성공적으로 완료되었습니다!
사용자는 이제 URL 하나로 완전한 제품 신뢰도 분석을 받을 수 있습니다."""
            else:
                return f"""❌ 제품 ID를 찾을 수 없습니다.

스크래핑 결과: {scraping_result}

⚠️ 새로운 스크래핑과 기존 데이터베이스 검색 모두 실패했습니다.
다음을 확인해주세요:
1. URL이 올바른 올리브영 제품 페이지인지 확인
2. 네트워크 연결 상태 확인
3. 이전에 이 제품을 스크래핑한 적이 있는지 확인"""
                
        except Exception as e:
            logger.error(f"완전한 플로우 처리 오류: {e}")
            return f"❌ 처리 중 오류가 발생했습니다: {str(e)}"