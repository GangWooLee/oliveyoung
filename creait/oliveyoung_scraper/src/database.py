import sqlite3
from loguru import logger
from pathlib import Path
from typing import Optional

# ProductInfo 클래스의 정확한 임포트 경로를 확인해야 합니다.
# 현재 구조상으로는 아래 경로가 맞을 것으로 예상됩니다.
from src.scraper.oliveyoung_scraper import ProductInfo

DB_FILE = Path(__file__).parent.parent / "creait.db"

def init_db():
    """데이터베이스 파일을 초기화하고 테이블을 생성합니다."""
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()

        # products 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                name TEXT,
                price TEXT,
                rating TEXT,
                review_count TEXT,
                rating_dist_5_star_percent TEXT,
                rating_dist_4_star_percent TEXT,
                rating_dist_3_star_percent TEXT,
                rating_dist_2_star_percent TEXT,
                rating_dist_1_star_percent TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # product_images 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS product_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        """)

        # product_reviews 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS product_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                review_text TEXT,
                review_rating TEXT,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        """)

        # product_image_texts 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS product_image_texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (image_id) REFERENCES product_images (id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        """)

        # 기존 테이블에 review_rating 컬럼이 없으면 추가
        try:
            cur.execute("ALTER TABLE product_reviews ADD COLUMN review_rating TEXT")
            logger.info("기존 product_reviews 테이블에 review_rating 컬럼을 추가했습니다.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("review_rating 컬럼이 이미 존재합니다.")
            else:
                logger.warning(f"컬럼 추가 중 오류: {e}")

        # 기존 테이블에 detailed_summary 컬럼이 없으면 추가
        try:
            cur.execute("ALTER TABLE products ADD COLUMN detailed_summary TEXT")
            logger.info("기존 products 테이블에 detailed_summary 컬럼을 추가했습니다.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("detailed_summary 컬럼이 이미 존재합니다.")
            else:
                logger.warning(f"컬럼 추가 중 오류: {e}")

        # review_analysis 테이블 생성 (리뷰 분석 결과 저장)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                sentiment_group TEXT NOT NULL,
                advantages TEXT NOT NULL,
                disadvantages TEXT NOT NULL,
                review_count INTEGER NOT NULL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        """)

        # product_evaluations 테이블 생성 (제품 평가 결과 저장)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS product_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                weighted_score REAL NOT NULL,
                contradiction_penalties REAL NOT NULL,
                final_score REAL NOT NULL,
                evaluation_details TEXT NOT NULL,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        """)

        # claims_vs_reality 테이블 생성 (마케팅 주장 vs 실제 리뷰 분석 결과 저장)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS claims_vs_reality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                contradictions TEXT NOT NULL,
                consistency_points TEXT NOT NULL,
                overall_assessment TEXT NOT NULL,
                trust_level TEXT NOT NULL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        """)

        con.commit()
        logger.info(f"데이터베이스 초기화 완료: {DB_FILE}")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류 발생: {e}")
    finally:
        if con:
            con.close()

def save_image_text(image_id: int, product_id: int, image_url: str, extracted_text: str):
    """이미지에서 추출된 텍스트를 데이터베이스에 저장합니다. (성공한 경우에만)"""
    if not extracted_text or not extracted_text.strip():
        logger.debug(f"빈 텍스트이므로 저장하지 않습니다: image_id={image_id}")
        return False
    
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        # 기존 데이터가 있는지 확인
        cur.execute("SELECT id FROM product_image_texts WHERE image_id = ?", (image_id,))
        existing = cur.fetchone()
        
        if existing:
            # 업데이트
            cur.execute("""
                UPDATE product_image_texts 
                SET extracted_text = ?, extracted_at = CURRENT_TIMESTAMP
                WHERE image_id = ?
            """, (extracted_text, image_id))
            logger.info(f"이미지 ID {image_id}의 텍스트가 업데이트되었습니다.")
        else:
            # 새로 삽입
            cur.execute("""
                INSERT INTO product_image_texts (image_id, product_id, image_url, extracted_text) 
                VALUES (?, ?, ?, ?)
            """, (image_id, product_id, image_url, extracted_text))
            logger.info(f"이미지 ID {image_id}의 텍스트가 저장되었습니다.")
        
        con.commit()
        return True
        
    except Exception as e:
        logger.error(f"이미지 텍스트 저장 중 오류 발생: {e}")
        if con:
            con.rollback()
        return False
    finally:
        if con:
            con.close()

def get_product_images_with_ids(product_id: Optional[int] = None) -> list[tuple]:
    """제품의 이미지 정보를 ID와 함께 가져옵니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        if product_id:
            cur.execute("""
                SELECT pi.id, p.id, p.name, pi.image_url 
                FROM products p 
                JOIN product_images pi ON p.id = pi.product_id 
                WHERE p.id = ?
                ORDER BY p.id, pi.id
            """, (product_id,))
        else:
            cur.execute("""
                SELECT pi.id, p.id, p.name, pi.image_url 
                FROM products p 
                JOIN product_images pi ON p.id = pi.product_id 
                ORDER BY p.id, pi.id
            """)
        
        return cur.fetchall()
        
    except Exception as e:
        logger.error(f"제품 이미지 조회 중 오류 발생: {e}")
        return []
    finally:
        if con:
            con.close()

def get_product_images(product_id: Optional[int] = None) -> list[tuple]:
    """제품의 이미지 정보를 가져옵니다. (호환성 유지)"""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        if product_id:
            cur.execute("""
                SELECT p.id, p.name, pi.image_url 
                FROM products p 
                JOIN product_images pi ON p.id = pi.product_id 
                WHERE p.id = ?
                ORDER BY p.id, pi.id
            """, (product_id,))
        else:
            cur.execute("""
                SELECT p.id, p.name, pi.image_url 
                FROM products p 
                JOIN product_images pi ON p.id = pi.product_id 
                ORDER BY p.id, pi.id
            """)
        
        return cur.fetchall()
        
    except Exception as e:
        logger.error(f"제품 이미지 조회 중 오류 발생: {e}")
        return []
    finally:
        if con:
            con.close()

def get_unprocessed_images() -> list[tuple]:
    """아직 텍스트 추출이 되지 않은 이미지들을 가져옵니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        cur.execute("""
            SELECT pi.id, p.id, p.name, pi.image_url 
            FROM products p 
            JOIN product_images pi ON p.id = pi.product_id 
            LEFT JOIN product_image_texts pit ON pi.id = pit.image_id
            WHERE pit.id IS NULL
            ORDER BY p.id, pi.id
        """)
        
        return cur.fetchall()
        
    except Exception as e:
        logger.error(f"미처리 이미지 조회 중 오류 발생: {e}")
        return []
    finally:
        if con:
            con.close()

def save_product_info(product_info: ProductInfo, url: str):
    """스크래핑된 제품 정보를 데이터베이스에 저장합니다."""
    if not product_info or not product_info.name:
        logger.warning("저장할 제품 정보가 유효하지 않습니다.")
        return

    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()

        # 1. 제품 정보 삽입 또는 업데이트
        dist = product_info.review_rating_distribution
        
        cur.execute("SELECT id FROM products WHERE url = ?", (url,))
        result = cur.fetchone()
        if result:
            product_id = result[0]
            logger.info(f"기존 제품 발견 (ID: {product_id}). 데이터를 업데이트합니다.")
            # 기존 이미지/리뷰 삭제 (ON DELETE CASCADE로 자동 처리되지만 명시적으로도 가능)
            cur.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
            cur.execute("DELETE FROM product_reviews WHERE product_id = ?", (product_id,))
            
            cur.execute("""
                UPDATE products 
                SET name=?, price=?, rating=?, review_count=?, 
                    rating_dist_5_star_percent=?, rating_dist_4_star_percent=?, 
                    rating_dist_3_star_percent=?, rating_dist_2_star_percent=?, 
                    rating_dist_1_star_percent=?, scraped_at=CURRENT_TIMESTAMP
                WHERE id = ?
            """, (product_info.name, product_info.price, product_info.rating, product_info.review_count,
                  dist.get(5), dist.get(4), dist.get(3), dist.get(2), dist.get(1), product_id))
        else:
            logger.info("새로운 제품을 데이터베이스에 추가합니다.")
            product_data = (
                url,
                product_info.name,
                product_info.price,
                product_info.rating,
                product_info.review_count,
                dist.get(5), dist.get(4), dist.get(3), dist.get(2), dist.get(1)
            )
            cur.execute("""
                INSERT INTO products (
                    url, name, price, rating, review_count,
                    rating_dist_5_star_percent, rating_dist_4_star_percent,
                    rating_dist_3_star_percent, rating_dist_2_star_percent,
                    rating_dist_1_star_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, product_data)
            product_id = cur.lastrowid

        # 2. 상세 이미지 URL 삽입
        if product_info.detail_images:
            image_data = [(product_id, img_url) for img_url in product_info.detail_images]
            cur.executemany("INSERT INTO product_images (product_id, image_url) VALUES (?, ?)", image_data)

        # 3. 리뷰 텍스트와 별점 삽입
        if product_info.reviews and product_info.review_ratings:
            review_data = [(product_id, review_text, review_rating) 
                          for review_text, review_rating in zip(product_info.reviews, product_info.review_ratings)]
            cur.executemany("INSERT INTO product_reviews (product_id, review_text, review_rating) VALUES (?, ?, ?)", review_data)

        con.commit()
        logger.info(f"제품 '{product_info.name}' 정보가 데이터베이스에 성공적으로 저장되었습니다 (ID: {product_id}).")

    except Exception as e:
        logger.error(f"데이터베이스 저장 중 오류 발생: {e}")
        if con:
            con.rollback()
    finally:
        if con:
            con.close()

def save_product_summary(product_id: int, detailed_summary: str) -> bool:
    """제품의 통합된 상세정보를 데이터베이스에 저장합니다."""
    if not detailed_summary or not detailed_summary.strip():
        logger.debug(f"빈 요약이므로 저장하지 않습니다: product_id={product_id}")
        return False
    
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        # 제품 정보 업데이트
        cur.execute("""
            UPDATE products 
            SET detailed_summary = ?
            WHERE id = ?
        """, (detailed_summary, product_id))
        
        if cur.rowcount > 0:
            con.commit()
            logger.info(f"제품 ID {product_id}의 상세 요약이 저장되었습니다.")
            return True
        else:
            logger.warning(f"제품 ID {product_id}를 찾을 수 없습니다.")
            return False
        
    except Exception as e:
        logger.error(f"제품 요약 저장 중 오류 발생: {e}")
        if con:
            con.rollback()
        return False
    finally:
        if con:
            con.close()

def get_product_image_texts(product_id: int) -> list[str]:
    """제품의 모든 이미지에서 추출된 텍스트를 가져옵니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        cur.execute("""
            SELECT extracted_text
            FROM product_image_texts 
            WHERE product_id = ?
            ORDER BY extracted_at ASC
        """, (product_id,))
        
        results = cur.fetchall()
        return [text[0] for text in results if text[0] and text[0].strip()]
        
    except Exception as e:
        logger.error(f"제품 이미지 텍스트 조회 중 오류 발생: {e}")
        return []
    finally:
        if con:
            con.close()

def get_product_reviews_by_rating(product_id: int) -> dict:
    """제품의 리뷰를 별점별로 분류하여 반환합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        cur.execute("""
            SELECT review_text, review_rating
            FROM product_reviews 
            WHERE product_id = ? AND review_text IS NOT NULL AND review_rating IS NOT NULL
            ORDER BY review_rating DESC
        """, (product_id,))
        
        results = cur.fetchall()
        
        # 별점별로 분류
        classified_reviews = {
            'positive_5': [],      # 5점
            'neutral_4_3': [],     # 4-3점
            'negative_2_1': []     # 2-1점
        }
        
        for review_text, rating in results:
            if rating == '5':
                classified_reviews['positive_5'].append(review_text)
            elif rating in ['4', '3']:
                classified_reviews['neutral_4_3'].append(review_text)
            elif rating in ['2', '1']:
                classified_reviews['negative_2_1'].append(review_text)
        
        return classified_reviews
        
    except Exception as e:
        logger.error(f"제품 리뷰 분류 조회 중 오류 발생: {e}")
        return {'positive_5': [], 'neutral_4_3': [], 'negative_2_1': []}
    finally:
        if con:
            con.close()

def save_review_analysis(product_id: int, sentiment_group: str, advantages: str, disadvantages: str, review_count: int) -> bool:
    """리뷰 분석 결과를 데이터베이스에 저장합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        # 기존 분석 결과가 있는지 확인
        cur.execute("""
            SELECT id FROM review_analysis 
            WHERE product_id = ? AND sentiment_group = ?
        """, (product_id, sentiment_group))
        
        existing = cur.fetchone()
        
        if existing:
            # 업데이트
            cur.execute("""
                UPDATE review_analysis 
                SET advantages = ?, disadvantages = ?, review_count = ?, analyzed_at = CURRENT_TIMESTAMP
                WHERE product_id = ? AND sentiment_group = ?
            """, (advantages, disadvantages, review_count, product_id, sentiment_group))
            logger.info(f"제품 ID {product_id}의 {sentiment_group} 분석 결과가 업데이트되었습니다.")
        else:
            # 새로 삽입
            cur.execute("""
                INSERT INTO review_analysis (product_id, sentiment_group, advantages, disadvantages, review_count)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, sentiment_group, advantages, disadvantages, review_count))
            logger.info(f"제품 ID {product_id}의 {sentiment_group} 분석 결과가 저장되었습니다.")
        
        con.commit()
        return True
        
    except Exception as e:
        logger.error(f"리뷰 분석 결과 저장 중 오류 발생: {e}")
        if con:
            con.rollback()
        return False
    finally:
        if con:
            con.close()

