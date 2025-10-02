# """Olive Young 제품 정보 스크래퍼 (Playwright 기반)"""
# import asyncio
# import json
# from pathlib import Path
# from typing import Optional
# from loguru import logger
# from playwright.async_api import async_playwright, Page, Browser
# from playwright_stealth import Stealth


# class ProductInfo:
#     """제품 정보 데이터 클래스"""
#     def __init__(self):
#         self.name: Optional[str] = None
#         self.price: Optional[str] = None
#         self.rating: Optional[str] = None
#         self.review_count: Optional[str] = None
#         self.detail_images: list[str] = []
#         self.review_rating_distribution: dict[int, str] = {}
#         self.reviews: list[str] = []
#         self.review_ratings: list[str] = []


# class OliveYoungScraper:
#     """Olive Young 제품 페이지 스크래퍼 (Playwright 기반)"""

#     SELECTORS = {
#         "name": "#Contents > div.prd_detail_box.renew > div.right_area > div > p.prd_name",
#         "regular_price": "#Contents > div.prd_detail_box.renew > div.right_area > div > div.price > span.price-1 > strike",
#         "discount_price": "#Contents > div.prd_detail_box.renew > div.right_area > div > div.price > span.price-2 > strong",
#         "rating": "#repReview > b",
#         "review_count": "#repReview > em",
#         "detail_toggle": "#btn_toggle_detail_image",
#         "review_button": "#reviewInfo > a",
#         "sort_by_helpfulness_button": "#gdasSort > li:nth-child(2) > a",
#     }

#     def __init__(self, headless: bool = False):
#         """
#         Args:
#             headless: 브라우저를 headless 모드로 실행할지 여부
#         """
#         self.headless = headless
#         self.browser: Optional[Browser] = None
#         self.page: Optional[Page] = None
#         self.playwright = None

#     async def __aenter__(self):
#         """Async context manager entry"""
#         self.playwright = await async_playwright().start()

#         # 실제 Chrome 브라우저 사용 (channel='chrome')
#         self.browser = await self.playwright.chromium.launch(
#             headless=self.headless,
#             channel='chrome',
#             args=[
#                 '--disable-blink-features=AutomationControlled',
#                 '--disable-dev-shm-usage',
#                 '--no-sandbox',
#                 '--disable-web-security',
#                 '--disable-features=IsolateOrigins,site-per-process',
#                 '--disable-site-isolation-trials',
#                 '--disable-features=BlockInsecurePrivateNetworkRequests'
#             ]
#         )

#         # Context 생성 (User Agent 및 Viewport 설정)
#         context = await self.browser.new_context(
#             user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
#             viewport={"width": 1920, "height": 1080},
#             locale="ko-KR",
#             timezone_id="Asia/Seoul",
#             permissions=["geolocation"],
#             geolocation={"longitude": 126.9780, "latitude": 37.5665},
#             extra_http_headers={
#                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
#                 "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
#                 "Accept-Encoding": "gzip, deflate, br",
#                 "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
#                 "Sec-Ch-Ua-Mobile": "?0",
#                 "Sec-Ch-Ua-Platform": '"macOS"',
#                 "Sec-Fetch-Dest": "document",
#                 "Sec-Fetch-Mode": "navigate",
#                 "Sec-Fetch-Site": "none",
#                 "Sec-Fetch-User": "?1",
#                 "Upgrade-Insecure-Requests": "1"
#             }
#         )

#         self.page = await context.new_page()

#         # 쿠키 로드 및 주입
#         await self._load_cookies()

#         # Stealth 모드 적용
#         stealth = Stealth()
#         await stealth.apply_stealth_async(self.page)

#         # 추가 JavaScript 우회 스크립트
#         await self.page.add_init_script("""
#             // WebDriver 속성 제거
#             Object.defineProperty(navigator, 'webdriver', {
#                 get: () => undefined
#             });

#             // Chrome 객체 추가
#             window.chrome = {
#                 runtime: {}
#             };

#             // Permissions API 우회
#             const originalQuery = window.navigator.permissions.query;
#             window.navigator.permissions.query = (parameters) => (
#                 parameters.name === 'notifications' ?
#                     Promise.resolve({ state: Notification.permission }) :
#                     originalQuery(parameters)
#             );

#             // Plugin 배열 설정
#             Object.defineProperty(navigator, 'plugins', {
#                 get: () => [1, 2, 3, 4, 5]
#             });
#             // Languages 설정
#             Object.defineProperty(navigator, 'languages', {
#                 get: () => ['ko-KR', 'ko', 'en-US', 'en']
#             });
#         """)

#         return self

#     async def __aexit__(self, exc_type, exc_val, exc_tb):
#         """Async context manager exit"""
#         if self.page:
#             await self.page.close()
#         if self.browser:
#             await self.browser.close()
#         if self.playwright:
#             await self.playwright.stop()

#     async def scrape(self, url: str, max_reviews: int = 30) -> ProductInfo:
#         """
#         제품 페이지에서 정보를 스크래핑합니다.

#         Args:
#             url: Olive Young 제품 페이지 URL
#             max_reviews: 최대 스크래핑할 리뷰 개수

#         Returns:
#             ProductInfo: 스크래핑된 제품 정보
#         """
#         if not self.page:
#             raise RuntimeError("Scraper must be used as async context manager")

#         logger.info(f"Scraping URL: {url}")

#         # 페이지 로딩
#         await self.page.goto(url, wait_until="load", timeout=60000)
#         logger.info("페이지 로딩 완료")

#         # 안정화 대기
#         await self.page.wait_for_timeout(3000)

#         # 마우스 움직임 시뮬레이션 (봇 탐지 우회)
#         await self.page.mouse.move(100, 100)
#         await self.page.wait_for_timeout(500)
#         await self.page.mouse.move(300, 300)
#         await self.page.wait_for_timeout(500)

#         # 스크롤 시뮬레이션
#         await self.page.evaluate("window.scrollTo(0, 200)")
#         await self.page.wait_for_timeout(1000)
#         await self.page.evaluate("window.scrollTo(0, 0)")
#         await self.page.wait_for_timeout(1000)

#         product = ProductInfo()

#         # 제품명
#         try:
#             await self.page.wait_for_timeout(1000)  # 추가 대기
#             product.name = await self._get_text(self.SELECTORS["name"])
#             logger.info(f"제품명: {product.name}")
#         except Exception as e:
#             logger.warning(f"제품명 가져오기 실패: {e}")

#         # 가격
#         try:
#             product.price = await self._get_price()
#             logger.info(f"가격: {product.price}")
#         except Exception as e:
#             logger.warning(f"가격 가져오기 실패: {e}")

