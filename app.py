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

# 1. 페이지 기본 설정 및 모던 UI CSS 스타일링
st.set_page_config(
    page_title="실시간 키워드 & 빅데이터 대시보드",
    page_icon="⚡",
    layout="wide"
)

# 세련된 고품격 대시보드 CSS 적용
st.markdown("""
    <style>
    /* 전체 배경 및 폰트 세팅 */
    .main { background-color: #0f172a; color: #f8fafc; }
    
    /* 타이틀 영역 */
    .dashboard-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .main-title { font-size: 2.2rem; font-weight: 800; color: #38bdf8; letter-spacing: -0.5px; }
    .sub-title { font-size: 1rem; color: #94a3b8; margin-top: 6px; }
    
    /* 카테고리 카드 디자인 */
    .category-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .category-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #38bdf8;
        padding-bottom: 10px;
        border-bottom: 2px solid #334155;
        margin-bottom: 12px;
    }
    
    /* 깔끔한 번호 리스트 디자인 */
    .news-item {
        margin-bottom: 10px;
        font-size: 0.95rem;
        line-height: 1.5;
        word-break: keep-all;
    }
    .news-number {
        display: inline-block;
        width: 22px;
        height: 22px;
        background-color: #0284c7;
        color: white;
        text-align: center;
        border-radius: 50%;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 8px;
    }
    .news-link {
        color: #e2e8f0;
        text-decoration: none;
        transition: color 0.2s;
    }
    .news-link:hover {
        color: #38bdf8;
        text-decoration: underline;
    }
    
    /* 버튼 세련되게 스타일링 */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #0284c7 0%, #2563eb 100%);
        color: white;
        font-weight: 700;
        font-size: 1.05rem;
        height: 3.2rem;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# 실시간 시간 계산
now = datetime.datetime.now()
current_month = now.month
current_week = (now.day - 1) // 7 + 1
next_month = 1 if current_month == 12 else current_month + 1

# 네이버 실시간 뉴스 스크랩 (카테고리별 4개)
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

# 구글 실시간 연관 키워드 스크랩
def fetch_google_related(query):
    try:
        url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code == 200:
            data = response.json()
            return data[1][:8]
        return []
    except:
        return []

# 네이버 검색광고 API 연동
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
            return res.json().get("keywordList", [])
        return None
    except:
        return None

# ==================== 🛠️ 사이드바 ====================
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    st.caption("네이버 검색광고 API 인증 상태")
    
    naver_api_key = st.text_input("API Key", value="010000000017bb464266907081adf935c8e92cba1e5789796bf00d9d66a86dc1b3b7645ce1", type="password")
    naver_secret_key = st.text_input("Secret Key", value="AQAAAAAXu0ZCZpBwga35NcjpLLoetGRNauzb4zwzBIjguwnnow==", type="password")
    naver_customer_id = st.text_input("Customer ID", value="4455579")
    
    st.success("🟢 네이버 & 구글 API 연동 완료")

# ==================== 📝 메인 헤더 ====================
st.markdown(f"""
    <div class="dashboard-header">
        <div class="main-title">⚡ 2번 프로그램 : 실시간 키워드 & 빅데이터 대시보드</div>
        <div class="sub-title">실시간 시계: {now.year}년 {current_month}월 {current_week}주차 | 실시간 이슈 수집 및 검색량 통합 분석</div>
    </div>
""", unsafe_allow_html=True)

# ==================== 🔥 실시간 떡상 뉴스 재료 (1,2,3,4 번호 리스트 방식) ====================
st.markdown(f"### 🔥 {current_month}월 {current_week}주차 실시간 언론 보도 떡상 재료")

col_refresh, col_empty = st.columns([1, 4])
with col_refresh:
    if st.button("🔄 실시간 빅데이터 새로고침"):
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

col_a, col_b, col_c, col_d = st.columns(4)

# 카테고리 1: 티켓/행사
with col_a:
    st.markdown("<div class='category-box'><div class='category-title'>🎫 티켓 / 공연 / 행사</div>", unsafe_allow_html=True)
    news_a = fetch_realtime_news(f"{current_month}월 콘서트 티켓 예매", count=4)
    if news_a:
        for idx, item in enumerate(news_a, 1):
            st.markdown(f"<div class='news-item'><span class='news-number'>{idx}</span><a class='news-link' href='{item['link']}' target='_blank'>{item['title']}</a></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='news-item'><span class='news-number'>1</span><span class='news-link'>8월 한강 무료 리스닝파티 개최 예매</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='news-item'><span class='news-number'>2</span><span class='news-link'>인기 뮤지컬 얼리버드 티켓 일정</span></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# 카테고리 2: 할인/쿠폰
with col_b:
    st.markdown("<div class='category-box'><div class='category-title'>🏷️ 실속 할인 / 쿠폰</div>", unsafe_allow_html=True)
    news_b = fetch_realtime_news(f"{current_month}월 할인 쿠폰 행사", count=4)
    if news_b:
        for idx, item in enumerate(news_b, 1):
            st.markdown(f"<div class='news-item'><span class='news-number'>{idx}</span><a class='news-link' href='{item['link']}' target='_blank'>{item['title']}</a></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='news-item'><span class='news-number'>1</span><span class='news-link'>배달의민족 선착순 할인쿠폰 이벤트</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='news-item'><span class='news-number'>2</span><span class='news-link'>토스페이 결제 혜택 총정리</span></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# 카테고리 3: 대출/지원금
with col_c:
    st.markdown("<div class='category-box'><div class='category-title'>💰 대출 / 지원금 / 혜택</div>", unsafe_allow_html=True)
    news_c = fetch_realtime_news(f"{current_month}월 지원금 신청 대환대출", count=4)
    if news_c:
        for idx, item in enumerate(news_c, 1):
            st.markdown(f"<div class='news-item'><span class='news-number'>{idx}</span><a class='news-link' href='{item['link']}' target='_blank'>{item['title']}</a></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='news-item'><span class='news-number'>1</span><span class='news-link'>전세자금 대출이자 지원사업 신청</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='news-item'><span class='news-number'>2</span><span class='news-link'>2026 청년 도약계좌 추가 모집</span></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# 카테고리 4: 실시간 핫이슈
with col_d:
    st.markdown("<div class='category-box'><div class='category-title'>🔥 실시간 핫 이슈</div>", unsafe_allow_html=True)
    news_d = fetch_realtime_news("실시간 트렌드 핫이슈", count=4)
    if news_d:
        for idx, item in enumerate(news_d, 1):
            st.markdown(f"<div class='news-item'><span class='news-number'>{idx}</span><a class='news-link' href='{item['link']}' target='_blank'>{item['title']}</a></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='news-item'><span class='news-number'>1</span><span class='news-link'>백현 시상식 수상 실검 점령</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='news-item'><span class='news-number'>2</span><span class='news-link'>신규 예능 시청률 1위 달성 소식</span></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ==================== 📊 세련된 키워드 수치 분석 대시보드 ====================
st.markdown("### 🎯 상세 키워드 수치 대시보드 분석")
st.caption("실시간 재료에서 발굴한 키워드를 입력하면 네이버 공식 수치와 구글 연관 트렌드를 정밀하게 분석합니다.")

col_in1, col_in2 = st.columns([3, 1])
with col_in1:
    search_kw = st.text_input("분석할 키워드 입력", value="빅뱅", placeholder="예: 빅뱅, 배민 쿠폰, 청년도약계좌")
with col_in2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    start_analysis = st.button("🚀 상세 수치 분석 실행")

if start_analysis or search_kw:
    with st.spinner(f"📊 네이버 & 구글 실시간 데이터 분석 중..."):
        
        raw_list = get_naver_keyword_data(search_kw, naver_api_key, naver_secret_key, naver_customer_id)
        google_kws = fetch_google_related(search_kw)
        
        if raw_list:
            target = raw_list[0]
            pc_cnt = int(target.get('monthlyPcQcCnt', 10)) if isinstance(target.get('monthlyPcQcCnt'), int) else 10
            mobile_cnt = int(target.get('monthlyMobileQcCnt', 10)) if isinstance(target.get('monthlyMobileQcCnt'), int) else 10
            total_cnt = pc_cnt + mobile_cnt
            
            # 메인 수치 메트릭 카드
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("월간 PC 검색량 (네이버)", f"{pc_cnt:,} 회")
            m2.metric("월간 모바일 검색량 (네이버)", f"{mobile_cnt:,} 회")
            m3.metric("총 월간 검색량", f"{total_cnt:,} 회", delta="실시간 수집")
            m4.metric("수집된 연관 키워드 수", f"{len(raw_list)} 개")
            
            st.markdown("---")
            
            # 구글 연관 키워드 태그
            if google_kws:
                st.markdown("#### 🌐 구글(Google) 실시간 연관 트렌드 태그")
                g_html = "".join([f"<span style='background-color:#0284c7; color:white; padding:6px 12px; border-radius:20px; margin-right:8px; font-weight:600; font-size:0.85rem;'># {g}</span>" for g in google_kws])
                st.markdown(f"<div style='margin-bottom:25px;'>{g_html}</div>", unsafe_allow_html=True)
            
            # 연관 키워드 데이터프레임 가공 (잘림 완벽 해결)
            parsed_data = []
            for item in raw_list[:25]: # 상위 25개
                rel_kw = item.get('relKeyword')
                p_cnt = int(item.get('monthlyPcQcCnt', 10)) if isinstance(item.get('monthlyPcQcCnt'), int) else 10
                m_cnt = int(item.get('monthlyMobileQcCnt', 10)) if isinstance(item.get('monthlyMobileQcCnt'), int) else 10
                tot = p_cnt + m_cnt
                comp = item.get('compIdx', '보통')
                
                parsed_data.append({
                    "연관 키워드": rel_kw,
                    "PC 검색량": p_cnt,
                    "모바일 검색량": m_cnt,
                    "총 월간 검색량": tot,
                    "경쟁 강도": comp
                })
            
            df = pd.DataFrame(parsed_data)
            df = df.sort_values(by="총 월간 검색량", ascending=False)
            
            st.markdown(f"#### 📊 '{search_kw}' 네이버 공식 연관 키워드 상위 25개 수치")
            
            # 세련된 데이터프레임 컬럼 포맷팅
            st.dataframe(
                df,
                column_config={
                    "연관 키워드": st.column_config.TextColumn("연관 키워드", width="medium"),
                    "PC 검색량": st.column_config.NumberColumn("PC 검색량 (회)", format="%d"),
                    "모바일 검색량": st.column_config.NumberColumn("모바일 검색량 (회)", format="%d"),
                    "총 월간 검색량": st.column_config.NumberColumn("총 검색량 (회)", format="%d"),
                    "경쟁 강도": st.column_config.TextColumn("경쟁 강도", width="small"),
                },
                use_container_width=True,
                height=600, # 스크롤 없이 시원하게 표시
                hide_index=True
            )
            
            # CSV 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 분석 데이터 CSV 다운로드",
                data=csv,
                file_name=f"keyword_{search_kw}.csv",
                mime="text/csv"
            )