def get_review_analysis_results(product_id: Optional[int] = None) -> list[tuple]:
    """리뷰 분석 결과를 조회합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        if product_id:
            cur.execute("""
                SELECT ra.product_id, p.name, ra.sentiment_group, ra.advantages, ra.disadvantages, ra.review_count, ra.analyzed_at
                FROM review_analysis ra
                JOIN products p ON ra.product_id = p.id
                WHERE ra.product_id = ?
                ORDER BY ra.product_id, 
                    CASE ra.sentiment_group 
                        WHEN 'positive_5' THEN 1 
                        WHEN 'neutral_4_3' THEN 2 
                        WHEN 'negative_2_1' THEN 3 
                    END
            """, (product_id,))
        else:
            cur.execute("""
                SELECT ra.product_id, p.name, ra.sentiment_group, ra.advantages, ra.disadvantages, ra.review_count, ra.analyzed_at
                FROM review_analysis ra
                JOIN products p ON ra.product_id = p.id
                ORDER BY ra.product_id, 
                    CASE ra.sentiment_group 
                        WHEN 'positive_5' THEN 1 
                        WHEN 'neutral_4_3' THEN 2 
                        WHEN 'negative_2_1' THEN 3 
                    END
            """)
        
        return cur.fetchall()
        
    except Exception as e:
        logger.error(f"리뷰 분석 결과 조회 중 오류 발생: {e}")
        return []
    finally:
        if con:
            con.close()

def get_product_review_ratings(product_id: int) -> list[tuple]:
    """제품의 모든 리뷰 별점을 가져옵니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        cur.execute("""
            SELECT review_rating, COUNT(*) as count
            FROM product_reviews 
            WHERE product_id = ? AND review_rating IS NOT NULL
            GROUP BY review_rating
            ORDER BY review_rating DESC
        """, (product_id,))
        
        return cur.fetchall()
        
    except Exception as e:
        logger.error(f"제품 리뷰 별점 조회 중 오류 발생: {e}")
        return []
    finally:
        if con:
            con.close()