#         # 리뷰 평점
#         try:
#             product.rating = await self._get_text(self.SELECTORS["rating"])
#             logger.info(f"평점: {product.rating}")
#         except Exception as e:
#             logger.warning(f"평점 가져오기 실패: {e}")

#         # 리뷰 개수
#         try:
#             product.review_count = await self._get_text(self.SELECTORS["review_count"])
#             logger.info(f"리뷰 개수: {product.review_count}")
#         except Exception as e:
#             logger.warning(f"리뷰 개수 가져오기 실패: {e}")

#         # 제품 상세정보 이미지
#         try:
#             product.detail_images = await self._get_detail_images()
#             logger.info(f"상세 이미지 개수: {len(product.detail_images)}")
#         except Exception as e:
#             logger.warning(f"상세 이미지 가져오기 실패: {e}")

#         # 리뷰 탭 클릭, 평점 분포 가져오기, 정렬 및 추출
#         try:
#             await self._click_review_tab()
#             product.review_rating_distribution = await self._get_review_rating_distribution()
#             await self._sort_reviews_by_helpfulness()

#             # 페이지네이션하며 모든 리뷰 추출
#             product.reviews, product.review_ratings = await self._paginate_and_extract_reviews(max_reviews=max_reviews)
#             logger.info(f"총 {len(product.reviews)}개의 리뷰 추출 완료")

#         except Exception as e:
#             logger.warning(f"리뷰 정보 가져오기, 정렬 및 추출 실패: {e}")

#         return product

#     async def _paginate_and_extract_reviews(self, max_reviews: int) -> tuple[list[str], list[str]]:
#         """모든 리뷰 페이지를 돌며 최대 max_reviews개까지 리뷰를 추출합니다."""
#         all_reviews = []
#         all_ratings = []
#         while len(all_reviews) < max_reviews:
#             # 현재 페이지 리뷰 추출
#             reviews_on_page, ratings_on_page = await self._extract_reviews_from_page()
#             if not reviews_on_page:
#                 logger.info("현재 페이지에 리뷰가 없어 페이지네이션을 중단합니다.")
#                 break
            
#             for review, rating in zip(reviews_on_page, ratings_on_page):
#                 if len(all_reviews) < max_reviews:
#                     all_reviews.append(review)
#                     all_ratings.append(rating)
#                 else:
#                     break
            
#             if len(all_reviews) >= max_reviews:
#                 logger.info(f"최대 리뷰 개수({max_reviews})에 도달했습니다.")
#                 break

#             # 다음 페이지로 이동
#             try:
#                 paging_container = "#gdasContentsArea > div > div.pageing"
#                 # 현재 활성화된 페이지(<strong>)를 찾음
#                 current_page_element = await self.page.query_selector(f"{paging_container} > strong")
#                 if not current_page_element:
#                     logger.info("활성화된 페이지 번호를 찾을 수 없어 중단합니다.")
#                     break
                
#                 current_page_num = int((await current_page_element.text_content()).strip())

#                 # 다음 버튼 찾기
#                 next_button = None
#                 # 현재 페이지가 10, 20, ... 이면 '다음' 버튼 클릭
#                 if current_page_num % 10 == 0:
#                     next_button = await self.page.query_selector(f"{paging_container} > a.next")
#                 # 그렇지 않으면 바로 다음 번호(<strong> 바로 다음 <a>) 클릭
#                 else:
#                     next_button = await self.page.query_selector(f"{paging_container} > strong + a")

#                 if not next_button:
#                     logger.info("마지막 페이지입니다. 리뷰 추출을 종료합니다.")
#                     break

#                 button_text = (await next_button.text_content()).strip()
#                 logger.info(f"다음 페이지로 이동합니다: '{button_text}'")
#                 await next_button.click()
#                 # TODO: 페이지 로딩을 더 안정적으로 기다리는 방법으로 개선 필요
#                 await self.page.wait_for_timeout(2000)

#             except Exception as e:
#                 logger.warning(f"페이지 이동 중 오류 발생: {e}. 페이지네이션을 중단합니다.")
#                 break
        
#         return all_reviews, all_ratings

#     async def _extract_reviews_from_page(self) -> tuple[list[str], list[str]]:
#         """현재 페이지의 리뷰 텍스트와 별점을 추출합니다."""
#         reviews_on_page = []
#         ratings_on_page = []
#         logger.info("현재 페이지의 리뷰 추출 시작")
#         try:
#             review_list_selector = "#gdasList"
#             await self.page.wait_for_selector(review_list_selector, timeout=5000)

#             review_elements = await self.page.query_selector_all(f"{review_list_selector} > li")
#             logger.info(f"현재 페이지에서 {len(review_elements)}개의 리뷰 항목을 찾았습니다.")

#             for i in range(1, len(review_elements) + 1):
#                 review_text_selector = f"#gdasList > li:nth-child({i}) > div.review_cont > div.txt_inner"
#                 review_rating_selector = f"#gdasList > li:nth-child({i}) > div.review_cont > div.score_area > span.review_point > span"
                
#                 try:
#                     # 리뷰 텍스트 추출
#                     text = await self._get_text(review_text_selector, timeout=1000)
#                     # 리뷰 별점 추출
#                     rating_text = await self._get_text(review_rating_selector, timeout=1000)
#                     rating = self._parse_rating_from_text(rating_text)
                    
#                     reviews_on_page.append(text)
#                     ratings_on_page.append(rating)
#                     logger.debug(f"{i}번째 리뷰 추출 성공. 별점: {rating}")
#                 except Exception:
#                     # txt_inner가 없는 경우 (e.g. 포토리뷰)는 텍스트가 없으므로 건너뜀
#                     logger.warning(f"{i}번째 리뷰에서 텍스트(.txt_inner) 또는 별점을 찾지 못했습니다. 포토리뷰일 수 있습니다.")
        
#         except Exception as e:
#             logger.error(f"리뷰 목록 추출 중 오류 발생: {e}")

#         logger.info(f"현재 페이지에서 {len(reviews_on_page)}개의 리뷰 텍스트를 추출했습니다.")
#         return reviews_on_page, ratings_on_page

#     async def _sort_reviews_by_helpfulness(self):
#         """리뷰를 '도움순'으로 정렬합니다."""
#         logger.info("리뷰를 '도움순'으로 정렬합니다.")
#         try:
#             sort_button = await self.page.wait_for_selector(
#                 self.SELECTORS["sort_by_helpfulness_button"],
#                 timeout=5000
#             )
#             await sort_button.click()
#             logger.info("'도움순' 정렬 버튼 클릭 성공")
#             # 정렬 후 리뷰 목록이 새로고침될 때까지 대기
#             # TODO: 더 안정적인 대기 방법 (e.g., network idle or a specific element change)
#             await self.page.wait_for_timeout(2000)
#         except Exception as e:
#             logger.warning(f"'도움순'으로 정렬하는 데 실패했습니다: {e}")
#             await self.page.screenshot(path="debug_screenshot_sort_fail.png")
#             logger.info("디버깅 스크린샷 저장: debug_screenshot_sort_fail.png")

