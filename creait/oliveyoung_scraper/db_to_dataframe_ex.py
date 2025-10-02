import sqlite3
import pandas as pd
from pathlib import Path
from loguru import logger

DB_FILE = Path(__file__).parent / "creait.db"

def load_products_to_dataframe():
    """
    'products' 테이블의 모든 데이터를 pandas DataFrame으로 불러옵니다.
    """
    if not DB_FILE.exists():
        logger.error(f"데이터베이스 파일이 존재하지 않습니다: {DB_FILE}")
        return None

    try:
        con = sqlite3.connect(DB_FILE)
        
        # SQL 쿼리를 사용하여 'products' 테이블 전체를 읽어옵니다.
        query = "SELECT * FROM products"
        df = pd.read_sql_query(query, con)
        
        logger.info(f"성공적으로 {len(df)}개의 제품을 DataFrame으로 불러왔습니다.")
        return df

    except Exception as e:
        logger.error(f"데이터베이스를 DataFrame으로 불러오는 중 오류 발생: {e}")
        return None
    finally:
        if con:
            con.close()

def main():
    """
    데이터베이스에서 제품 정보를 DataFrame으로 로드하고,
    기본 정보와 처음 5개 행을 출력합니다.
    """
    logger.info("데이터베이스에서 'products' 테이블을 DataFrame으로 변환하는 예제입니다.")
    
    products_df = load_products_to_dataframe()
    
    if products_df is not None:
        logger.info("\n=== DataFrame 정보 ===")
        products_df.info()
        
        logger.info("\n=== DataFrame 상위 5개 행 ===")
        print(products_df.head())
        
        # 예: 특정 컬럼만 선택하여 보기
        logger.info("\n=== 'name'과 'rating' 컬럼만 보기 ===")
        print(products_df[['name', 'rating']].head())

if __name__ == "__main__":
    # 이 스크립트를 실행하려면 pandas 라이브러리가 필요합니다.
    # pip install pandas
    main()
