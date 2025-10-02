"""통합된 제품 정보 확인 스크립트"""
import asyncio
import json
from src.agent.tools import DatabaseQueryTool, ProductSummaryTool
from src.product_summarizer import ProductSummarizer

async def main():
    print("🔍 제품 상세정보 통합 결과 확인")
    print("=" * 50)
    
    # 1. 데이터베이스에서 통합된 정보 확인
    print("\n📋 1. 데이터베이스 조회:")
    query_tool = DatabaseQueryTool()
    result = query_tool._run(8, "product_info")
    print(result)
    
    # 2. 통합된 요약 정보 확인
    print("\n📄 2. 통합된 상세정보:")
    import sqlite3
    from pathlib import Path
    
    DB_FILE = Path("creait.db")
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    
    cur.execute("SELECT detailed_summary FROM products WHERE id = 8")
    result = cur.fetchone()
    
    if result and result[0]:
        try:
            data = json.loads(result[0])
            print(f"📋 제품 요약: {data.get('product_summary', 'N/A')}")
            print(f"💡 주요 효능: {data.get('benefits_claims', 'N/A')}")
            print(f"ℹ️ 추가정보: {data.get('additional_info', 'N/A')}")
        except:
            print("원본 텍스트:", result[0][:200] + "...")
    
    con.close()
    
    # 3. 이미지 텍스트 통계
    print("\n🖼️ 3. 이미지 텍스트 통계:")
    result = query_tool._run(8, "image_texts")
    print(result)
    
    print("\n✅ 통합된 정보 확인 완료!")
    print("\n📍 통합된 정보 위치:")
    print("- 데이터베이스: creait.db -> products 테이블 -> detailed_summary 컬럼")
    print("- 개별 이미지 텍스트: product_image_texts 테이블")

if __name__ == "__main__":
    asyncio.run(main())