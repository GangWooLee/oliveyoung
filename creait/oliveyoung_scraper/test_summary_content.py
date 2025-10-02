import sqlite3
import json
from src.database import DB_FILE

def analyze_summary_content():
    """통합된 상세 정보 내용 분석"""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute('SELECT detailed_summary FROM products WHERE id = 8')
    result = cur.fetchone()

    if result and result[0]:
        summary = result[0]
        print('🔍 제품 ID 8의 통합된 상세 정보 (전체):')
        print('=' * 80)
        
        # ```json 태그 제거
        if summary.startswith('```json'):
            summary = summary.replace('```json', '').replace('```', '').strip()
        
        try:
            # JSON 파싱
            parsed = json.loads(summary)
            
            print('📊 통합된 정보의 구조와 내용:')
            print('=' * 60)
            
            for section, content in parsed.items():
                print(f'\n🔸 {section.upper()}:')
                if isinstance(content, dict):
                    for key, value in content.items():
                        if isinstance(value, list):
                            if value:  # 리스트가 비어있지 않으면
                                print(f'   • {key}: {value}')
                            else:
                                print(f'   • {key}: (정보 없음)')
                        else:
                            if value and str(value).strip():  # 값이 있으면
                                print(f'   • {key}: {value}')
                            else:
                                print(f'   • {key}: (정보 없음)')
                elif isinstance(content, list):
                    if content:
                        print(f'   • {content}')
                    else:
                        print(f'   • (정보 없음)')
                else:
                    if content and str(content).strip():
                        print(f'   • {content}')
                    else:
                        print('   • (정보 없음)')
                        
            print('\n' + '=' * 80)
            print('🎯 분석 결과:')
            
            # 정보 충실도 평가
            total_fields = 0
            filled_fields = 0
            
            def count_fields(obj, prefix=''):
                nonlocal total_fields, filled_fields
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, (dict, list)):
                            count_fields(value, f'{prefix}.{key}' if prefix else key)
                        else:
                            total_fields += 1
                            if value and str(value).strip() and value != 'null':
                                filled_fields += 1
                elif isinstance(obj, list):
                    total_fields += 1
                    if obj:
                        filled_fields += 1
            
            count_fields(parsed)
            
            fill_rate = (filled_fields / total_fields * 100) if total_fields > 0 else 0
            print(f'   정보 충실도: {filled_fields}/{total_fields}개 필드 ({fill_rate:.1f}%)')
            
            if fill_rate > 70:
                print('   ✅ 매우 상세한 정보가 성공적으로 통합되었습니다!')
            elif fill_rate > 50:
                print('   ✅ 충분한 정보가 통합되었습니다.')
            else:
                print('   ⚠️ 일부 정보가 부족합니다.')
                
        except json.JSONDecodeError as e:
            print(f'❌ JSON 파싱 실패: {e}')
            print('원본 텍스트:')
            print(summary[:500] + '...' if len(summary) > 500 else summary)

    else:
        print('❌ 통합된 정보가 없습니다.')

    con.close()

if __name__ == "__main__":
    analyze_summary_content()