#     async def _get_review_rating_distribution(self) -> dict[int, str]:
#         """각 별점별 리뷰 분포(%)를 가져옵니다."""
#         distribution = {}
#         logger.info("리뷰 평점별 분포 가져오기 시작")
#         try:
#             graph_area_selector = "#gdasContentsArea > div > div.product_rating_area.review-write-delete > div > div.graph_area"
#             await self.page.wait_for_selector(graph_area_selector, timeout=5000)

#             for i in range(1, 6):  # li:nth-child(1) to li:nth-child(5)
#                 rating = 6 - i  # 5 stars to 1 star
#                 selector = f"{graph_area_selector} > ul > li:nth-child({i}) > span.per"
#                 percentage_text = await self._get_text(selector, timeout=1000)
#                 if percentage_text:
#                     distribution[rating] = percentage_text
#                     logger.info(f"{rating}점 리뷰 비율: {percentage_text}")
#                 else:
#                     logger.warning(f"{rating}점 리뷰 비율을 찾을 수 없습니다.")

#         except Exception as e:
#             logger.warning(f"리뷰 평점별 분포를 가져오는 데 실패했습니다: {e}")
#         return distribution

#     async def _click_review_tab(self):
#         """리뷰 탭을 클릭하여 리뷰 정보를 로드합니다."""
#         try:
#             review_button = await self.page.wait_for_selector(
#                 self.SELECTORS["review_button"],
#                 timeout=10000
#             )
#             await review_button.click()
#             logger.info("리뷰 탭 클릭 성공")
#             # 리뷰가 로드될 때까지 잠시 대기합니다.
#             # TODO: 리뷰 컨테이너가 나타날 때까지 기다리는 더 안정적인 방법으로 변경해야 합니다.
#             await self.page.wait_for_timeout(2000)
#             logger.info("리뷰 정보 로딩 대기 완료")
#         except Exception as e:
#             logger.warning(f"리뷰 탭 클릭 실패: {e}")
#             await self.page.screenshot(path="debug_screenshot_review_click_fail.png")
#             logger.info("디버깅 스크린샷 저장: debug_screenshot_review_click_fail.png")

#     async def _get_price(self) -> str:
#         """가격을 추출합니다. 할인가가 있으면 할인가를, 없으면 정가를 반환합니다."""
#         try:
#             # 먼저 할인가 시도
#             try:
#                 discount_price = await self._get_text(self.SELECTORS["discount_price"], timeout=2000)
#                 if discount_price:
#                     logger.info(f"할인가 발견: {discount_price}")
#                     return discount_price
#             except Exception:
#                 logger.debug("할인가를 찾을 수 없습니다.")
            
#             # 할인가가 없으면 정가 시도
#             try:
#                 regular_price = await self._get_text(self.SELECTORS["regular_price"], timeout=2000)
#                 if regular_price:
#                     logger.info(f"정가 발견: {regular_price}")
#                     return regular_price
#             except Exception:
#                 logger.debug("정가를 찾을 수 없습니다.")
            
#             logger.warning("정가와 할인가 모두 찾을 수 없습니다.")
#             return ""
            
#         except Exception as e:
#             logger.warning(f"가격 추출 중 오류 발생: {e}")
#             return ""

#     def _parse_rating_from_text(self, rating_text: str) -> str:
#         """'5점만점에 x점' 형식의 텍스트에서 별점만 추출합니다."""
#         try:
#             if "점만점에" in rating_text and "점" in rating_text:
#                 # '5점만점에 4점' -> '4' 추출
#                 parts = rating_text.split("점만점에")
#                 if len(parts) > 1:
#                     score_part = parts[1].replace("점", "").strip()
#                     return score_part
#             return ""
#         except Exception as e:
#             logger.warning(f"별점 파싱 실패: {rating_text}, 에러: {e}")
#             return ""

#     async def _get_text(self, selector: str, timeout: int = 10000) -> str:
#         """CSS selector로 요소의 텍스트를 가져옵니다."""
#         element = await self.page.wait_for_selector(selector, state='attached', timeout=timeout)
#         text = await element.text_content()
#         return text.strip() if text else ""

#     async def _get_detail_images(self) -> list[str]:
#         """제품 상세 이미지들을 가져옵니다."""
#         # 페이지를 아래로 스크롤하여 상세정보 영역 로딩
#         await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
#         await self.page.wait_for_timeout(2000)

#         # 상세정보 토글 버튼 클릭
#         try:
#             toggle_btn = await self.page.wait_for_selector(
#                 self.SELECTORS["detail_toggle"],
#                 timeout=10000
#             )
#             await toggle_btn.click()
#             logger.info("상세정보 토글 버튼 클릭 성공")
#             await self.page.wait_for_timeout(3000)  # 이미지 로딩 대기
#         except Exception as e:
#             logger.warning(f"상세정보 토글 버튼 클릭 실패: {e}")
#             await self.page.screenshot(path="debug_screenshot.png")
#             logger.info("디버깅 스크린샷 저장: debug_screenshot.png")
#             return []

#         # 모든 이미지 URL 수집 - 다중 셀렉터 패턴 사용
#         images = []
#         logger.info("상세 이미지 수집 시작")
        
#         # 다양한 제품 페이지 구조에 대응하기 위한 셀렉터 패턴들
#         selector_patterns = [
#             # 최신 구체적 패턴 (최우선)
#             {"container": "#tempHtml2 > center", "selector": "#tempHtml2 > center > div:nth-child(1) > img:nth-child(1)"},
#             {"container": "#tempHtml2 > center", "selector": "#tempHtml2 > center > div img"},
#             {"container": "#tempHtml2 > center", "selector": "#tempHtml2 > center img"},
#             # 기본 패턴
#             {"container": "#tempHtml2", "selector": "#tempHtml2 > div"},
#             {"container": "#tempHtml2", "selector": "#tempHtml2 img"},
#             # 대체 패턴들
#             {"container": "#tempHtml", "selector": "#tempHtml > div"},
#             {"container": "#tempHtml", "selector": "#tempHtml img"},
#             {"container": ".detail_info_wrap", "selector": ".detail_info_wrap img"},
#             {"container": ".prd_detail_info", "selector": ".prd_detail_info img"},
#             {"container": ".goods_detail_wrap", "selector": ".goods_detail_wrap img"},
#         ]
        