def save_product_evaluation(product_id: int, weighted_score: float, contradiction_penalties: float, 
                           final_score: float, evaluation_details: str) -> bool:
    """제품 평가 결과를 데이터베이스에 저장합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        # 기존 평가 결과가 있는지 확인
        cur.execute("SELECT id FROM product_evaluations WHERE product_id = ?", (product_id,))
        existing = cur.fetchone()
        
        if existing:
            # 업데이트
            cur.execute("""
                UPDATE product_evaluations 
                SET weighted_score = ?, contradiction_penalties = ?, final_score = ?, 
                    evaluation_details = ?, evaluated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            """, (weighted_score, contradiction_penalties, final_score, evaluation_details, product_id))
            logger.info(f"제품 ID {product_id}의 평가 결과가 업데이트되었습니다.")
        else:
            # 새로 삽입
            cur.execute("""
                INSERT INTO product_evaluations (product_id, weighted_score, contradiction_penalties, final_score, evaluation_details)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, weighted_score, contradiction_penalties, final_score, evaluation_details))
            logger.info(f"제품 ID {product_id}의 평가 결과가 저장되었습니다.")
        
        con.commit()
        return True
        
    except Exception as e:
        logger.error(f"제품 평가 결과 저장 중 오류 발생: {e}")
        if con:
            con.rollback()
        return False
    finally:
        if con:
            con.close()

