"""리뷰 분류 및 장단점 추출 시스템 테스트"""
import asyncio
import json
from src.review_classifier import ReviewClassifier
from src.database import init_db, get_review_analysis_results

async def test_review_classification():
    """리뷰 분류 시스템 전체 테스트"""
    print("🧪 리뷰 분류 시스템 테스트 시작")
    print("=" * 80)
    
    # 데이터베이스 초기화 (새 테이블 생성)
    print("📊 데이터베이스 초기화 중...")
    init_db()
    
    # ReviewClassifier 초기화
    try:
        classifier = ReviewClassifier()
        print("✅ ReviewClassifier 초기화 완료")
    except Exception as e:
        print(f"❌ ReviewClassifier 초기화 실패: {e}")
        return
    
    # 테스트할 제품 ID (기존 리뷰가 있는 제품)
    test_product_id = 8  # 맥스컷 프로 제품
    
    print(f"\n🎯 테스트 제품 ID: {test_product_id}")
    print("-" * 50)
    
    # 1. 리뷰 분류 테스트
    print("1️⃣ 리뷰 분류 테스트")
    classified_reviews = classifier.classify_reviews_by_rating(test_product_id)
    
    for group, reviews in classified_reviews.items():
        group_name = {
            'positive_5': '긍정 (5점)',
            'neutral_4_3': '중립 (4-3점)',
            'negative_2_1': '부정 (2-1점)'
        }.get(group, group)
        
        print(f"   📝 {group_name}: {len(reviews)}개 리뷰")
        if reviews:
            print(f"      샘플: {reviews[0][:100]}...")
    
    # 2. 전체 분석 실행
    print(f"\n2️⃣ 제품 ID {test_product_id} 전체 리뷰 분석 실행")
    print("   ⏳ 분석 중... (OpenAI API 호출)")
    
    try:
        analysis_results = await classifier.analyze_product_reviews(test_product_id)
        
        print("   ✅ 분석 완료!")
        
        # 분석 결과 요약 출력
        for group, result in analysis_results.items():
            group_name = {
                'positive_5': '긍정 (5점)',
                'neutral_4_3': '중립 (4-3점)',
                'negative_2_1': '부정 (2-1점)'
            }.get(group, group)
            
            print(f"\n   📊 {group_name} 그룹:")
            print(f"      리뷰 수: {result['review_count']}개")
            
            analysis = result['analysis']
            advantages = analysis.get('advantages', [])
            disadvantages = analysis.get('disadvantages', [])
            
            print(f"      장점: {len(advantages)}개 항목")
            print(f"      단점: {len(disadvantages)}개 항목")
            
            # 장점 미리보기
            if advantages:
                print(f"      장점 예시: {advantages[0].get('point', 'N/A')}")
            
            # 단점 미리보기
            if disadvantages:
                print(f"      단점 예시: {disadvantages[0].get('point', 'N/A')}")
    
    except Exception as e:
        print(f"   ❌ 분석 실패: {e}")
        return
    
    # 3. 저장된 결과 확인
    print(f"\n3️⃣ 데이터베이스 저장 결과 확인")
    stored_results = get_review_analysis_results(test_product_id)
    
    if stored_results:
        print(f"   ✅ {len(stored_results)}개 그룹 분석 결과가 저장됨")
        for result in stored_results:
            product_id, product_name, sentiment_group, advantages, disadvantages, review_count, analyzed_at = result
            
            group_name = {
                'positive_5': '긍정 (5점)',
                'neutral_4_3': '중립 (4-3점)',
                'negative_2_1': '부정 (2-1점)'
            }.get(sentiment_group, sentiment_group)
            
            print(f"      {group_name}: {review_count}개 리뷰 분석 완료 ({analyzed_at})")
    else:
        print("   ❌ 저장된 결과를 찾을 수 없습니다.")
    
    # 4. 제품 분석 요약 조회
    print(f"\n4️⃣ 제품 분석 요약")
    summary = classifier.get_product_analysis_summary(test_product_id)
    
    if summary:
        print(f"   제품명: {summary['product_name']}")
        print(f"   제품 ID: {summary['product_id']}")
        
        for group, info in summary['analysis_groups'].items():
            group_name = {
                'positive_5': '긍정 (5점)',
                'neutral_4_3': '중립 (4-3점)',
                'negative_2_1': '부정 (2-1점)'
            }.get(group, group)
            
            print(f"   📈 {group_name}:")
            print(f"      리뷰 수: {info['review_count']}개")
            print(f"      장점 항목: {info['advantages_count']}개")
            print(f"      단점 항목: {info['disadvantages_count']}개")
    
    # 5. 전체 시스템 통계
    print(f"\n5️⃣ 전체 시스템 통계")
    stats = await classifier.get_analysis_stats()
    
    if stats:
        print(f"   전체 제품 수: {stats['total_products']}개")
        print(f"   분석 완료 제품: {stats['analyzed_products']}개")
        print(f"   완료율: {stats['completion_rate']}")
        
        if 'group_analysis' in stats:
            for group, info in stats['group_analysis'].items():
                group_name = {
                    'positive_5': '긍정 (5점)',
                    'neutral_4_3': '중립 (4-3점)',
                    'negative_2_1': '부정 (2-1점)'
                }.get(group, group)
                
                print(f"   📊 {group_name}: {info['analyzed_products']}개 제품, {info['total_reviews']}개 리뷰")
    
    print("\n" + "=" * 80)
    print("🎉 리뷰 분류 시스템 테스트 완료!")

async def test_specific_group_analysis():
    """특정 그룹 분석만 테스트 (디버깅용)"""
    print("\n🔍 특정 그룹 분석 상세 테스트")
    print("-" * 50)
    
    classifier = ReviewClassifier()
    
    # 샘플 리뷰들 (5점 리뷰 예시)
    sample_reviews = [
        "보통 제형감이 변하면 색도 똑같이 잡기가 어려운데이건 제형도 유리아쥬 립밤 보습력은 그대로 가져오면서색깔은 롬앤 스럽게 잘 뽑아내서 너무 만족스러워요!",
        "발림성도 좋고 색깔도 예쁘네요. 립밤치고 발색도 괜찮고 보습력도 좋아서 만족합니다.",
        "가격대비 너무 좋아요! 효과도 좋고 성분도 마음에 들어서 재구매 의사 있습니다."
    ]
    
    print(f"샘플 리뷰 {len(sample_reviews)}개로 테스트")
    
    result = await classifier.extract_insights_with_evidence(sample_reviews, "positive_5")
    
    print("\n📋 분석 결과:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # 전체 시스템 테스트
    asyncio.run(test_review_classification())
    
    # 특정 그룹 분석 테스트 (선택사항)
    # asyncio.run(test_specific_group_analysis())