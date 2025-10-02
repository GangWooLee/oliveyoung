"""LangChain 에이전트 실행 스크립트"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from src.agent.agent import OliveYoungAgent, SimpleOliveYoungAgent


async def test_simple_agent():
    """간단한 에이전트 테스트"""
    print("🤖 SimpleOliveYoungAgent 시작...")
    
    # 사용자로부터 URL 입력받기
    url = input("📝 처리할 올리브영 제품 URL을 입력하세요: ").strip()
    if not url or "oliveyoung.co.kr" not in url:
        print("❌ 유효한 올리브영 URL이 아닙니다.")
        return
    
    agent = SimpleOliveYoungAgent()
    
    print(f"📝 처리할 URL: {url}")
    print("⏳ 처리 시작...\n")
    
    result = await agent.process_url_simple(url)
    
    print("\n" + "="*80)
    print("🎉 최종 결과:")
    print("="*80)
    print(result)


async def test_react_agent():
    """ReAct 에이전트 테스트"""
    print("🤖 OliveYoungAgent (ReAct) 테스트 시작...")
    
    try:
        agent = OliveYoungAgent(model_name="gpt-4", temperature=0.0)
        
        print("🛠️ 에이전트 정보:")
        print(agent.get_stats())
        print("\n" + agent.get_tools_info())
        
        # 테스트 URL
        test_url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000203347"
        
        print(f"📝 처리할 URL: {test_url}")
        print("⏳ 처리 시작...\n")
        
        result = await agent.process_url(test_url)
        
        print("\n" + "="*80)
        print("🎉 최종 결과:")
        print("="*80)
        print(result)
        
    except Exception as e:
        logger.error(f"ReAct 에이전트 오류: {e}")
        print(f"❌ ReAct 에이전트 실행 실패: {e}")


async def interactive_mode():
    """대화형 모드"""
    print("🎯 대화형 모드 시작...")
    print("'exit' 또는 'quit'를 입력하면 종료됩니다.")
    print("URL을 입력하거나 자연어로 질문해보세요.\n")
    
    try:
        agent = OliveYoungAgent(model_name="gpt-4", temperature=0.1)
        
        while True:
            user_input = input("💬 You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', '종료', '나가기']:
                print("👋 대화를 종료합니다.")
                break
                
            if not user_input:
                continue
                
            print("🤖 Agent: 처리 중...")
            response = await agent.chat(user_input)
            print(f"🤖 Agent: {response}\n")
            
    except KeyboardInterrupt:
        print("\n👋 사용자에 의해 종료되었습니다.")
    except Exception as e:
        logger.error(f"대화형 모드 오류: {e}")
        print(f"❌ 오류가 발생했습니다: {e}")


async def quick_process():
    """완전한 URL 처리 모드 - 사용자가 원하는 6단계 완전한 플로우"""
    print("🚀 올리브영 제품 신뢰도 분석기 (완전한 플로우)")
    print("="*60)
    
    # 사용자로부터 URL 입력받기
    url = input("📝 처리할 올리브영 제품 URL을 입력하세요: ").strip()
    if not url or "oliveyoung.co.kr" not in url:
        print("❌ 유효한 올리브영 URL이 아닙니다.")
        return
    
    print("\n🤖 완전한 분석 시스템 시작...")
    agent = SimpleOliveYoungAgent()
    
    print(f"📝 처리할 URL: {url}")
    print("⏳ 완전한 6단계 플로우 시작...\n")
    print("🔄 단계:")
    print("   1️⃣ 제품 스크래핑")
    print("   2️⃣ 이미지 텍스트 추출")
    print("   3️⃣ 텍스트 통합 및 구조화")
    print("   4️⃣ 리뷰 분류 및 장단점 분석")
    print("   5️⃣ 제품 평가 및 점수 계산")
    print("   6️⃣ 최종 통계\n")
    
    result = await agent.process_url_simple(url)
    
    print("\n" + "="*80)
    print("🎉 최종 결과:")
    print("="*80)
    print(result)

async def main():
    """메인 실행 함수"""
    print("🚀 OliveYoung LangChain Agent")
    print("="*50)
    
    print("실행할 모드를 선택하세요:")
    print("1. 완전한 URL 처리 (6단계 완전한 플로우) ⭐")
    print("2. 간단한 에이전트 테스트")
    print("3. ReAct 에이전트 테스트")
    print("4. 대화형 모드")
    
    try:
        choice = input("선택 (1-4): ").strip()
        
        if choice == "1":
            await quick_process()
        elif choice == "2":
            await test_simple_agent()
        elif choice == "3":
            await test_react_agent()
        elif choice == "4":
            await interactive_mode()
        else:
            print("❌ 잘못된 선택입니다.")
            return
            
    except KeyboardInterrupt:
        print("\n👋 프로그램이 중단되었습니다.")
    except Exception as e:
        logger.error(f"메인 실행 오류: {e}")
        print(f"❌ 실행 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    asyncio.run(main())