def get_product_evaluation(product_id: int) -> Optional[tuple]:
    """특정 제품의 평가 결과를 조회합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        cur.execute("""
            SELECT pe.product_id, p.name, pe.weighted_score, pe.contradiction_penalties, 
                   pe.final_score, pe.evaluation_details, pe.evaluated_at
            FROM product_evaluations pe
            JOIN products p ON pe.product_id = p.id
            WHERE pe.product_id = ?
        """, (product_id,))
        
        return cur.fetchone()
        
    except Exception as e:
        logger.error(f"제품 평가 결과 조회 중 오류 발생: {e}")
        return None
    finally:
        if con:
            con.close()

def get_all_product_evaluations() -> list[tuple]:
    """모든 제품의 평가 결과를 조회합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        cur.execute("""
            SELECT pe.product_id, p.name, pe.weighted_score, pe.contradiction_penalties, 
                   pe.final_score, pe.evaluated_at
            FROM product_evaluations pe
            JOIN products p ON pe.product_id = p.id
            ORDER BY pe.final_score DESC
        """)
        
        return cur.fetchall()
        
    except Exception as e:
        logger.error(f"전체 제품 평가 결과 조회 중 오류 발생: {e}")
        return []
    finally:
        if con:
            con.close()

def save_claims_vs_reality_analysis(product_id: int, analysis_result: dict) -> bool:
    """마케팅 주장 vs 실제 리뷰 분석 결과를 데이터베이스에 저장합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        import json
        
        # 기존 분석 결과가 있는지 확인
        cur.execute("SELECT id FROM claims_vs_reality WHERE product_id = ?", (product_id,))
        existing = cur.fetchone()
        
        # JSON 직렬화
        contradictions_json = json.dumps(analysis_result.get('contradictions', []), ensure_ascii=False)
        consistency_points_json = json.dumps(analysis_result.get('consistency_points', []), ensure_ascii=False)
        overall_assessment = analysis_result.get('overall_assessment', '')
        trust_level = analysis_result.get('trust_level', '보통')
        
        if existing:
            # 업데이트
            cur.execute("""
                UPDATE claims_vs_reality 
                SET contradictions = ?, consistency_points = ?, overall_assessment = ?, 
                    trust_level = ?, analyzed_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            """, (contradictions_json, consistency_points_json, overall_assessment, trust_level, product_id))
            logger.info(f"제품 ID {product_id}의 마케팅 주장 vs 실제 리뷰 분석 결과가 업데이트되었습니다.")
        else:
            # 새로 저장
            cur.execute("""
                INSERT INTO claims_vs_reality (product_id, contradictions, consistency_points, 
                                              overall_assessment, trust_level)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, contradictions_json, consistency_points_json, overall_assessment, trust_level))
            logger.info(f"제품 ID {product_id}의 마케팅 주장 vs 실제 리뷰 분석 결과가 저장되었습니다.")
        
        con.commit()
        return True
        
    except Exception as e:
        logger.error(f"마케팅 주장 vs 실제 리뷰 분석 결과 저장 중 오류 발생: {e}")
        if con:
            con.rollback()
        return False
    finally:
        if con:
            con.close()