#         for pattern in selector_patterns:
#             try:
#                 container_selector = pattern["container"]
#                 img_selector = pattern["selector"]
                
#                 # 컨테이너가 지정된 경우 존재 여부 확인
#                 if container_selector:
#                     containers = await self.page.query_selector_all(container_selector)
#                     if not containers:
#                         logger.debug(f"컨테이너 '{container_selector}' 없음, 다음 패턴 시도")
#                         continue
                
#                 # div 컨테이너 기반 패턴
#                 if " > div" in img_selector:
#                     div_containers = await self.page.query_selector_all(img_selector)
#                     logger.debug(f"패턴 '{img_selector}': {len(div_containers)}개 div 컨테이너 발견")
                    
#                     for i, div_container in enumerate(div_containers, 1):
#                         imgs_in_div = await div_container.query_selector_all("img")
#                         logger.debug(f"Div 컨테이너 #{i}에서 {len(imgs_in_div)}개의 img 태그 발견")

#                         for img in imgs_in_div:
#                             src = await self._extract_image_src(img)
#                             if src and src not in images:
#                                 images.append(src)
#                                 logger.debug(f"이미지 추가: {src}")
                
#                 # 직접 이미지 셀렉터 패턴
#                 else:
#                     img_elements = await self.page.query_selector_all(img_selector)
#                     logger.debug(f"패턴 '{img_selector}': {len(img_elements)}개 이미지 발견")
                    
#                     for img in img_elements:
#                         src = await self._extract_image_src(img)
#                         if src and src not in images:
#                             images.append(src)
#                             logger.debug(f"이미지 추가: {src}")
                
#                 # 이미지를 찾았다면 추가 패턴 시도 중단
#                 if images:
#                     logger.info(f"패턴 '{img_selector}'에서 {len(images)}개 이미지 발견")
#                     break
                    
#             except Exception as e:
#                 logger.debug(f"패턴 '{pattern['selector']}' 처리 중 오류: {e}")
#                 continue

#         if images:
#             logger.info(f"총 {len(images)}개의 상세 이미지 URL 수집 완료")
#         else:
#             logger.warning("모든 셀렉터 패턴에서 상세 이미지를 찾을 수 없습니다")
#             # 디버깅을 위해 스크린샷과 HTML 저장
#             await self.page.screenshot(path="debug_screenshot_detail_img.png")
#             html_content = await self.page.content()
#             with open("debug_page_source_detail_img.html", "w", encoding="utf-8") as f:
#                 f.write(html_content)
#             logger.info("상세 이미지 디버깅 파일 저장 완료")

#         return images

#     async def _extract_image_src(self, img_element) -> Optional[str]:
#         """이미지 요소에서 src 속성을 추출합니다."""
#         try:
#             # 다양한 src 속성 시도
#             src = await img_element.get_attribute("src")
#             if not src or "http" not in src:
#                 src = await img_element.get_attribute("data-src")
#             if not src or "http" not in src:
#                 src = await img_element.get_attribute("data-original")
#             if not src or "http" not in src:
#                 src = await img_element.get_attribute("data-lazy")

#             return src if src and "http" in src else None
#         except Exception as e:
#             logger.debug(f"이미지 src 추출 실패: {e}")
#             return None

#     async def _load_cookies(self):
#         """cookies.json 파일에서 쿠키를 로드하여 페이지에 주입합니다."""
#         try:
#             cookie_file = Path("cookies.json")
#             if not cookie_file.exists():
#                 logger.warning("cookies.json 파일이 없습니다. 쿠키 없이 진행합니다.")
#                 return

#             with open(cookie_file, 'r', encoding='utf-8') as f:
#                 cookies_data = json.load(f)

#             # EditThisCookie 형식의 중첩 배열 처리
#             if isinstance(cookies_data, list) and len(cookies_data) > 0:
#                 if isinstance(cookies_data[0], list):
#                     cookies_data = cookies_data[0]

#             # Playwright 형식으로 변환하여 추가
#             playwright_cookies = []
#             for cookie in cookies_data:
#                 playwright_cookie = {
#                     'name': cookie['name'],
#                     'value': cookie['value'],
#                     'domain': cookie['domain'],
#                     'path': cookie.get('path', '/'),
#                 }

#                 # 선택적 필드 추가
#                 if 'expirationDate' in cookie:
#                     playwright_cookie['expires'] = cookie['expirationDate']
#                 if 'httpOnly' in cookie:
#                     playwright_cookie['httpOnly'] = cookie['httpOnly']
#                 if 'secure' in cookie:
#                     playwright_cookie['secure'] = cookie['secure']
#                 if 'sameSite' in cookie and cookie['sameSite'] != 'unspecified':
#                     # sameSite 값 변환
#                     same_site_map = {
#                         'no_restriction': 'None',
#                         'lax': 'Lax',
#                         'strict': 'Strict'
#                     }
#                     playwright_cookie['sameSite'] = same_site_map.get(cookie['sameSite'], 'Lax')

#                 playwright_cookies.append(playwright_cookie)

#             # 쿠키 추가
#             await self.page.context.add_cookies(playwright_cookies)
#             logger.info(f"✅ {len(playwright_cookies)}개의 쿠키를 성공적으로 로드했습니다.")

#             # 중요한 쿠키 확인
#             important_cookies = ['__cf_bm', '_cfuvid', 'cf_clearance']
#             loaded_important = [c['name'] for c in playwright_cookies if c['name'] in important_cookies]
#             if loaded_important:
#                 logger.info(f"🔑 Cloudflare 쿠키 로드됨: {', '.join(loaded_important)}")

#         except Exception as e:
#             logger.warning(f"쿠키 로드 실패: {e}. 쿠키 없이 진행합니다.")

"""Olive Young 제품 정보 스크래퍼 (Playwright 기반)"""
import asyncio
import json
import random
from pathlib import Path
from typing import Optional
from loguru import logger
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import Stealth


class ProductInfo:
    """제품 정보 데이터 클래스"""
    def __init__(self):
        self.name: Optional[str] = None
        self.price: Optional[str] = None
        self.rating: Optional[str] = None
        self.review_count: Optional[str] = None
        self.detail_images: list[str] = []
        self.review_rating_distribution: dict[int, str] = {}
        self.reviews: list[str] = []
        self.review_ratings: list[str] = []


