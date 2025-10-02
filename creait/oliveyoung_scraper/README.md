# 🛍️ 올리브영 제품 신뢰도 분석 시스템

**AI 기반 Instagram 광고 제품 신뢰도 검증 플랫폼**

올리브영 제품의 마케팅 주장과 실제 소비자 리뷰를 종합적으로 분석하여 제품의 실제 신뢰도를 평가하는 AI 기반 시스템입니다. Instagram 광고에서 보는 제품들이 정말 효과가 있는지 객관적으로 판단할 수 있도록 도와줍니다.

## ✨ 주요 기능

### 🚀 **완전 자동화된 6단계 분석 파이프라인**
URL 하나만 입력하면 모든 분석이 자동으로 완료됩니다:

1. **📊 제품 스크래핑**: 제품 정보, 가격, 평점, 리뷰 수집
2. **🖼️ 이미지 텍스트 추출**: AI OCR로 상세 이미지에서 성분, 효능 정보 추출
3. **📝 텍스트 통합 및 구조화**: 추출된 정보를 JSON 형태로 구조화
4. **🔍 리뷰 분류 및 장단점 분석**: AI가 리뷰를 감정별로 분류하고 장단점 추출
5. **⭐ 제품 평가 및 점수 계산**: 가중 평균 점수 및 등급 산출
6. **🎯 마케팅 주장 vs 실제 리뷰 모순 분석**: 광고 문구와 실제 리뷰 간의 모순점 탐지

### 🤖 **AI 기술 활용**
- **OpenAI GPT-4o**: 리뷰 감정 분석, 장단점 추출, 모순 탐지
- **Vision API**: 제품 상세 이미지에서 텍스트 추출
- **LangChain ReAct Agent**: 복잡한 분석 작업 자동화

### 📈 **고급 분석 기능**
- **청크 기반 처리**: 대량 리뷰(270개+) 토큰 제한 문제 해결
- **감정별 리뷰 분류**: positive_5, neutral_4_3, negative_2_1 그룹화
- **신뢰도 수준 평가**: 높음/보통/낮음 단계별 신뢰도 측정
- **모순점 탐지**: 마케팅 주장과 실제 경험 간의 차이점 분석

## 🏗️ 시스템 아키텍처

```
📁 올리브영 신뢰도 분석 시스템
├── 🚀 메인 실행부
│   ├── main.py                    # 기본 스크래핑 실행
│   └── agent_main.py              # AI 에이전트 실행
│
├── 🧠 AI 에이전트 시스템
│   ├── src/agent/
│   │   ├── agent.py               # ReAct 에이전트 및 완전 자동화 워크플로우
│   │   ├── tools.py               # 스크래핑, 이미지 추출, 요약 도구
│   │   └── prompts.py             # AI 프롬프트 템플릿
│
├── 🔍 핵심 분석 엔진
│   ├── src/scraper/
│   │   └── oliveyoung_scraper.py  # 고급 웹 스크래핑 (Playwright)
│   ├── src/image_text_extractor.py # AI 이미지 텍스트 추출
│   ├── src/review_classifier.py   # AI 리뷰 분류 및 감정 분석
│   └── src/product_evaluator.py   # AI 제품 평가 및 모순 탐지
│
├── 💾 데이터 관리
│   ├── src/database.py            # SQLite 데이터베이스 관리
│   └── creait.db                  # 분석 결과 저장소
│
└── 📊 분석 도구
    ├── db_to_dataframe_ex.py      # 데이터 시각화
    └── process_product_images.py  # 이미지 재처리
```

## 🛠️ 기술 스택

### **웹 스크래핑 & 자동화**
- **Playwright**: 동적 웹페이지 스크래핑
- **Asyncio**: 비동기 처리로 성능 최적화

### **AI & 머신러닝**
- **OpenAI GPT-4o**: 텍스트 분석, 감정 분류, 모순 탐지
- **OpenAI Vision API**: 이미지 OCR 및 텍스트 추출
- **LangChain**: AI 에이전트 프레임워크

### **데이터 처리**
- **SQLite**: 경량 데이터베이스
- **Pandas**: 데이터 분석 및 시각화
- **JSON**: 구조화된 데이터 저장

### **로깅 & 모니터링**
- **Loguru**: 상세한 로깅 시스템
- **실시간 진행상황 표시**: 6단계 처리 과정 추적

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install --with-deps chromium

