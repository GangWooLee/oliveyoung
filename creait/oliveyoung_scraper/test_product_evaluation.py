"""제품 평가 시스템 테스트"""
import asyncio
import json
from src.product_evaluator import ProductEvaluator
from src.database import init_db

async def test_product_evaluation():
    """제품 평가 시스템 전체 테스트"""
    print("🧪 제품 평가 시스템 테스트 시작")
    print("=" * 80)
    
    # 데이터베이스 초기화
    print("📊 데이터베이스 초기화 중...")
    init_db()
    
    # ProductEvaluator 초기화
    try:
        evaluator = ProductEvaluator()
        print("✅ ProductEvaluator 초기화 완료")
    except Exception as e:
        print(f"❌ ProductEvaluator 초기화 실패: {e}")
        return
    
    # 테스트할 제품 ID
    test_product_id = 8  # 맥스컷 프로 제품
    
    print(f"\n🎯 테스트 제품 ID: {test_product_id}")
    print("-" * 50)
    
    # 1단계: 가중평균 점수 계산 테스트
    print("1️⃣ 가중평균 점수 계산 테스트")
    weighted_score, calculation_details = evaluator.calculate_weighted_score(test_product_id)
    
    if weighted_score > 0:
        print(f"   ✅ 가중평균 점수: {weighted_score:.2f}/5.0")
        print(f"   📊 리뷰 분포:")
        
        for calc in calculation_details.get("calculations", []):
            rating = calc["rating"]
            count = calc["count"]
            weight = calc["weight"]
            contribution = calc["contribution"]
            print(f"      {rating}점: {count}개 × {weight} = {contribution:.1f}")
        
        print(f"   📈 총 리뷰: {calculation_details.get('total_reviews', 0)}개")
        print(f"   🧮 가중치 합: {calculation_details.get('weight_sum', 0):.1f}")
    else:
        print(f"   ❌ 가중평균 계산 실패: {calculation_details}")
        return
    
    # 2단계: 모순 탐지 테스트
    print(f"\n2️⃣ 상세정보-리뷰 모순 탐지 테스트")
    print("   ⏳ AI 모순 분석 실행 중...")
    
    try:
        contradictions, penalty_score = await evaluator.detect_contradictions(test_product_id)
        
        print(f"   ✅ 모순 탐지 완료!")
        print(f"   🔍 발견된 모순: {len(contradictions)}개")
        print(f"   📉 점수 차감: -{penalty_score:.2f}점")
        
        if contradictions:
            print(f"   📋 모순 상세:")
            for i, contradiction in enumerate(contradictions, 1):
                severity = contradiction.get("severity", "unknown")
                claim = contradiction.get("claim", "N/A")
                reality = contradiction.get("reality", "N/A")
                contradiction_type = contradiction.get("type", "기타")
                
                print(f"      {i}. [{severity.upper()}] {contradiction_type}")
                print(f"         주장: {claim}")
                print(f"         현실: {reality}")
        else:
            print("   ✅ 모순이 발견되지 않았습니다.")
    
    except Exception as e:
        print(f"   ❌ 모순 탐지 실패: {e}")
        penalty_score = 0.0
        contradictions = []
    
    # 3단계: 종합 평가 실행
    print(f"\n3️⃣ 종합 평가 실행")
    print("   ⏳ 전체 평가 프로세스 실행 중...")
    
    try:
        evaluation_result = await evaluator.evaluate_product(test_product_id)
        
        if "error" in evaluation_result:
            print(f"   ❌ 평가 실패: {evaluation_result['error']}")
            return
        
        print(f"   ✅ 종합 평가 완료!")
        
        # 결과 출력
        final_score = evaluation_result["final_score"]
        weighted_score = evaluation_result["weighted_score"]
        penalty_score = evaluation_result["penalty_score"]
        grade = evaluation_result["evaluation_summary"]["evaluation_grade"]
        
        print(f"\n📊 최종 평가 결과:")
        print(f"   🎯 가중평균 점수: {weighted_score:.1f}/100점")
        print(f"   ⚠️ 모순 차감: -{penalty_score:.1f}점")
        print(f"   🏆 최종 점수: {final_score:.1f}/100점")
        print(f"   📈 평가 등급: {grade}")
        
    except Exception as e:
        print(f"   ❌ 종합 평가 실패: {e}")
        return
    
    # 4단계: 저장된 결과 확인
    print(f"\n4️⃣ 데이터베이스 저장 결과 확인")
    evaluation_summary = evaluator.get_evaluation_summary(test_product_id)
    
    if evaluation_summary:
        print(f"   ✅ 평가 결과가 성공적으로 저장됨")
        print(f"   제품명: {evaluation_summary['product_name']}")
        print(f"   최종 점수: {evaluation_summary['final_score']:.1f}/100점")
        print(f"   등급: {evaluation_summary['grade']}")
        print(f"   모순 개수: {evaluation_summary['contradictions_count']}개")
        print(f"   평가 일시: {evaluation_summary['evaluated_at']}")
    else:
        print(f"   ❌ 저장된 평가 결과를 찾을 수 없습니다.")
    
    # 5단계: 전체 통계 확인
    print(f"\n5️⃣ 전체 평가 통계")
    stats = await evaluator.get_evaluation_stats()
    
    if "error" not in stats and "message" not in stats:
        print(f"   총 평가 제품: {stats['total_evaluated']}개")
        print(f"   평균 점수: {stats['average_score']:.1f}/100점")
        print(f"   최고 점수: {stats['highest_score']:.1f}/100점")
        print(f"   최저 점수: {stats['lowest_score']:.1f}/100점")
        
        print(f"   📊 등급 분포:")
        for grade, count in stats['grade_distribution'].items():
            print(f"      {grade}: {count}개")
        
        print(f"   🏆 상위 제품:")
        for i, product in enumerate(stats['top_products'], 1):
            print(f"      {i}. {product['name']}: {product['final_score']:.1f}점 ({product['grade']})")
    else:
        print(f"   📊 통계: {stats.get('message', stats.get('error', 'Unknown'))}")
    
    print("\n" + "=" * 80)
    print("🎉 제품 평가 시스템 테스트 완료!")

async def test_weighted_score_only():
    """가중평균 점수 계산만 테스트 (디버깅용)"""
    print("\n🔍 가중평균 점수 계산 상세 테스트")
    print("-" * 50)
    
    evaluator = ProductEvaluator()
    
    # 가중치 설정 확인
    print("⚖️ 가중치 설정:")
    for rating, weight in evaluator.rating_weights.items():
        print(f"   {rating}점: {weight}")
    
    # 테스트 계산
    weighted_score, details = evaluator.calculate_weighted_score(8)
    
    print(f"\n📊 계산 결과:")
    print(f"   가중평균: {weighted_score:.2f}/5.0")
    print(f"   총 리뷰: {details.get('total_reviews', 0)}개")
    
    # 일반 평균과 비교
    total_score = 0
    total_count = 0
    for calc in details.get("calculations", []):
        rating = calc["rating"]
        count = calc["count"]
        total_score += rating * count
        total_count += count
    
    if total_count > 0:
        simple_average = total_score / total_count
        print(f"   일반 평균: {simple_average:.2f}/5.0")
        print(f"   차이: {weighted_score - simple_average:.2f}점")

if __name__ == "__main__":
    # 전체 시스템 테스트
    asyncio.run(test_product_evaluation())
    
    # 가중평균 상세 테스트 (선택사항)
    # asyncio.run(test_weighted_score_only())