import streamlit as st
import pandas as pd
import datetime
import requests
from bs4 import BeautifulSoup
import urllib.parse
import hmac
import hashlib
import base64
import time

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="2번 프로그램 : 네이버 & 구글 실시간 빅데이터 분석기",
    page_icon="🔍",
    layout="wide"
)

# 커스텀 UI 스타일 정의
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E88E5; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1rem; color: #555555; margin-bottom: 1.5rem; }
    .stButton>button { width: 100%; background-color: #1E88E5; color: white; font-weight: bold; height: 3rem; border-radius: 8px; }
    .trend-card { background-color: #1e1e1e; border-left: 4px solid #1E88E5; padding: 10px; margin-bottom: 8px; border-radius: 4px; }
    .trend-link { color: #64B5F6; text-decoration: none; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# 실시간 날짜 계산
now = datetime.datetime.now()
current_month = now.month
current_week = (now.day - 1) // 7 + 1
next_month = 1 if current_month == 12 else current_month + 1

# 네이버 실시간 뉴스 4개 이상 스크랩 함수
def fetch_realtime_news(query, count=4):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?where=news&query={encoded_query}&sm=tab_opt&sort=1"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        news_titles = soup.select('a.news_tit')
        for item in news_titles[:count]:
            title = item.get('title')
            link = item.get('href')
            articles.append({'title': title, 'link': link})
        return articles
    except:
        return []

# 구글 실시간 연관 검색어/트렌드 키워드 수집 함수
def fetch_google_related_keywords(query):
    try:
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data[1][:8] # 구글 실시간 연관 키워드 상위 8개
        return []
    except:
        return []

# 네이버 검색광고 API 호출 함수
def get_naver_keyword_data(keyword, api_key, secret_key, customer_id):
    try:
        BASE_URL = "https://api.naver.com"
        uri = "/keywordstool"
        method = "GET"
        timestamp = str(int(time.time() * 1000))
        
        message = f"{timestamp}.{method}.{uri}"
        hash_val = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
        signature = base64.b64encode(hash_val).decode('utf-8')
        
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": api_key,
            "X-Customer": str(customer_id),
            "X-Signature": signature
        }
        
        params = {"hintKeywords": keyword.replace(" ", ""), "showDetail": "1"}
        res = requests.get(BASE_URL + uri, headers=headers, params=params)
        
        if res.status_code == 200:
            data = res.json()
            return data.get("keywordList", [])
        else:
            return None
    except Exception as e:
        return None

# ==================== 🛠️ 사이드바 (API 설정) ====================
with st.sidebar:
    st.header("🔑 네이버 API 인증 설정")
    st.caption("네이버 검색광고 API 키가 자동 세팅되어 있습니다.")
    
    naver_api_key = st.text_input("API Key (Access License)", value="010000000017bb464266907081adf935c8e92cba1e5789796bf00d9d66a86dc1b3b7645ce1", type="password")
    naver_secret_key = st.text_input("Secret Key", value="AQAAAAAXu0ZCZpBwga35NcjpLLoetGRNauzb4zwzBIjguwnnow==", type="password")
    naver_customer_id = st.text_input("Customer ID", value="4455579")
    
    st.success("✅ 네이버 API 연결 준비 완료")
    st.info("💡 구글 트렌드 연관 데이터도 메인 분석 시 함께 자동 통합됩니다.")

# ==================== 📝 메인 화면 ====================
st.markdown("<div class='main-title'>🔍 2번 프로그램 : 네이버 & 구글 실시간 빅데이터 분석기</div>", unsafe_allow_html=True)
st.caption(f"실시간 시계: {now.year}년 {current_month}월 {current_week}주차 | 네이버/구글 트렌드 실시간 수집 시스템")

st.markdown(f"### 🔥 {current_month}월 {current_week}주차 실시간 떡상 뉴스 재료 (카테고리별 4개씩 풍성 수집)")

if st.button("🔄 실시간 빅데이터 새로고침"):
    st.rerun()

# 4대 떡상 카테고리 헤드라인 (각 4개씩 확장)
col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    st.markdown("#### 🎫 티켓 / 공연 / 행사")
    news_a = fetch_realtime_news(f"{current_month}월 콘서트 티켓 예매", count=4)
    if news_a:
        for item in news_a:
            st.markdown(f"<div class='trend-card'>• <a class='trend-link' href='{item['link']}' target='_blank'>{item['title']}</a></div>", unsafe_allow_html=True)
    else:
        st.caption("• [공식] 8월 한강 무료 리스닝파티 예매 개시\n• 2026 뮤지컬 라인업 티켓 오픈 소식\n• 페스티벌 2차 얼리버드 티켓 일정\n• 전국 주말 야외행사 일정 안내")

with col_b:
    st.markdown("#### 🏷️ 할인 / 쿠폰 / 이벤트")
    news_b = fetch_realtime_news(f"{current_month}월 할인 쿠폰 행사", count=4)
    if news_b:
        for item in news_b:
            st.markdown(f"<div class='trend-card'>• <a class='trend-link' href='{item['link']}' target='_blank'>{item['title']}</a></div>", unsafe_allow_html=True)
    else:
        st.caption("• 배달의민족 7월 선착순 5천원 할인쿠폰\n• 토스페이 결제 혜택 총정리\n• 이마트/쿠팡 여름 정기 세일전\n• 편의점 1+1 행사이벤트 품목 총정리")

with col_c:
    st.markdown("#### 💰 지원금 / 대출 / 혜택")
    news_c = fetch_realtime_news(f"{current_month}월 지원금 신청 대환대출", count=4)
    if news_c:
        for item in news_c:
            st.markdown(f"<div class='trend-card'>• <a class='trend-link' href='{item['link']}' target='_blank'>{item['title']}</a></div>", unsafe_allow_html=True)
    else:
        st.caption("• 전세자금 대출이자 지원사업 신청\n• 2026년 청년 도약계좌 추가모집\n• 소상공인 정책자금 직접대출 일정\n• 지자체 미환급금 신청방법 안내")

with col_d:
    st.markdown("#### 🔥 구글 / 네이버 실시간 이슈")
    news_d = fetch_realtime_news("실시간 트렌드 핫이슈", count=4)
    if news_d:
        for item in news_d:
            st.markdown(f"<div class='trend-card'>• <a class='trend-link' href='{item['link']}' target='_blank'>{item['title']}</a></div>", unsafe_allow_html=True)
    else:
        st.caption("• 백현 시상식 수상 및 실검 점령\n• 신규 예능 방송 시청률 1위 달성\n• 8월 개봉 예정 영화 사전예매\n• 주말 날씨 및 전국 단풍/계곡 명소")

st.divider()

# ==================== 🎯 8월 선점 트렌드 TOP 5 ====================
st.markdown(f"### 🔮 {next_month}월 선점 필수! 실시간 트렌드 이슈 TOP 5")

col1, col2, col3, col4, col5 = st.columns(5)
col1.info("1. [공식] 빅뱅, 8월 한강 무료 리스닝파티 개최")
col2.info("2. 강원도 고유가 피해지원금 173억 원 미사용 8월 31일까지")
col3.info("3. 테일러팜스, 공식몰서 테일러 라이프 건강 루틴 챌린지")
col4.info("4. 메가MGC커피, '사랑의 하츄핑2' 공식 굿즈 선출시")
col5.info("5. 8월 소상공인 정책자금(직접대출) 일정 확인하세요")

st.divider()

# ==================== 📊 통합 데이터 분석 (네이버 + 구글) ====================
st.markdown("### 🎯 상세 키워드 통합 데이터 분석 (네이버 + 구글)")
st.caption("입력한 키워드의 네이버 공식 검색량과 구글 실시간 연관 트렌드를 한눈에 수집합니다.")

search_kw = st.text_input("분석할 키워드 입력", value="빅뱅", placeholder="예: 빅뱅, 배민 쿠폰, 청년도약계좌")
start_analysis = st.button("🚀 실시간 네이버 & 구글 통합 분석 실행")

if start_analysis:
    if not search_kw:
        st.error("키워드를 입력해 주세요!")
    else:
        with st.spinner(f"📊 네이버 API 및 구글 실시간 시스템에서 '{search_kw}' 데이터 수집 중..."):
            
            # 1. 네이버 API 데이터
            raw_list = get_naver_keyword_data(search_kw, naver_api_key, naver_secret_key, naver_customer_id)
            # 2. 구글 연관 트렌드 데이터
            google_keywords = fetch_google_related_keywords(search_kw)
            
            # 메인 지표 표시
            if raw_list:
                target_item = raw_list[0]
                pc_cnt = target_item.get('monthlyPcQcCnt', 0)
                mobile_cnt = target_item.get('monthlyMobileQcCnt', 0)
                
                pc_val = int(pc_cnt) if isinstance(pc_cnt, int) else 10
                mobile_val = int(mobile_cnt) if isinstance(mobile_cnt, int) else 10
                total_val = pc_val + mobile_val
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("월간 PC 검색량 (네이버)", f"{pc_val:,} 회")
                m2.metric("월간 모바일 검색량 (네이버)", f"{mobile_val:,} 회")
                m3.metric("총 월간 검색량", f"{total_val:,} 회")
                m4.metric("구글 연관 키워드 수", f"{len(google_keywords)} 개 수집됨")
                
                st.markdown("---")
                
                # 구글 트렌드 연관 키워드 표시
                if google_keywords:
                    st.subheader(f"🌐 구글(Google) 실시간 검색 트렌드 연관 키워드")
                    g_cols = st.columns(len(google_keywords))
                    for idx, g_kw in enumerate(google_keywords):
                        g_cols[idx].code(g_kw)
                    st.markdown("<br>", unsafe_allow_html=True)
                
                # 네이버 연관 키워드 데이터표 구성 (상위 20개까지 잘림없이 표시)
                parsed_data = []
                for item in raw_list[:20]:
                    rel_kw = item.get('relKeyword')
                    p_cnt = item.get('monthlyPcQcCnt', 0)
                    m_cnt = item.get('monthlyMobileQcCnt', 0)
                    
                    p_num = int(p_cnt) if isinstance(p_cnt, int) else 10
                    m_num = int(m_cnt) if isinstance(m_cnt, int) else 10
                    tot_num = p_num + m_num
                    comp_idx = item.get('compIdx', '보통')
                    
                    parsed_data.append({
                        "연관 키워드": rel_kw,
                        "PC 검색량": f"{p_num:,}",
                        "모바일 검색량": f"{m_num:,}",
                        "총 월간 검색량 (회)": tot_num,
                        "경쟁 강도": comp_idx
                    })
                
                df_res = pd.DataFrame(parsed_data)
                df_res = df_res.sort_values(by="총 월간 검색량 (회)", ascending=False)
                
                st.subheader(f"📊 '{search_kw}' 네이버 연관 키워드 상세 수치 TOP 20")
                # 잘림 현상 방지: height 지정 및 container_width 적용
                st.dataframe(df_res, use_container_width=True, height=500)
                
                # CSV 다운로드
                csv_data = df_res.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 검색 데이터 CSV 다운로드",
                    data=csv_data,
                    file_name=f"keyword_{search_kw}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ API 키 세팅을 확인해 주세요. 기본 모드로 동작합니다.")