# OpenAI API 키 설정
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력
```

### 2. AI 에이전트로 완전 자동 분석

```bash
# 🎯 추천: 완전 자동화된 6단계 분석
python agent_main.py
```

URL을 입력하면 6단계 분석이 자동으로 실행됩니다:
- ✅ 1단계: 제품 스크래핑
- ✅ 2단계: 이미지 텍스트 추출  
- ✅ 3단계: 텍스트 통합 및 구조화
- ✅ 4단계: 리뷰 분류 및 장단점 분석
- ✅ 5단계: 제품 평가 및 점수 계산
- ✅ 6단계: 마케팅 주장 vs 실제 리뷰 모순 분석

### 3. 기본 스크래핑만 실행

```bash
# 기본 스크래핑만 (AI 분석 제외)
python main.py
```

### 4. 분석 결과 확인

```bash
# 데이터베이스 내용을 DataFrame으로 확인
python db_to_dataframe_ex.py
```

## 📊 데이터베이스 스키마

### **products** - 제품 기본 정보
```sql
- id: 제품 고유 ID
- url: 올리브영 제품 URL
- name: 제품명
- price: 가격
- rating: 평점 (5점 만점)
- review_count: 리뷰 수
- rating_dist_*: 별점별 리뷰 분포
- detailed_summary: AI가 생성한 구조화된 제품 정보 (JSON)
- scraped_at: 수집 시각
```

### **product_images** - 제품 이미지
```sql
- id: 이미지 ID
- product_id: 제품 ID (FK)
- product_name: 제품명
- image_url: 이미지 URL
```

### **product_reviews** - 리뷰 데이터
```sql
- id: 리뷰 ID
- product_id: 제품 ID (FK)
- review_text: 리뷰 내용
- review_rating: 개별 리뷰 평점
```

### **image_texts** - AI 추출 텍스트
```sql
- id: 추출 ID
- image_id: 이미지 ID (FK)
- product_id: 제품 ID (FK)
- image_url: 원본 이미지 URL
- extracted_text: AI가 추출한 텍스트
- extracted_at: 추출 시각
```

### **review_analysis** - AI 리뷰 분석 결과
```sql
- id: 분석 ID
- product_id: 제품 ID (FK)
- sentiment_group: 감정 그룹 (positive_5, neutral_4_3, negative_2_1)
- advantages: 장점 목록 (JSON)
- disadvantages: 단점 목록 (JSON)
- analysis_summary: 분석 요약
- analyzed_at: 분석 시각
```

## 🎯 사용 예시

### 완전 자동 분석 예시
```python
from src.agent.agent import SimpleOliveYoungAgent
import asyncio

async def analyze_product():
    agent = SimpleOliveYoungAgent()
    
    # URL 입력만으로 완전한 분석 수행
    url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000225470"
    result = await agent.process_url_simple(url)
    
    print(result)  # 6단계 완전 분석 결과

asyncio.run(analyze_product())
```

### 개별 컴포넌트 사용 예시
```python
# 리뷰 감정 분석
from src.review_classifier import ReviewClassifier

classifier = ReviewClassifier()
analysis = await classifier.analyze_product_reviews(product_id=1)

# 제품 신뢰도 평가
from src.product_evaluator import ProductEvaluator

evaluator = ProductEvaluator()
evaluation = await evaluator.evaluate_product(product_id=1)
contradiction = await evaluator.analyze_claims_vs_reality(product_id=1)
```

## 🔧 고급 기능

### 🚀 **대량 리뷰 처리 최적화**
- **청크 기반 처리**: 270개+ 리뷰를 80개씩 분할하여 토큰 제한 해결
- **비동기 처리**: 동시 처리로 속도 향상
- **자동 재시도**: 네트워크 오류 시 자동 재시도

### 🧠 **AI 분석 품질 보장**
- **다층 JSON 파싱**: 파싱 실패 시 자동 복구
- **감정 분류 정확도**: GPT-4o 기반 고정밀 감정 분석
- **모순 탐지 알고리즘**: 마케팅 주장과 실제 리뷰 간 차이점 자동 탐지

### 📊 **실시간 모니터링**
- **진행상황 표시**: 6단계 처리 과정 실시간 추적
- **상세 로깅**: Loguru 기반 디버깅 정보
- **에러 핸들링**: 단계별 오류 처리 및 복구

## 📈 분석 결과 해석

### **신뢰도 등급 체계**
- **높음**: 마케팅 주장과 실제 리뷰가 일치
- **보통**: 일부 모순점 존재하나 전반적으로 신뢰 가능
- **낮음**: 마케팅 주장과 실제 경험의 상당한 차이

### **점수 체계**
- **최종 점수**: 0-100점 (가중 평균 기반)
- **가중 평균**: 리뷰 수와 신뢰도를 고려한 점수
- **등급**: A+, A, B+, B, C+, C, D 등급

## 🤝 기여하기

이 프로젝트는 소비자의 합리적 선택을 돕기 위한 프로젝트입니다.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⚠️ 주의사항

- **API 키 보안**: OpenAI API 키를 안전하게 관리하세요
- **사용량 제한**: OpenAI API 사용량과 비용을 모니터링하세요
- **윤리적 사용**: 웹 스크래핑 시 서버에 과부하를 주지 않도록 주의하세요
- **데이터 정확성**: AI 분석 결과는 참고용이며, 최종 구매 결정은 사용자 판단입니다

## 📞 문의 및 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/yourusername/oliveyoung_scraper/issues)
- **기능 제안**: Pull Request 또는 Issue로 제안해주세요

---

**🎯 "Instagram 광고에 소개된 내용이 과장되진 않았을까?"**

*AI 기술로 소비자의 합리적 선택을 돕는 제품 신뢰도 분석 플랫폼입니다.*