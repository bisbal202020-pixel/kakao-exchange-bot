from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

def get_exchange_rates_advanced():
    """한국수출입은행 API로 실시간 환율 정보 조회"""
    try:
        from datetime import datetime
        import os
        
        # API 키 (환경변수에서 가져오거나 직접 입력)
        api_key = os.getenv('EXIM_API_KEY', 'YOUR_API_KEY_HERE')
        
        # API 키 확인 로그
        if api_key == 'YOUR_API_KEY_HERE':
            print("⚠️ 한국수출입은행 API 키가 설정되지 않았습니다")
            return None
        
        print(f"🔑 API 키 확인: {api_key[:10]}... (길이: {len(api_key)})")
        
        # 오늘 날짜 (YYYYMMDD)
        today = datetime.now().strftime('%Y%m%d')
        print(f"📅 조회 날짜: {today}")
        
        # 한국수출입은행 API
        url = 'https://www.koreaexim.go.kr/site/program/financial/exchangeJSON'
        params = {
            'authkey': api_key,
            'searchdate': today,
            'data': 'AP01'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        print(f"🌐 API 요청: {url}")
        print(f"📊 파라미터: searchdate={today}, data=AP01")
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        print(f"📡 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ JSON 파싱 성공, 항목 수: {len(data) if isinstance(data, list) else 'dict'}")
            except:
                print(f"❌ JSON 파싱 실패, 응답 내용: {response.text[:200]}")
                return None
            
            # 응답이 에러 메시지인지 확인
            if isinstance(data, dict) and 'error' in data:
                print(f"❌ API 에러 응답: {data}")
                return None
            
            # 필요한 통화만 추출
            target_currencies = {
                'USD': '미국 달러',
                'JPY(100)': '일본 엔',
                'EUR': '유로',
                'CNY': '중국 위안',
                'GBP': '영국 파운드'
            }
            
            rates = []
            
            for item in data:
                cur_unit = item.get('cur_unit', '')
                
                if cur_unit in target_currencies:
                    # 환율
                    deal_bas_r = item.get('deal_bas_r', '0')
                    rate = deal_bas_r.replace(',', '')
                    
                    # 전일 대비
                    try:
                        cur_val = float(rate)
                        yest_val = float(item.get('bkpr', '0').replace(',', ''))
                        change = cur_val - yest_val
                        change_str = f"+{change:.2f}" if change > 0 else f"{change:.2f}"
                    except:
                        change_str = "+0.00"
                    
                    # 통화 코드 정리
                    currency_code = 'JPY100' if cur_unit == 'JPY(100)' else cur_unit
                    
                    rates.append({
                        'currency': currency_code,
                        'rate': deal_bas_r,
                        'change': change_str
                    })
                    
                    print(f"  💱 {currency_code}: {deal_bas_r} ({change_str})")
            
            if rates:
                print(f"✅ 한국수출입은행 API에서 실시간 환율 수집 성공: {len(rates)}개")
                return rates
            else:
                print("⚠️ API 응답은 있지만 대상 통화 데이터가 없음")
                return None
        else:
            print(f"❌ API 요청 실패: {response.status_code}")
            print(f"   응답 내용: {response.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"⏱️ 한국수출입은행 API 타임아웃 (30초 초과)")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"🔌 한국수출입은행 API 연결 실패: {e}")
        return None
    except Exception as e:
        print(f"❌ 한국수출입은행 API 에러: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def get_exchange_rates_naver():
    """네이버 금융 API로 실시간 환율 조회"""
    try:
        # 네이버 금융 환율 API (비공식이지만 안정적)
        base_url = "https://quotation-api-cdn.dunamu.com/v1/forex/recent"
        
        # 필요한 통화 코드
        codes = ['FRX.KRWUSD', 'FRX.KRWJPY', 'FRX.KRWEUR', 'FRX.KRWCNY', 'FRX.KRWGBP']
        
        rates = []
        
        for code in codes:
            try:
                url = f"{base_url}?codes={code}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0:
                        item = data[0]
                        
                        # 통화 코드 추출
                        currency_code = code.replace('FRX.KRW', '')
                        if currency_code == 'JPY':
                            currency_code = 'JPY100'
                            base_price = item.get('basePrice', 0) * 100
                            change_price = item.get('changePrice', 0) * 100
                        else:
                            base_price = item.get('basePrice', 0)
                            change_price = item.get('changePrice', 0)
                        
                        # 변동폭
                        if change_price > 0:
                            change_str = f"+{change_price:.2f}"
                        elif change_price < 0:
                            change_str = f"{change_price:.2f}"
                        else:
                            change_str = "0.00"
                        
                        rates.append({
                            'currency': currency_code,
                            'rate': f"{base_price:,.2f}",
                            'change': change_str
                        })
                        
                        print(f"  💱 {currency_code}: {base_price:,.2f} ({change_str})")
                        
            except Exception as e:
                print(f"  ⚠️ {code} 조회 실패: {e}")
                continue
        
        if rates:
            print(f"✅ 네이버 금융에서 실시간 환율 수집 성공: {len(rates)}개")
            return rates
        else:
            print("❌ 네이버 금융 환율 수집 실패")
            return None
            
    except Exception as e:
        print(f"❌ 네이버 금융 에러: {e}")
        return None

def get_exchange_rates_fallback():
    """대체 API: exchangerate-api.com (무료, API 키 불필요)"""
    try:
        # KRW 기준 환율
        url = "https://open.er-api.com/v6/latest/KRW"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('result') == 'success':
                rates_data = data['rates']
                
                rates = []
                
                # USD
                if 'USD' in rates_data:
                    usd_to_krw = 1 / rates_data['USD']
                    rates.append({
                        'currency': 'USD',
                        'rate': f"{usd_to_krw:,.2f}",
                        'change': '+0.00'
                    })
                
                # JPY (100엔 기준)
                if 'JPY' in rates_data:
                    jpy_to_krw = (1 / rates_data['JPY']) * 100
                    rates.append({
                        'currency': 'JPY100',
                        'rate': f"{jpy_to_krw:,.2f}",
                        'change': '+0.00'
                    })
                
                # EUR
                if 'EUR' in rates_data:
                    eur_to_krw = 1 / rates_data['EUR']
                    rates.append({
                        'currency': 'EUR',
                        'rate': f"{eur_to_krw:,.2f}",
                        'change': '+0.00'
                    })
                
                # CNY
                if 'CNY' in rates_data:
                    cny_to_krw = 1 / rates_data['CNY']
                    rates.append({
                        'currency': 'CNY',
                        'rate': f"{cny_to_krw:,.2f}",
                        'change': '+0.00'
                    })
                
                # GBP
                if 'GBP' in rates_data:
                    gbp_to_krw = 1 / rates_data['GBP']
                    rates.append({
                        'currency': 'GBP',
                        'rate': f"{gbp_to_krw:,.2f}",
                        'change': '+0.00'
                    })
                
                if rates:
                    print(f"✅ ExchangeRate-API에서 환율 수집 성공: {len(rates)}개")
                    return rates
        
        return None
        
    except Exception as e:
        print(f"❌ ExchangeRate-API 에러: {e}")
        return None

def get_fallback_rates():
    """크롤링 실패시 사용할 폴백 환율 데이터"""
    return [
        {'currency': 'USD', 'rate': '1,475.5', 'change': '+5.2', 'flag': '🇺🇸', 'name': '미국 달러'},
        {'currency': 'JPY100', 'rate': '933.54', 'change': '+6.58', 'flag': '🇯🇵', 'name': '일본 엔'},
        {'currency': 'EUR', 'rate': '1,711.8', 'change': '+4.93', 'flag': '🇪🇺', 'name': '유로'},
        {'currency': 'CNY', 'rate': '211.78', 'change': '+0.63', 'flag': '🇨🇳', 'name': '중국 위안'},
        {'currency': 'GBP', 'rate': '2,045.3', 'change': '+3.8', 'flag': '🇬🇧', 'name': '영국 파운드'}
    ]

def get_exchange_news():
    """환율 관련 뉴스 크롤링 (매일경제, MBN, 매경이코노미만)"""
    try:
        url = "https://www.mk.co.kr/news/search/?word=환율"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 허용된 언론사 리스트
        allowed_sources = ['매일경제', 'MBN', '매경이코노미', 'mk.co.kr', 'mbn.co.kr']
        
        news_list = []
        
        # 뉴스 항목 찾기
        articles = soup.find_all('div', class_='news_item')[:20]  # 더 많이 가져와서 필터링
        
        if not articles:
            articles = soup.find_all('li', class_='news_node')[:20]
        
        for article in articles:
            try:
                title_elem = article.find('a')
                if not title_elem:
                    continue
                
                title = title_elem.text.strip()
                link = title_elem.get('href', '')
                
                if link and not link.startswith('http'):
                    link = 'https://www.mk.co.kr' + link
                
                # 언론사 확인
                source_elem = article.find('span', class_='news_source') or article.find('span', class_='source')
                source_text = source_elem.text.strip() if source_elem else ''
                
                # 링크에서 언론사 판단 (매일경제는 mk.co.kr 도메인)
                is_allowed = False
                
                # 1. 명시적 언론사 텍스트 체크
                for allowed in allowed_sources:
                    if allowed in source_text:
                        is_allowed = True
                        break
                
                # 2. URL로 체크 (매일경제 도메인)
                if 'mk.co.kr' in link or 'mbn.co.kr' in link:
                    is_allowed = True
                
                # 허용된 언론사가 아니면 스킵
                if not is_allowed and source_text:
                    continue
                
                # 이미지
                img_elem = article.find('img')
                img_url = img_elem.get('src', '') if img_elem else ''
                if img_url and not img_url.startswith('http'):
                    img_url = 'https:' + img_url if img_url.startswith('//') else ''
                
                # 시간
                time_elem = article.find('span', class_='time')
                time_text = time_elem.text.strip() if time_elem else ''
                
                # 언론사명 (없으면 매일경제로 기본값)
                display_source = source_text if source_text else '매일경제'
                
                news_list.append({
                    'title': title[:50] + '...' if len(title) > 50 else title,
                    'link': link,
                    'image': img_url,
                    'time': time_text,
                    'source': display_source
                })
                
                # 5개 모으면 종료
                if len(news_list) >= 5:
                    break
                
            except:
                continue
        
        # 폴백 뉴스 (매일경제 계열만)
        if not news_list:
            news_list = [
                {'title': '고환율에도 주요소 기름값 6주 연속 내려...국제유가 하락', 'link': 'https://www.mk.co.kr/', 'image': '', 'time': '2시간전', 'source': '매일경제'},
                {'title': '日감사원 美추기 구입비, 헬저급 3년간 2.8조원 낭비', 'link': 'https://www.mk.co.kr/', 'image': '', 'time': '2시간전', 'source': 'MBN'},
                {'title': '[단독] 국민연금이 원화약세 주력하나?', 'link': 'https://www.mk.co.kr/', 'image': '', 'time': '2시간전', 'source': '매경이코노미'}
            ]
        
        return news_list[:5]
        
    except Exception as e:
        print(f"뉴스 크롤링 에러: {e}")
        return [
            {'title': '고환율에도 주요소 기름값 6주 연속 내려...국제유가 하락', 'link': 'https://www.mk.co.kr/', 'image': '', 'time': '2시간전', 'source': '매일경제'},
            {'title': '日감사원 美추기 구입비, 헬저급 3년간 2.8조원 낭비', 'link': 'https://www.mk.co.kr/', 'image': '', 'time': '2시간전', 'source': 'MBN'},
            {'title': '[단독] 국민연금이 원화약세 주력하나?', 'link': 'https://www.mk.co.kr/', 'image': '', 'time': '2시간전', 'source': '매경이코노미'}
        ]

def format_currency_data(rates):
    """환율 데이터를 카카오톡 형식으로 포맷팅"""
    currency_map = {
        'USD': {'flag': '🇺🇸', 'name': '미국 달러'},
        'JPY100': {'flag': '🇯🇵', 'name': '일본 엔'},
        'JPY': {'flag': '🇯🇵', 'name': '일본 엔'},
        'EUR': {'flag': '🇪🇺', 'name': '유로'},
        'CNY': {'flag': '🇨🇳', 'name': '중국 위안'},
        'GBP': {'flag': '🇬🇧', 'name': '영국 파운드'},
        'CHF': {'flag': '🇨🇭', 'name': '스위스 프랑'},
        'CAD': {'flag': '🇨🇦', 'name': '캐나다 달러'}
    }
    
    formatted_rates = []
    for rate in rates:
        currency_code = rate.get('currency', '').split()[0]
        currency_info = currency_map.get(currency_code, {'flag': '💱', 'name': currency_code})
        
        formatted_rates.append({
            'currency': f"{currency_code} ({currency_info['name']})",
            'rate': rate.get('rate', 'N/A'),
            'change': rate.get('change', '0'),
            'flag': currency_info['flag']
        })
    
    return formatted_rates

@app.route('/exchange_rate', methods=['POST'])
def exchange_rate():
    """카카오톡 스킬 엔드포인트"""
    try:
        # 요청 데이터 로깅
        req_data = request.get_json()
        print(f"수신 데이터: {req_data}")
        
        # 환율 정보 가져오기 (우선순위)
        # 1. 네이버 금융 (빠르고 안정적, 변동폭 포함)
        rates = get_exchange_rates_naver()
        
        # 2. 한국수출입은행 API (공식 환율, 접속 문제 가능)
        if not rates:
            print("🔄 한국수출입은행 API 시도중...")
            rates = get_exchange_rates_advanced()
        
        # 3. ExchangeRate-API (무료, API 키 불필요, 변동폭 없음)
        if not rates:
            print("🔄 대체 API 시도중...")
            rates = get_exchange_rates_fallback()
        
        # 4. 폴백 데이터 (고정값)
        if not rates:
            print("⚠️ 모든 API 실패, 폴백 데이터 사용")
            rates = get_fallback_rates()
        
        rates = format_currency_data(rates)
        
        if not rates:
            return create_error_response("환율 정보를 가져오는데 실패했습니다.")
        
        # 뉴스 정보 가져오기
        news_list = get_exchange_news()
        
        # 환율 ListCard 아이템
        exchange_list_items = []
        for rate in rates:
            change_value = str(rate['change']).replace('+', '').replace('-', '')
            
            # 변동폭이 0이면 아이콘 없이 표시
            if change_value == '0.00' or change_value == '0.0' or change_value == '0':
                description = rate['rate']
            else:
                change_icon = "▲" if '+' in str(rate['change']) else "▼"
                description = f"{rate['rate']}  {change_icon} {change_value}"
            
            exchange_list_items.append({
                "title": f"{rate['flag']} {rate['currency']}",
                "description": description
            })
        
        # 뉴스 ListCard 아이템 (이미지 포함)
        news_list_items = []
        for news in news_list:
            item = {
                "title": news['title'][:50] + '...' if len(news['title']) > 50 else news['title'],
                "description": f"{news.get('time', '')} {news.get('source', '매일경제')}".strip(),
                "link": {
                    "web": news['link']
                }
            }
            
            # 썸네일 이미지 추가
            if news.get('image'):
                item['imageUrl'] = news['image']
            
            news_list_items.append(item)
        
        # 응답 구성
        outputs = [
            {
                "listCard": {
                    "header": {
                        "title": "이 시각 환율"
                    },
                    "items": exchange_list_items[:5],
                    "buttons": [
                        {
                            "action": "webLink",
                            "label": "매일경제 마켓",
                            "webLinkUrl": "https://stock.mk.co.kr/"
                        }
                    ]
                }
            },
            {
                "listCard": {
                    "header": {
                        "title": "환율 관련 뉴스"
                    },
                    "items": news_list_items[:5],
                    "buttons": [
                        {
                            "action": "webLink",
                            "label": "뉴스 더보기",
                            "webLinkUrl": "https://www.mk.co.kr/news/search/?word=환율"
                        }
                    ]
                }
            },
            {
                "simpleText": {
                    "text": f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            }
        ]
        
        response = {
            "version": "2.0",
            "template": {
                "outputs": outputs
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return create_error_response(f"서버 오류: {str(e)}")

def create_error_response(message):
    """에러 응답 생성"""
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"⚠️ {message}\n잠시 후 다시 시도해주세요."
                }
            }]
        }
    }), 200  # 카카오는 200을 기대함

@app.route('/health', methods=['GET'])
def health():
    """헬스체크"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "kakao-exchange-rate-skill"
    })

@app.route('/', methods=['GET'])
def index():
    """기본 페이지"""
    return """
    <h1>카카오톡 환율 스킬 서버</h1>
    <p>상태: 정상 작동중</p>
    <p>엔드포인트: POST /exchange_rate</p>
    <p>헬스체크: GET /health</p>
    """

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 카카오톡 환율 스킬 서버 시작")
    print("=" * 60)
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📍 엔드포인트:")
    print("   - POST /exchange_rate (카카오톡 스킬)")
    print("   - GET /health (헬스체크)")
    print("   - GET / (정보 페이지)")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
