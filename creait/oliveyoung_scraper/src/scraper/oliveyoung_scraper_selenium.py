"""Olive Young 제품 정보 스크래퍼 (Selenium Undetected ChromeDriver 기반)"""
import time
import json
from pathlib import Path
from typing import Optional
from loguru import logger
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


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


class OliveYoungScraperSelenium:
    """Olive Young 제품 페이지 스크래퍼 (Selenium Undetected ChromeDriver 기반)"""

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

    def __init__(self, headless: bool = False):
        """
        Args:
            headless: 브라우저를 headless 모드로 실행할지 여부
        """
        self.headless = headless
        self.driver = None

    def __enter__(self):
        """Context manager entry"""
        # SSL 검증 무시 설정
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context

        # Undetected ChromeDriver 옵션 설정
        options = uc.ChromeOptions()

        if self.headless:
            options.add_argument('--headless=new')

        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-gpu')
        options.add_argument('--lang=ko-KR')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')

        # User Agent 설정
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

        # Undetected ChromeDriver 초기화
        self.driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)

        # 쿠키 로드
        self._load_cookies()

        logger.info("Selenium Undetected ChromeDriver 초기화 완료")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.driver:
            self.driver.quit()

    def scrape(self, url: str, max_reviews: int = 30) -> ProductInfo:
        """
        제품 페이지에서 정보를 스크래핑합니다.

        Args:
            url: Olive Young 제품 페이지 URL
            max_reviews: 최대 스크래핑할 리뷰 개수

        Returns:
            ProductInfo: 스크래핑된 제품 정보
        """
        if not self.driver:
            raise RuntimeError("Scraper must be used as context manager")

        logger.info(f"Scraping URL: {url}")

        # 페이지 로딩
        self.driver.get(url)
        logger.info("페이지 초기 로딩 완료")

        # Cloudflare 체크 대기
        self._wait_for_cloudflare()

        # 추가 안정화 대기
        time.sleep(3)

        # 마우스 움직임 시뮬레이션
        self.driver.execute_script("window.scrollTo(0, 200)")
        time.sleep(1)
        self.driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(1)

        product = ProductInfo()

        # 제품명
        try:
            time.sleep(1)
            product.name = self._get_text(self.SELECTORS["name"])
            logger.info(f"제품명: {product.name}")
        except Exception as e:
            logger.warning(f"제품명 가져오기 실패: {e}")

        # 가격
        try:
            product.price = self._get_price()
            logger.info(f"가격: {product.price}")
        except Exception as e:
            logger.warning(f"가격 가져오기 실패: {e}")

        # 리뷰 평점
        try:
            product.rating = self._get_text(self.SELECTORS["rating"])
            logger.info(f"평점: {product.rating}")
        except Exception as e:
            logger.warning(f"평점 가져오기 실패: {e}")

        # 리뷰 개수
        try:
            product.review_count = self._get_text(self.SELECTORS["review_count"])
            logger.info(f"리뷰 개수: {product.review_count}")
        except Exception as e:
            logger.warning(f"리뷰 개수 가져오기 실패: {e}")

        # 제품 상세정보 이미지
        try:
            product.detail_images = self._get_detail_images()
            logger.info(f"상세 이미지 개수: {len(product.detail_images)}")
        except Exception as e:
            logger.warning(f"상세 이미지 가져오기 실패: {e}")

        # 리뷰 탭 클릭, 평점 분포 가져오기, 정렬 및 추출
        try:
            self._click_review_tab()
            product.review_rating_distribution = self._get_review_rating_distribution()
            self._sort_reviews_by_helpfulness()

            # 페이지네이션하며 모든 리뷰 추출
            product.reviews, product.review_ratings = self._paginate_and_extract_reviews(max_reviews=max_reviews)
            logger.info(f"총 {len(product.reviews)}개의 리뷰 추출 완료")

        except Exception as e:
            logger.warning(f"리뷰 정보 가져오기, 정렬 및 추출 실패: {e}")

        return product

    def _wait_for_cloudflare(self):
        """Cloudflare 체크 대기"""
        logger.info("Cloudflare 체크 대기 중...")

        max_wait = 120  # 최대 2분
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text

                # Cloudflare 체크 화면이 아닌지 확인
                if ('잠시만 기다려 주세요' not in body_text and
                    '확인 중' not in body_text and
                    'Checking your browser' not in body_text):
                    logger.info("✅ Cloudflare 체크 통과!")
                    return

                # Cloudflare 화면이 보이면 사용자에게 알림
                if '잠시만 기다려 주세요' in body_text or 'Checking your browser' in body_text:
                    if time.time() - start_time < 10:  # 처음 10초만 메시지 출력
                        logger.info("🔴 Cloudflare 봇 탐지 활성화됨. 자동 대기 중...")

                time.sleep(2)

            except Exception as e:
                logger.debug(f"Cloudflare 체크 중 오류: {e}")
                time.sleep(2)

        logger.warning("⚠️ Cloudflare 체크 대기 타임아웃. 계속 진행...")

    def _load_cookies(self):
        """cookies.json 파일에서 쿠키를 로드하여 브라우저에 주입합니다."""
        try:
            cookie_file = Path("cookies.json")
            if not cookie_file.exists():
                logger.warning("cookies.json 파일이 없습니다. 쿠키 없이 진행합니다.")
                return

            # 먼저 도메인에 접속해야 쿠키를 설정할 수 있음
            self.driver.get("https://www.oliveyoung.co.kr")
            time.sleep(2)

            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies_data = json.load(f)

            # EditThisCookie 형식의 중첩 배열 처리
            if isinstance(cookies_data, list) and len(cookies_data) > 0:
                if isinstance(cookies_data[0], list):
                    cookies_data = cookies_data[0]

            # Selenium 형식으로 변환하여 추가
            for cookie in cookies_data:
                selenium_cookie = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie.get('path', '/'),
                }

                # 선택적 필드 추가
                if 'expirationDate' in cookie:
                    selenium_cookie['expiry'] = int(cookie['expirationDate'])
                if 'httpOnly' in cookie:
                    selenium_cookie['httpOnly'] = cookie['httpOnly']
                if 'secure' in cookie:
                    selenium_cookie['secure'] = cookie['secure']
                if 'sameSite' in cookie and cookie['sameSite'] != 'unspecified':
                    same_site_map = {
                        'no_restriction': 'None',
                        'lax': 'Lax',
                        'strict': 'Strict'
                    }
                    selenium_cookie['sameSite'] = same_site_map.get(cookie['sameSite'], 'Lax')

                try:
                    self.driver.add_cookie(selenium_cookie)
                except Exception as e:
                    logger.debug(f"쿠키 추가 실패 ({cookie['name']}): {e}")

            logger.info(f"✅ {len(cookies_data)}개의 쿠키를 로드했습니다.")

            # 중요한 쿠키 확인
            important_cookies = ['__cf_bm', '_cfuvid', 'cf_clearance']
            loaded_important = [c['name'] for c in cookies_data if c['name'] in important_cookies]
            if loaded_important:
                logger.info(f"🔑 Cloudflare 쿠키 로드됨: {', '.join(loaded_important)}")

        except Exception as e:
            logger.warning(f"쿠키 로드 실패: {e}. 쿠키 없이 진행합니다.")

    def _get_text(self, selector: str, timeout: int = 10) -> str:
        """CSS selector로 요소의 텍스트를 가져옵니다."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            text = element.text
            return text.strip() if text else ""
        except TimeoutException:
            raise Exception(f"Element not found: {selector}")

    def _get_price(self) -> str:
        """가격을 추출합니다."""
        try:
            # 먼저 할인가 시도
            try:
                discount_price = self._get_text(self.SELECTORS["discount_price"], timeout=2)
                if discount_price:
                    logger.info(f"할인가 발견: {discount_price}")
                    return discount_price
            except Exception:
                logger.debug("할인가를 찾을 수 없습니다.")

            # 할인가가 없으면 정가 시도
            try:
                regular_price = self._get_text(self.SELECTORS["regular_price"], timeout=2)
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

    def _get_detail_images(self) -> list[str]:
        """제품 상세 이미지들을 가져옵니다."""
        # 페이지를 아래로 스크롤하여 상세정보 영역 로딩
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2)")
        time.sleep(2)

        # 상세정보 토글 버튼 클릭
        try:
            toggle_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTORS["detail_toggle"]))
            )
            toggle_btn.click()
            logger.info("상세정보 토글 버튼 클릭 성공")
            time.sleep(3)
        except Exception as e:
            logger.warning(f"상세정보 토글 버튼 클릭 실패: {e}")
            self.driver.save_screenshot("debug_screenshot.png")
            logger.info("디버깅 스크린샷 저장: debug_screenshot.png")
            return []

        # 모든 이미지 URL 수집
        images = []
        logger.info("상세 이미지 수집 시작")

        selector_patterns = [
            "#tempHtml2 > center img",
            "#tempHtml2 img",
            "#tempHtml img",
            ".detail_info_wrap img",
            ".prd_detail_info img",
            ".goods_detail_wrap img",
        ]

        for selector in selector_patterns:
            try:
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                logger.debug(f"패턴 '{selector}': {len(img_elements)}개 이미지 발견")

                for img in img_elements:
                    src = self._extract_image_src(img)
                    if src and src not in images:
                        images.append(src)
                        logger.debug(f"이미지 추가: {src}")

                if images:
                    logger.info(f"패턴 '{selector}'에서 {len(images)}개 이미지 발견")
                    break

            except Exception as e:
                logger.debug(f"패턴 '{selector}' 처리 중 오류: {e}")
                continue

        if images:
            logger.info(f"총 {len(images)}개의 상세 이미지 URL 수집 완료")
        else:
            logger.warning("모든 셀렉터 패턴에서 상세 이미지를 찾을 수 없습니다")

        return images

    def _extract_image_src(self, img_element) -> Optional[str]:
        """이미지 요소에서 src 속성을 추출합니다."""
        try:
            src = img_element.get_attribute("src")
            if not src or "http" not in src:
                src = img_element.get_attribute("data-src")
            if not src or "http" not in src:
                src = img_element.get_attribute("data-original")
            if not src or "http" not in src:
                src = img_element.get_attribute("data-lazy")

            return src if src and "http" in src else None
        except Exception as e:
            logger.debug(f"이미지 src 추출 실패: {e}")
            return None

    def _click_review_tab(self):
        """리뷰 탭을 클릭하여 리뷰 정보를 로드합니다."""
        try:
            review_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTORS["review_button"]))
            )
            review_button.click()
            logger.info("리뷰 탭 클릭 성공")
            time.sleep(2)
            logger.info("리뷰 정보 로딩 대기 완료")
        except Exception as e:
            logger.warning(f"리뷰 탭 클릭 실패: {e}")
            self.driver.save_screenshot("debug_screenshot_review_click_fail.png")
            logger.info("디버깅 스크린샷 저장: debug_screenshot_review_click_fail.png")

    def _get_review_rating_distribution(self) -> dict[int, str]:
        """각 별점별 리뷰 분포(%)를 가져옵니다."""
        distribution = {}
        logger.info("리뷰 평점별 분포 가져오기 시작")
        try:
            graph_area_selector = "#gdasContentsArea > div > div.product_rating_area.review-write-delete > div > div.graph_area"
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, graph_area_selector))
            )

            for i in range(1, 6):
                rating = 6 - i
                selector = f"{graph_area_selector} > ul > li:nth-child({i}) > span.per"
                try:
                    percentage_text = self._get_text(selector, timeout=1)
                    if percentage_text:
                        distribution[rating] = percentage_text
                        logger.info(f"{rating}점 리뷰 비율: {percentage_text}")
                    else:
                        logger.warning(f"{rating}점 리뷰 비율을 찾을 수 없습니다.")
                except Exception:
                    logger.warning(f"{rating}점 리뷰 비율을 찾을 수 없습니다.")

        except Exception as e:
            logger.warning(f"리뷰 평점별 분포를 가져오는 데 실패했습니다: {e}")
        return distribution

    def _sort_reviews_by_helpfulness(self):
        """리뷰를 '도움순'으로 정렬합니다."""
        logger.info("리뷰를 '도움순'으로 정렬합니다.")
        try:
            sort_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTORS["sort_by_helpfulness_button"]))
            )
            sort_button.click()
            logger.info("'도움순' 정렬 버튼 클릭 성공")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"'도움순'으로 정렬하는 데 실패했습니다: {e}")
            self.driver.save_screenshot("debug_screenshot_sort_fail.png")
            logger.info("디버깅 스크린샷 저장: debug_screenshot_sort_fail.png")

    def _paginate_and_extract_reviews(self, max_reviews: int) -> tuple[list[str], list[str]]:
        """모든 리뷰 페이지를 돌며 최대 max_reviews개까지 리뷰를 추출합니다."""
        all_reviews = []
        all_ratings = []

        while len(all_reviews) < max_reviews:
            reviews_on_page, ratings_on_page = self._extract_reviews_from_page()
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
                current_page_element = self.driver.find_element(By.CSS_SELECTOR, f"{paging_container} > strong")
                if not current_page_element:
                    logger.info("활성화된 페이지 번호를 찾을 수 없어 중단합니다.")
                    break

                current_page_num = int(current_page_element.text.strip())

                next_button = None
                if current_page_num % 10 == 0:
                    try:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, f"{paging_container} > a.next")
                    except NoSuchElementException:
                        pass
                else:
                    try:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, f"{paging_container} > strong + a")
                    except NoSuchElementException:
                        pass

                if not next_button:
                    logger.info("마지막 페이지입니다. 리뷰 추출을 종료합니다.")
                    break

                button_text = next_button.text.strip()
                logger.info(f"다음 페이지로 이동합니다: '{button_text}'")
                next_button.click()
                time.sleep(2)

            except Exception as e:
                logger.warning(f"페이지 이동 중 오류 발생: {e}. 페이지네이션을 중단합니다.")
                break

        return all_reviews, all_ratings

    def _extract_reviews_from_page(self) -> tuple[list[str], list[str]]:
        """현재 페이지의 리뷰 텍스트와 별점을 추출합니다."""
        reviews_on_page = []
        ratings_on_page = []
        logger.info("현재 페이지의 리뷰 추출 시작")

        try:
            review_list_selector = "#gdasList"
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, review_list_selector))
            )

            review_elements = self.driver.find_elements(By.CSS_SELECTOR, f"{review_list_selector} > li")
            logger.info(f"현재 페이지에서 {len(review_elements)}개의 리뷰 항목을 찾았습니다.")

            for i in range(1, len(review_elements) + 1):
                review_text_selector = f"#gdasList > li:nth-child({i}) > div.review_cont > div.txt_inner"
                review_rating_selector = f"#gdasList > li:nth-child({i}) > div.review_cont > div.score_area > span.review_point > span"

                try:
                    text = self._get_text(review_text_selector, timeout=1)
                    rating_text = self._get_text(review_rating_selector, timeout=1)
                    rating = self._parse_rating_from_text(rating_text)

                    reviews_on_page.append(text)
                    ratings_on_page.append(rating)
                    logger.debug(f"{i}번째 리뷰 추출 성공. 별점: {rating}")
                except Exception:
                    logger.warning(f"{i}번째 리뷰에서 텍스트(.txt_inner) 또는 별점을 찾지 못했습니다. 포토리뷰일 수 있습니다.")

        except Exception as e:
            logger.error(f"리뷰 목록 추출 중 오류 발생: {e}")

        logger.info(f"현재 페이지에서 {len(reviews_on_page)}개의 리뷰 텍스트를 추출했습니다.")
        return reviews_on_page, ratings_on_page

    def _parse_rating_from_text(self, rating_text: str) -> str:
        """'5점만점에 x점' 형식의 텍스트에서 별점만 추출합니다."""
        try:
            if "점만점에" in rating_text and "점" in rating_text:
                parts = rating_text.split("점만점에")
                if len(parts) > 1:
                    score_part = parts[1].replace("점", "").strip()
                    return score_part
            return ""
        except Exception as e:
            logger.warning(f"별점 파싱 실패: {rating_text}, 에러: {e}")
            return ""