class OliveYoungScraper:
    """Olive Young 제품 페이지 스크래퍼 (Playwright 기반)"""

    # 다양한 User Agent 목록 (최신 Chrome, Firefox, Safari)
    USER_AGENTS = [
        # Chrome (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        
        # Chrome (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        
        # Firefox (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        
        # Firefox (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
        
        # Safari (macOS)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6.1 Safari/605.1.15",
        
        # Edge (Windows)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    ]

    SELECTORS = {
        "name": "#Contents > div.prd_detail_box.renew > div.right_area > div > p.prd_name",
        "regular_price": "#Contents > div.prd_detail_box.renew > div.right_area > div > div.price > span.price-1 > strike",
        "discount_price": "#Contents > div.prd_detail_box.renew > div.right_area > div > div.price > span.price-2 > strong",
        "rating": "#repReview > b",
        "review_count": "#repReview > em",
        "detail_toggle": "#btn_toggle_detail_image",
        "review_button": "#reviewInfo > a",
        "sort_by_helpfulness_button": "#gdasSort > li:nth-child(2) > a",
    }

    def __init__(self, headless: bool = True, use_random_user_agent: bool = True):
        """
        Args:
            headless: 브라우저를 headless 모드로 실행할지 여부 (기본값: True)
            use_random_user_agent: 랜덤 User Agent 사용 여부
        """
        self.headless = headless
        self.use_random_user_agent = use_random_user_agent
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.selected_user_agent = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.playwright = await async_playwright().start()

        # User Agent 선택
        if self.use_random_user_agent:
            self.selected_user_agent = random.choice(self.USER_AGENTS)
            logger.info(f"🎭 선택된 User Agent: {self.selected_user_agent}")
        else:
            self.selected_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

        # 실제 Chrome 브라우저 사용 (channel='chrome')
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            channel='chrome',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # 이미지 로딩 비활성화로 속도 향상
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-default-apps',
                '--disable-popup-blocking',
                '--disable-translate',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-client-side-phishing-detection',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-report-upload',
                '--disable-ipc-flooding-protection'
            ]
        )

        # User Agent에 따른 헤더 동적 생성
        headers = self._generate_headers_for_user_agent(self.selected_user_agent)

        # Context 생성 (User Agent 및 Viewport 설정)
        context = await self.browser.new_context(
            user_agent=self.selected_user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            permissions=["geolocation"],
            geolocation={"longitude": 126.9780, "latitude": 37.5665},
            extra_http_headers=headers
        )

        self.page = await context.new_page()

        # 쿠키 로드 및 주입
        await self._load_cookies()

        # Stealth 모드 적용
        stealth = Stealth()
        await stealth.apply_stealth_async(self.page)

        # 추가 JavaScript 우회 스크립트
        await self.page.add_init_script("""
            // WebDriver 속성 완전 제거
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 자동화 관련 속성들 제거
            delete navigator.__proto__.webdriver;
            delete window.navigator.webdriver;
            
            // Chrome 객체 추가
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Permissions API 우회
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Plugin 배열 설정 (실제 브라우저처럼)
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return {
                        0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        2: { name: 'Native Client', filename: 'internal-nacl-plugin' },
                        length: 3
                    };
                }
            });

            // Languages 설정
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });
            
            // Connection 정보 설정
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10
                })
            });
            
            // Hardware concurrency 설정
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // Device memory 설정
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // Screen 정보 설정
            Object.defineProperty(screen, 'availHeight', {
                get: () => 1040
            });
            Object.defineProperty(screen, 'availWidth', {
                get: () => 1920
            });
            
            // Timezone 설정
            Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                value: function() {
                    return { timeZone: 'Asia/Seoul' };
                }
            });
            
            // Canvas fingerprinting 방지
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                if (type === '2d') {
                    const context = getContext.call(this, type);
                    const originalFillText = context.fillText;
                    context.fillText = function(text, x, y, maxWidth) {
                        return originalFillText.call(this, text + ' ', x, y, maxWidth);
                    };
                    return context;
                }
                return getContext.call(this, type);
            };
            
            // WebGL fingerprinting 방지
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel(R) Iris(TM) Graphics 6100';
                }
                return getParameter.call(this, parameter);
            };
        """)

        return self

    def _generate_headers_for_user_agent(self, user_agent: str) -> dict:
        """User Agent에 맞는 HTTP 헤더를 생성합니다."""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        # User Agent에 따른 브라우저별 헤더 설정
        if "Chrome" in user_agent and "Edg" not in user_agent:
            # Chrome
            chrome_version = self._extract_chrome_version(user_agent)
            headers.update({
                "Sec-Ch-Ua": f'"Chromium";v="{chrome_version}", "Not_A Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"' if "Windows" in user_agent else '"macOS"',
            })
        elif "Firefox" in user_agent:
            # Firefox
            headers.update({
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            # Safari
            headers.update({
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })
        elif "Edg" in user_agent:
            # Edge
            edge_version = self._extract_edge_version(user_agent)
            headers.update({
                "Sec-Ch-Ua": f'"Chromium";v="{edge_version}", "Not_A Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            })

        return headers

    def _extract_chrome_version(self, user_agent: str) -> str:
        """Chrome User Agent에서 버전을 추출합니다."""
        try:
            if "Chrome/" in user_agent:
                version = user_agent.split("Chrome/")[1].split(".")[0]
                return version
            return "131"
        except:
            return "131"

    def _extract_edge_version(self, user_agent: str) -> str:
        """Edge User Agent에서 버전을 추출합니다."""
        try:
            if "Edg/" in user_agent:
                version = user_agent.split("Edg/")[1].split(".")[0]
                return version
            return "131"
        except:
            return "131"

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape(self, url: str, max_reviews: int = 30) -> ProductInfo:
        """
        제품 페이지에서 정보를 스크래핑합니다.

        Args:
            url: Olive Young 제품 페이지 URL
            max_reviews: 최대 스크래핑할 리뷰 개수

        Returns:
            ProductInfo: 스크래핑된 제품 정보
        """
        if not self.page:
            raise RuntimeError("Scraper must be used as async context manager")

        logger.info(f"Scraping URL: {url}")

        # 페이지 로딩 (load까지만 대기)
        await self.page.goto(url, wait_until="load", timeout=60000)
        logger.info("페이지 초기 로딩 완료, Cloudflare 체크 대기 중...")

        # Cloudflare 체크 완료 대기 (최대 30초)
        try:
            # Cloudflare 로딩 화면이 사라질 때까지 대기
            await self.page.wait_for_function(
                """() => {
                    const bodyText = document.body.innerText;
                    // Cloudflare 체크 화면이 아닌지 확인
                    return !bodyText.includes('잠시만 기다려 주세요') &&
                           !bodyText.includes('확인 중') &&
                           !bodyText.includes('Checking your browser');
                }""",
                timeout=30000
            )
            logger.info("✅ Cloudflare 체크 통과!")
        except Exception as e:
            logger.warning(f"Cloudflare 체크 대기 중 타임아웃 (계속 진행): {e}")

        # 추가 안정화 대기
        await self.page.wait_for_timeout(3000)

        # 인간적인 행동 패턴 시뮬레이션
        await self._simulate_human_behavior()

        product = ProductInfo()

        # 제품명
        try:
            await self.page.wait_for_timeout(1000)  # 추가 대기
            product.name = await self._get_text(self.SELECTORS["name"])
            logger.info(f"제품명: {product.name}")
        except Exception as e:
            logger.warning(f"제품명 가져오기 실패: {e}")

        # 가격
        try:
            product.price = await self._get_price()
            logger.info(f"가격: {product.price}")
        except Exception as e:
            logger.warning(f"가격 가져오기 실패: {e}")

        # 리뷰 평점
        try:
            product.rating = await self._get_text(self.SELECTORS["rating"])
            logger.info(f"평점: {product.rating}")
        except Exception as e:
            logger.warning(f"평점 가져오기 실패: {e}")

        # 리뷰 개수
        try:
            product.review_count = await self._get_text(self.SELECTORS["review_count"])
            logger.info(f"리뷰 개수: {product.review_count}")
        except Exception as e:
            logger.warning(f"리뷰 개수 가져오기 실패: {e}")

        # 제품 상세정보 이미지
        try:
            product.detail_images = await self._get_detail_images()
            logger.info(f"상세 이미지 개수: {len(product.detail_images)}")
        except Exception as e:
            logger.warning(f"상세 이미지 가져오기 실패: {e}")

        # 리뷰 탭 클릭, 평점 분포 가져오기, 정렬 및 추출
        try:
            await self._click_review_tab()
            product.review_rating_distribution = await self._get_review_rating_distribution()
            await self._sort_reviews_by_helpfulness()

            # 페이지네이션하며 모든 리뷰 추출
            product.reviews, product.review_ratings = await self._paginate_and_extract_reviews(max_reviews=max_reviews)
            logger.info(f"총 {len(product.reviews)}개의 리뷰 추출 완료")

        except Exception as e:
            logger.warning(f"리뷰 정보 가져오기, 정렬 및 추출 실패: {e}")

        return product

    async def _paginate_and_extract_reviews(self, max_reviews: int) -> tuple[list[str], list[str]]:
        """모든 리뷰 페이지를 돌며 최대 max_reviews개까지 리뷰를 추출합니다."""
        all_reviews = []
        all_ratings = []
        while len(all_reviews) < max_reviews:
            # 현재 페이지 리뷰 추출
            reviews_on_page, ratings_on_page = await self._extract_reviews_from_page()
            if not reviews_on_page:
                logger.info("현재 페이지에 리뷰가 없어 페이지네이션을 중단합니다.")
                break
            
            for review, rating in zip(reviews_on_page, ratings_on_page):
                if len(all_reviews) < max_reviews:
                    all_reviews.append(review)
                    all_ratings.append(rating)
                else:
                    break
            
            if len(all_reviews) >= max_reviews:
                logger.info(f"최대 리뷰 개수({max_reviews})에 도달했습니다.")
                break

            # 다음 페이지로 이동
            try:
                paging_container = "#gdasContentsArea > div > div.pageing"
                # 현재 활성화된 페이지(<strong>)를 찾음
                current_page_element = await self.page.query_selector(f"{paging_container} > strong")
                if not current_page_element:
                    logger.info("활성화된 페이지 번호를 찾을 수 없어 중단합니다.")
                    break
                
                current_page_num = int((await current_page_element.text_content()).strip())

                # 다음 버튼 찾기
                next_button = None
                # 현재 페이지가 10, 20, ... 이면 '다음' 버튼 클릭
                if current_page_num % 10 == 0:
                    next_button = await self.page.query_selector(f"{paging_container} > a.next")
                # 그렇지 않으면 바로 다음 번호(<strong> 바로 다음 <a>) 클릭
                else:
                    next_button = await self.page.query_selector(f"{paging_container} > strong + a")

                if not next_button:
                    logger.info("마지막 페이지입니다. 리뷰 추출을 종료합니다.")
                    break

                button_text = (await next_button.text_content()).strip()
                logger.info(f"다음 페이지로 이동합니다: '{button_text}'")
                await next_button.click()
                # TODO: 페이지 로딩을 더 안정적으로 기다리는 방법으로 개선 필요
                await self.page.wait_for_timeout(2000)

            except Exception as e:
                logger.warning(f"페이지 이동 중 오류 발생: {e}. 페이지네이션을 중단합니다.")
                break
        
        return all_reviews, all_ratings

    async def _simulate_human_behavior(self):
        """인간적인 행동 패턴을 시뮬레이션합니다."""
        logger.info("🤖 인간적인 행동 패턴 시뮬레이션 시작")
        
        # 랜덤한 대기 시간 (1-3초)
        await self.page.wait_for_timeout(random.randint(1000, 3000))
        
        # 마우스 움직임 시뮬레이션 (자연스러운 패턴)
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await self.page.mouse.move(x, y)
            await self.page.wait_for_timeout(random.randint(200, 800))
        
        # 자연스러운 스크롤 패턴
        scroll_steps = random.randint(3, 6)
        for i in range(scroll_steps):
            scroll_y = random.randint(100, 500)
            await self.page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await self.page.wait_for_timeout(random.randint(300, 1000))
        
        # 페이지 상단으로 돌아가기
        await self.page.evaluate("window.scrollTo(0, 0)")
        await self.page.wait_for_timeout(random.randint(500, 1500))
        
        # 랜덤한 클릭 시뮬레이션 (빈 공간)
        try:
            x = random.randint(50, 200)
            y = random.randint(50, 200)
            await self.page.mouse.click(x, y)
            await self.page.wait_for_timeout(random.randint(200, 500))
        except:
            pass  # 클릭 실패해도 계속 진행
        
        logger.info("✅ 인간적인 행동 패턴 시뮬레이션 완료")

    async def _extract_reviews_from_page(self) -> tuple[list[str], list[str]]:
        """현재 페이지의 리뷰 텍스트와 별점을 추출합니다."""
        reviews_on_page = []
        ratings_on_page = []
        logger.info("현재 페이지의 리뷰 추출 시작")
        try:
            review_list_selector = "#gdasList"
            await self.page.wait_for_selector(review_list_selector, timeout=5000)

            review_elements = await self.page.query_selector_all(f"{review_list_selector} > li")
            logger.info(f"현재 페이지에서 {len(review_elements)}개의 리뷰 항목을 찾았습니다.")

            for i in range(1, len(review_elements) + 1):
                review_text_selector = f"#gdasList > li:nth-child({i}) > div.review_cont > div.txt_inner"
                review_rating_selector = f"#gdasList > li:nth-child({i}) > div.review_cont > div.score_area > span.review_point > span"
                
                try:
                    # 리뷰 텍스트 추출
                    text = await self._get_text(review_text_selector, timeout=1000)
                    # 리뷰 별점 추출
                    rating_text = await self._get_text(review_rating_selector, timeout=1000)
                    rating = self._parse_rating_from_text(rating_text)
                    
                    reviews_on_page.append(text)
                    ratings_on_page.append(rating)
                    logger.debug(f"{i}번째 리뷰 추출 성공. 별점: {rating}")
                except Exception:
                    # txt_inner가 없는 경우 (e.g. 포토리뷰)는 텍스트가 없으므로 건너뜀
                    logger.warning(f"{i}번째 리뷰에서 텍스트(.txt_inner) 또는 별점을 찾지 못했습니다. 포토리뷰일 수 있습니다.")
        
        except Exception as e:
            logger.error(f"리뷰 목록 추출 중 오류 발생: {e}")

        logger.info(f"현재 페이지에서 {len(reviews_on_page)}개의 리뷰 텍스트를 추출했습니다.")
        return reviews_on_page, ratings_on_page

    async def _sort_reviews_by_helpfulness(self):
        """리뷰를 '도움순'으로 정렬합니다."""
        logger.info("리뷰를 '도움순'으로 정렬합니다.")
        try:
            sort_button = await self.page.wait_for_selector(
                self.SELECTORS["sort_by_helpfulness_button"],
                timeout=5000
            )
            await sort_button.click()
            logger.info("'도움순' 정렬 버튼 클릭 성공")
            # 정렬 후 리뷰 목록이 새로고침될 때까지 대기
            # TODO: 더 안정적인 대기 방법 (e.g., network idle or a specific element change)
            await self.page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning(f"'도움순'으로 정렬하는 데 실패했습니다: {e}")
            await self.page.screenshot(path="debug_screenshot_sort_fail.png")
            logger.info("디버깅 스크린샷 저장: debug_screenshot_sort_fail.png")

    async def _get_review_rating_distribution(self) -> dict[int, str]:
        """각 별점별 리뷰 분포(%)를 가져옵니다."""
        distribution = {}
        logger.info("리뷰 평점별 분포 가져오기 시작")
        try:
            graph_area_selector = "#gdasContentsArea > div > div.product_rating_area.review-write-delete > div > div.graph_area"
            await self.page.wait_for_selector(graph_area_selector, timeout=5000)

            for i in range(1, 6):  # li:nth-child(1) to li:nth-child(5)
                rating = 6 - i  # 5 stars to 1 star
                selector = f"{graph_area_selector} > ul > li:nth-child({i}) > span.per"
                percentage_text = await self._get_text(selector, timeout=1000)
                if percentage_text:
                    distribution[rating] = percentage_text
                    logger.info(f"{rating}점 리뷰 비율: {percentage_text}")
                else:
                    logger.warning(f"{rating}점 리뷰 비율을 찾을 수 없습니다.")

        except Exception as e:
            logger.warning(f"리뷰 평점별 분포를 가져오는 데 실패했습니다: {e}")
        return distribution

    async def _click_review_tab(self):
        """리뷰 탭을 클릭하여 리뷰 정보를 로드합니다."""
        try:
            review_button = await self.page.wait_for_selector(
                self.SELECTORS["review_button"],
                timeout=10000
            )
            await review_button.click()
            logger.info("리뷰 탭 클릭 성공")
            # 리뷰가 로드될 때까지 잠시 대기합니다.
            # TODO: 리뷰 컨테이너가 나타날 때까지 기다리는 더 안정적인 방법으로 변경해야 합니다.
            await self.page.wait_for_timeout(2000)
            logger.info("리뷰 정보 로딩 대기 완료")
        except Exception as e:
            logger.warning(f"리뷰 탭 클릭 실패: {e}")
            await self.page.screenshot(path="debug_screenshot_review_click_fail.png")
            logger.info("디버깅 스크린샷 저장: debug_screenshot_review_click_fail.png")

    async def _get_price(self) -> str:
        """가격을 추출합니다. 할인가가 있으면 할인가를, 없으면 정가를 반환합니다."""
        try:
            # 먼저 할인가 시도
            try:
                discount_price = await self._get_text(self.SELECTORS["discount_price"], timeout=2000)
                if discount_price:
                    logger.info(f"할인가 발견: {discount_price}")
                    return discount_price
            except Exception:
                logger.debug("할인가를 찾을 수 없습니다.")
            
            # 할인가가 없으면 정가 시도
            try:
                regular_price = await self._get_text(self.SELECTORS["regular_price"], timeout=2000)
                if regular_price:
                    logger.info(f"정가 발견: {regular_price}")
                    return regular_price
            except Exception:
                logger.debug("정가를 찾을 수 없습니다.")
            
            logger.warning("정가와 할인가 모두 찾을 수 없습니다.")
            return ""
            
        except Exception as e:
            logger.warning(f"가격 추출 중 오류 발생: {e}")
            return ""

    def _parse_rating_from_text(self, rating_text: str) -> str:
        """'5점만점에 x점' 형식의 텍스트에서 별점만 추출합니다."""
        try:
            if "점만점에" in rating_text and "점" in rating_text:
                # '5점만점에 4점' -> '4' 추출
                parts = rating_text.split("점만점에")
                if len(parts) > 1:
                    score_part = parts[1].replace("점", "").strip()
                    return score_part
            return ""
        except Exception as e:
            logger.warning(f"별점 파싱 실패: {rating_text}, 에러: {e}")
            return ""

    async def _get_text(self, selector: str, timeout: int = 10000) -> str:
        """CSS selector로 요소의 텍스트를 가져옵니다."""
        element = await self.page.wait_for_selector(selector, state='attached', timeout=timeout)
        text = await element.text_content()
        return text.strip() if text else ""

    async def _get_detail_images(self) -> list[str]:
        """제품 상세 이미지들을 가져옵니다."""
        # 페이지를 아래로 스크롤하여 상세정보 영역 로딩
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await self.page.wait_for_timeout(2000)

        # 상세정보 토글 버튼 클릭
        try:
            toggle_btn = await self.page.wait_for_selector(
                self.SELECTORS["detail_toggle"],
                timeout=10000
            )
            await toggle_btn.click()
            logger.info("상세정보 토글 버튼 클릭 성공")
            await self.page.wait_for_timeout(3000)  # 이미지 로딩 대기
        except Exception as e:
            logger.warning(f"상세정보 토글 버튼 클릭 실패: {e}")
            await self.page.screenshot(path="debug_screenshot.png")
            logger.info("디버깅 스크린샷 저장: debug_screenshot.png")
            return []

        # 모든 이미지 URL 수집 - 다중 셀렉터 패턴 사용
        images = []
        logger.info("상세 이미지 수집 시작")
        
        # 다양한 제품 페이지 구조에 대응하기 위한 셀렉터 패턴들
        selector_patterns = [
            # 최신 구체적 패턴 (최우선)
            {"container": "#tempHtml2 > center", "selector": "#tempHtml2 > center > div:nth-child(1) > img:nth-child(1)"},
            {"container": "#tempHtml2 > center", "selector": "#tempHtml2 > center > div img"},
            {"container": "#tempHtml2 > center", "selector": "#tempHtml2 > center img"},
            # 기본 패턴
            {"container": "#tempHtml2", "selector": "#tempHtml2 > div"},
            {"container": "#tempHtml2", "selector": "#tempHtml2 img"},
            # 대체 패턴들
            {"container": "#tempHtml", "selector": "#tempHtml > div"},
            {"container": "#tempHtml", "selector": "#tempHtml img"},
            {"container": ".detail_info_wrap", "selector": ".detail_info_wrap img"},
            {"container": ".prd_detail_info", "selector": ".prd_detail_info img"},
            {"container": ".goods_detail_wrap", "selector": ".goods_detail_wrap img"},
        ]
        
        for pattern in selector_patterns:
            try:
                container_selector = pattern["container"]
                img_selector = pattern["selector"]
                
                # 컨테이너가 지정된 경우 존재 여부 확인
                if container_selector:
                    containers = await self.page.query_selector_all(container_selector)
                    if not containers:
                        logger.debug(f"컨테이너 '{container_selector}' 없음, 다음 패턴 시도")
                        continue
                
                # div 컨테이너 기반 패턴
                if " > div" in img_selector:
                    div_containers = await self.page.query_selector_all(img_selector)
                    logger.debug(f"패턴 '{img_selector}': {len(div_containers)}개 div 컨테이너 발견")
                    
                    for i, div_container in enumerate(div_containers, 1):
                        imgs_in_div = await div_container.query_selector_all("img")
                        logger.debug(f"Div 컨테이너 #{i}에서 {len(imgs_in_div)}개의 img 태그 발견")

                        for img in imgs_in_div:
                            src = await self._extract_image_src(img)
                            if src and src not in images:
                                images.append(src)
                                logger.debug(f"이미지 추가: {src}")
                
                # 직접 이미지 셀렉터 패턴
                else:
                    img_elements = await self.page.query_selector_all(img_selector)
                    logger.debug(f"패턴 '{img_selector}': {len(img_elements)}개 이미지 발견")
                    
                    for img in img_elements:
                        src = await self._extract_image_src(img)
                        if src and src not in images:
                            images.append(src)
                            logger.debug(f"이미지 추가: {src}")
                
                # 이미지를 찾았다면 추가 패턴 시도 중단
                if images:
                    logger.info(f"패턴 '{img_selector}'에서 {len(images)}개 이미지 발견")
                    break
                    
            except Exception as e:
                logger.debug(f"패턴 '{pattern['selector']}' 처리 중 오류: {e}")
                continue

        if images:
            logger.info(f"총 {len(images)}개의 상세 이미지 URL 수집 완료")
        else:
            logger.warning("모든 셀렉터 패턴에서 상세 이미지를 찾을 수 없습니다")
            # 디버깅을 위해 스크린샷과 HTML 저장
            await self.page.screenshot(path="debug_screenshot_detail_img.png")
            html_content = await self.page.content()
            with open("debug_page_source_detail_img.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info("상세 이미지 디버깅 파일 저장 완료")

        return images

    async def _extract_image_src(self, img_element) -> Optional[str]:
        """이미지 요소에서 src 속성을 추출합니다."""
        try:
            # 다양한 src 속성 시도
            src = await img_element.get_attribute("src")
            if not src or "http" not in src:
                src = await img_element.get_attribute("data-src")
            if not src or "http" not in src:
                src = await img_element.get_attribute("data-original")
            if not src or "http" not in src:
                src = await img_element.get_attribute("data-lazy")

            return src if src and "http" in src else None
        except Exception as e:
            logger.debug(f"이미지 src 추출 실패: {e}")
            return None

    async def _load_cookies(self):
        """cookies.json 파일에서 쿠키를 로드하여 페이지에 주입합니다."""
        try:
            cookie_file = Path("cookies.json")
            if not cookie_file.exists():
                logger.warning("cookies.json 파일이 없습니다. 쿠키 없이 진행합니다.")
                return

            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)

            # EditThisCookie 형식의 중첩 배열 처리
            if isinstance(cookies_data, list) and len(cookies_data) > 0:
                if isinstance(cookies_data[0], list):
                    cookies_data = cookies_data[0]

            # Playwright 형식으로 변환하여 추가
            playwright_cookies = []
            for cookie in cookies_data:
                playwright_cookie = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie.get('path', '/'),
                }

                # 선택적 필드 추가
                if 'expirationDate' in cookie:
                    playwright_cookie['expires'] = cookie['expirationDate']
                if 'httpOnly' in cookie:
                    playwright_cookie['httpOnly'] = cookie['httpOnly']
                if 'secure' in cookie:
                    playwright_cookie['secure'] = cookie['secure']
                if 'sameSite' in cookie and cookie['sameSite'] != 'unspecified':
                    # sameSite 값 변환
                    same_site_map = {
                        'no_restriction': 'None',
                        'lax': 'Lax',
                        'strict': 'Strict'
                    }
                    playwright_cookie['sameSite'] = same_site_map.get(cookie['sameSite'], 'Lax')

                playwright_cookies.append(playwright_cookie)

            # 쿠키 추가
            await self.page.context.add_cookies(playwright_cookies)
            logger.info(f"✅ {len(playwright_cookies)}개의 쿠키를 성공적으로 로드했습니다.")

            # 중요한 쿠키 확인
            important_cookies = ['__cf_bm', '_cfuvid', 'cf_clearance']
            loaded_important = [c['name'] for c in playwright_cookies if c['name'] in important_cookies]
            if loaded_important:
                logger.info(f"🔑 Cloudflare 쿠키 로드됨: {', '.join(loaded_important)}")

        except Exception as e:
            logger.warning(f"쿠키 로드 실패: {e}. 쿠키 없이 진행합니다.")
