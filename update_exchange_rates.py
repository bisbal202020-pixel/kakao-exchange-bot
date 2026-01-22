#!/usr/bin/env python3
"""
환율 자동 업데이트 스크립트
GitHub Actions에서 실행되어 환전 고시 환율을 크롤링하고 코드를 자동 업데이트합니다.
"""

import requests
import re
from datetime import datetime

def get_exchange_rates_from_naver():
    """네이버 금융에서 환율 크롤링"""
    try:
        from bs4 import BeautifulSoup
        
        url = "https://finance.naver.com/marketindex/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rates = {}
        
        # 주요 통화 찾기
        currency_items = soup.select('.market_info')
        
        for item in currency_items:
            try:
                # 통화명
                name = item.select_one('.h_lst').text.strip() if item.select_one('.h_lst') else ''
                
                # 현재가
                value = item.select_one('.value').text.strip().replace(',', '') if item.select_one('.value') else ''
                
                # 변동폭
                change_element = item.select_one('.change')
                if change_element:
                    change_text = change_element.text.strip().replace(',', '')
                    # 상승/하락 구분
                    if 'up' in change_element.get('class', []) or 'plus' in change_element.get('class', []):
                        change = '+' + change_text
                    elif 'down' in change_element.get('class', []) or 'minus' in change_element.get('class', []):
                        change = '-' + change_text
                    else:
                        change = '+0.00'
                else:
                    change = '+0.00'
                
                # 통화별 저장
                if 'USD' in name or '미국' in name:
                    rates['USD'] = {'rate': value, 'change': change}
                elif 'JPY' in name or '일본' in name:
                    # JPY는 100엔 기준
                    rates['JPY100'] = {'rate': value, 'change': change}
                elif 'EUR' in name or '유로' in name:
                    rates['EUR'] = {'rate': value, 'change': change}
                elif 'CNY' in name or '중국' in name:
                    rates['CNY'] = {'rate': value, 'change': change}
                elif 'GBP' in name or '영국' in name:
                    rates['GBP'] = {'rate': value, 'change': change}
                    
            except Exception as e:
                print(f"항목 파싱 에러: {e}")
                continue
        
        return rates if len(rates) >= 5 else None
        
    except Exception as e:
        print(f"네이버 금융 크롤링 실패: {e}")
        return None

def get_exchange_rates_from_dunamu():
    """업비트(두나무) API에서 환율 가져오기"""
    try:
        url = "https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD,FRX.KRWJPY,FRX.KRWEUR,FRX.KRWCNY,FRX.KRWGBP"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            rates = {}
            
            for item in data:
                code = item.get('code', '')
                base_price = item.get('basePrice', 0)
                change_price = item.get('changePrice', 0)
                
                # 변동폭 계산
                if change_price > 0:
                    change = f"+{change_price:.2f}"
                elif change_price < 0:
                    change = f"{change_price:.2f}"
                else:
                    change = "+0.00"
                
                if code == 'FRX.KRWUSD':
                    rates['USD'] = {'rate': f"{base_price:,.2f}", 'change': change}
                elif code == 'FRX.KRWJPY':
                    # 100엔 기준
                    rates['JPY100'] = {'rate': f"{base_price * 100:,.2f}", 'change': f"+{change_price * 100:.2f}" if change_price > 0 else f"{change_price * 100:.2f}"}
                elif code == 'FRX.KRWEUR':
                    rates['EUR'] = {'rate': f"{base_price:,.2f}", 'change': change}
                elif code == 'FRX.KRWCNY':
                    rates['CNY'] = {'rate': f"{base_price:,.2f}", 'change': change}
                elif code == 'FRX.KRWGBP':
                    rates['GBP'] = {'rate': f"{base_price:,.2f}", 'change': change}
            
            return rates if len(rates) >= 5 else None
            
    except Exception as e:
        print(f"업비트 API 실패: {e}")
        return None

def update_code_file(rates):
    """코드 파일의 환율 데이터 업데이트"""
    try:
        file_path = 'kakao_exchange_skill_advanced.py'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 현재 시간
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # 새로운 함수 내용 생성
        new_function = f'''def get_fallback_rates():
    """크롤링 실패시 사용할 폴백 환율 데이터 ({now} 환전 고시 환율)"""
    return [
        {{'currency': 'USD', 'rate': '{rates['USD']['rate']}', 'change': '{rates['USD']['change']}', 'flag': '🇺🇸', 'name': '미국 달러'}},
        {{'currency': 'JPY100', 'rate': '{rates['JPY100']['rate']}', 'change': '{rates['JPY100']['change']}', 'flag': '🇯🇵', 'name': '일본 엔'}},
        {{'currency': 'EUR', 'rate': '{rates['EUR']['rate']}', 'change': '{rates['EUR']['change']}', 'flag': '🇪🇺', 'name': '유로'}},
        {{'currency': 'CNY', 'rate': '{rates['CNY']['rate']}', 'change': '{rates['CNY']['change']}', 'flag': '🇨🇳', 'name': '중국 위안'}},
        {{'currency': 'GBP', 'rate': '{rates['GBP']['rate']}', 'change': '{rates['GBP']['change']}', 'flag': '🇬🇧', 'name': '영국 파운드'}}
    ]'''
        
        # 정규식으로 함수 전체 교체
        pattern = r'def get_fallback_rates\(\):.*?return \[.*?\]'
        new_content = re.sub(pattern, new_function, content, flags=re.DOTALL)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ 코드 파일 업데이트 성공!")
        return True
        
    except Exception as e:
        print(f"❌ 코드 파일 업데이트 실패: {e}")
        return False

def main():
    print("🚀 환율 자동 업데이트 시작...")
    
    # 1. 업비트 API 시도
    print("📊 업비트 API 시도...")
    rates = get_exchange_rates_from_dunamu()
    
    # 2. 실패하면 네이버 금융 크롤링
    if not rates:
        print("📊 네이버 금융 크롤링 시도...")
        rates = get_exchange_rates_from_naver()
    
    if not rates:
        print("❌ 모든 환율 소스 실패!")
        return False
    
    # 환율 정보 출력
    print("\n📈 수집된 환율:")
    for currency, data in rates.items():
        print(f"  {currency}: {data['rate']} ({data['change']})")
    
    # 코드 파일 업데이트
    print("\n💾 코드 파일 업데이트 중...")
    success = update_code_file(rates)
    
    if success:
        print("\n✅ 환율 자동 업데이트 완료!")
        return True
    else:
        print("\n❌ 환율 자동 업데이트 실패!")
        return False

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