def get_claims_vs_reality_analysis(product_id: int) -> Optional[tuple]:
    """특정 제품의 마케팅 주장 vs 실제 리뷰 분석 결과를 조회합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        cur.execute("""
            SELECT cvr.product_id, p.name, cvr.contradictions, cvr.consistency_points, 
                   cvr.overall_assessment, cvr.trust_level, cvr.analyzed_at
            FROM claims_vs_reality cvr
            JOIN products p ON cvr.product_id = p.id
            WHERE cvr.product_id = ?
        """, (product_id,))
        
        return cur.fetchone()
        
    except Exception as e:
        logger.error(f"마케팅 주장 vs 실제 리뷰 분석 결과 조회 중 오류 발생: {e}")
        return None
    finally:
        if con:
            con.close()

def get_all_claims_vs_reality_analysis() -> list[tuple]:
    """모든 제품의 마케팅 주장 vs 실제 리뷰 분석 결과를 조회합니다."""
    con = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        
        cur.execute("""
            SELECT cvr.product_id, p.name, cvr.trust_level, cvr.analyzed_at
            FROM claims_vs_reality cvr
            JOIN products p ON cvr.product_id = p.id
            ORDER BY cvr.analyzed_at DESC
        """)
        
        return cur.fetchall()
        
    except Exception as e:
        logger.error(f"전체 마케팅 주장 vs 실제 리뷰 분석 결과 조회 중 오류 발생: {e}")
        return []
    finally:
        if con:
            con.close()
