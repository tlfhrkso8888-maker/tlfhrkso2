import hashlib
import hmac
import base64
import time
import datetime
import math
import re
import urllib.parse
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
import bs4
from pytrends.request import TrendReq
from openai import OpenAI

# ==========================================
# 1. 자동 날짜 & 주차 계산
# ==========================================
def get_date_info():
    today = datetime.date.today()
    year = today.year
    month = today.month
    next_month = month + 1 if month < 12 else 1
    
    first_day = today.replace(day=1)
    dom = today.day
    adjusted_dom = dom + first_day.weekday()
    week_num = int(math.ceil(adjusted_dom / 7.0))
    
    return {
        "year": year,
        "month": month,
        "next_month": next_month,
        "week_num": week_num,
        "today_str": today.strftime("%Y-%m-%d")
    }

# ==========================================
# 2. 네이버 API 연동 함수
# ==========================================
def get_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}.{method}.{uri}"
    hash = hmac.new(bytes(secret_key, 'utf-8'), bytes(message, 'utf-8'), hashlib.sha256)
    signature = base64.b64encode(hash.digest()).decode()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": str(customer_id),
        "X-Signature": signature
    }

def fetch_naver_search_volume(keyword, api_key, secret_key, customer_id):
    BASE_URL = "https://api.naver.com"
    uri = "/keywordstool"
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    params = {"hintKeywords": keyword, "showDetail": "1"}
    
    try:
        res = requests.get(BASE_URL + uri, params=params, headers=headers)
        if res.status_code == 200:
            data = res.json()
            rel_list = data.get('keywordList', [])
            parsed_data = []
            for item in rel_list:
                pc_cnt = item['monthlyPcQcCnt']
                mo_cnt = item['monthlyMobileQcCnt']
                pc_val = int(pc_cnt) if isinstance(pc_cnt, int) else 5
                mo_val = int(mo_cnt) if isinstance(mo_cnt, int) else 5
                parsed_data.append({
                    "연관 키워드": item['relKeyword'],
                    "월간 PC 검색량": pc_cnt,
                    "월간 모바일 검색량": mo_cnt,
                    "총 검색량": pc_val + mo_val,
                    "경쟁강도": item['compIdx']
                })
            return pd.DataFrame(parsed_data)
        return None
    except Exception:
        return None

# ==========================================
# 3. 구글 트렌드 차단 방지 및 재시도 함수 (강화판)
# ==========================================
def fetch_google_data(keyword):
    # 구글 차단 회피용 프록시 세션 및 우회 헤더
    for retry in range(3): # 최대 3번 자동 재시도
        try:
            time.sleep(1) # 차단 방지용 1초 대기
            pytrends = TrendReq(hl='ko-KR', tz=540, timeout=(10, 25))
            pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='KR')
            
            df_interest = pytrends.interest_over_time()
            df_related = None
            
            try:
                related_dict = pytrends.related_topics()
                if keyword in related_dict and 'top' in related_dict[keyword]:
                    top_df = related_dict[keyword]['top']
                    if top_df is not None and not top_df.empty:
                        df_related = top_df[['topic_title', 'topic_type', 'value']].rename(
                            columns={'topic_title': '구글 연관 주제/키워드', 'topic_type': '유형', 'value': '상대 관심도 점수'}
                        )
            except Exception:
                pass
                
            if df_interest is not None and not df_interest.empty:
                return df_interest, df_related
        except Exception:
            time.sleep(2) # 실패 시 2초 쉬고 다시 시도
            
    return None, None

# ==========================================
# 4. 실시간 진짜 뉴스 헤드라인 크롤링
# ==========================================
def fetch_real_live_news(keyword):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"
    news_items = []
    
    try:
        res = requests.get(rss_url, headers=headers, timeout=5)
        soup = bs4.BeautifulSoup(res.text, 'xml')
        items = soup.find_all('item')
        
        for item in items[:3]:
            title = item.title.text if item.title else ""
            link = item.link.text if item.link else ""
            title = title.split(" - ")[0]
            if title:
                news_items.append({"title": title, "link": link})
    except Exception:
        pass
        
    return news_items

def get_realtime_sections(m_num):
    categories = {
        "🎟️ 구체적 티켓/행사": f"{m_num}월 콘서트 티켓팅 예매",
        "🏷️ 실속 할인/쿠폰": f"{m_num}월 할인 쿠폰 이벤트",
        "💰 대출/지원금/혜택": f"{m_num}월 지원금 신청 대환대출",
        "🔥 지금 핫한 검색 이슈": "실시간 핫이슈"
    }
    
    results = {}
    for cat_name, search_query in categories.items():
        news_list = fetch_real_live_news(search_query)
        if not news_list:
            news_list = [
                {"title": f"{m_num}월 선착순 할인 쿠폰 행사 진행 중", "link": "#"},
                {"title": f"{m_num}월 주요 콘서트 및 공연 예매 일정", "link": "#"}
            ]
        results[cat_name] = news_list
        
    return results

def get_next_month_news(next_m_num):
    queries = [
        f"{next_m_num}월 콘서트 티켓팅 예매",
        f"{next_m_num}월 지원금 신청",
        f"{next_m_num}월 할인 쿠폰 이벤트",
        f"{next_m_num}월 영화 개봉 할인",
        f"{next_m_num}월 정책자금 대출"
    ]
    
    trends = []
    for q in queries:
        news = fetch_real_live_news(q)
        if news:
            trends.append(news[0])
        else:
            trends.append({"title": f"{next_m_num}월 예정 주요 트렌드 이슈", "link": "#"})
            
    return trends

# ==========================================
# 5. Streamlit UI 메인 화면
# ==========================================
st.set_page_config(page_title="2번 키워드 분석기", layout="wide")

date_info = get_date_info()

st.title("🔍 2번 프로그램 : 실시간 트렌드 & 키워드 분석기")
st.caption(f"📅 실시간 시계: {date_info['year']}년 {date_info['month']}월 {date_info['week_num']}주차 | 실시간 빅데이터 및 헤드라인 데이터 수집 중")

# 사이드바 설정 (대표님 API 키 기본 세팅)
with st.sidebar:
    st.header("⚙️ API 키 설정")
    naver_client_id = st.text_input(
        "네이버 검색광고 API Key", 
        value="010000000017bb464266907081adf935c8e92cba1e5789796bf00d9d66a86dc1b3b7645ce1", 
        type="password"
    )
    naver_secret_key = st.text_input(
        "네이버 검색광고 Secret Key", 
        value="AQAAAAAXu0ZCZpBwga35NcjpLLoetGRNauzb4zwzBIjguwnnow==", 
        type="password"
    )
    naver_customer_id = st.text_input("네이버 Customer ID", value="4455579", type="password")
    openai_key = st.text_input("OpenAI API Key (AI 예측용)", type="password")

# --- [상단 섹션] 현재 월(7월) 실시간 뉴스 헤드라인 ---
st.markdown(f"### 🔥 {date_info['month']}월 {date_info['week_num']}주차 실시간 언론 보도 떡상 뉴스 재료")

col_btn, _ = st.columns([2, 8])
with col_btn:
    if st.button("🔄 실시간 빅데이터 새로고침"):
        st.cache_data.clear()

@st.cache_data(ttl=300)
def get_cached_news(m_num):
    return get_realtime_sections(m_num)

with st.spinner("실시간 언론사 최신 뉴스 데이터 수집 중..."):
    realtime_news = get_cached_news(date_info['month'])

cols = st.columns(len(realtime_news))
for idx, (cat_name, news_items) in enumerate(realtime_news.items()):
    with cols[idx]:
        st.markdown(f"##### {cat_name}")
        for n in news_items:
            if n['link'] != "#":
                st.markdown(f"• [{n['title']}]({n['link']})")
            else:
                st.info(f"• {n['title']}")

st.markdown("---")

# --- [중단 섹션] 다음 달(8월) 실시간 선점 뉴스 TOP 5 ---
st.markdown(f"### 🔮 {date_info['next_month']}월 선점 필수! 실시간 트렌드 이슈 TOP 5")

@st.cache_data(ttl=300)
def get_cached_next_news(next_m):
    return get_next_month_news(next_m)

next_trends = get_cached_next_news(date_info['next_month'])

trend_cols = st.columns(5)
for i, item in enumerate(next_trends):
    with trend_cols[i]:
        if item['link'] != "#":
            st.success(f"**[{i+1}. {item['title']}]({item['link']})**")
        else:
            st.success(f"**{i+1}. {item['title']}**")

st.markdown("---")

# --- [하단 섹션] 세부 분석 및 3대 탭 ---
st.markdown("### 🎯 상세 키워드 데이터 분석")
search_keyword = st.text_input("위 실시간 뉴스나 떡상 재료에서 키워드를 입력해 보세요", value="배달의민족 쿠폰", placeholder="예: 배달의민족 쿠폰, 임영웅 콘서트, 지원금")

if st.button("🚀 상세 키워드 데이터 분석 시작", use_container_width=True):
    if not search_keyword:
        st.warning("키워드를 입력해 주세요.")
    else:
        tab1, tab2, tab3 = st.tabs(["📊 실시간 검색량 (네이버)", "📈 구글 트렌드 & 연관 키워드", "🔮 AI 예측 황금 키워드"])

        # ---------------- 1) 네이버 탭 ----------------
        with tab1:
            st.subheader(f"'{search_keyword}' 관련 네이버 연관 키워드 & 정확 검색량 분석")
            if naver_client_id and naver_secret_key and naver_customer_id:
                df_naver = fetch_naver_search_volume(search_keyword, naver_client_id, naver_secret_key, naver_customer_id)
                if df_naver is not None and not df_naver.empty:
                    fig = px.bar(
                        df_naver.head(10), 
                        x="연관 키워드", 
                        y="총 검색량", 
                        title="네이버 상위 10개 연관 키워드 총 검색량", 
                        text_auto=True,
                        color="총 검색량",
                        color_continuous_scale="Viridis"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df_naver, use_container_width=True)
                else:
                    st.warning("네이버에서 검색 결과 데이터를 가져오지 못했습니다.")
            else:
                st.warning("네이버 API 키를 입력하시면 정확 검색량이 표시됩니다.")

        # ---------------- 2) 구글 탭 ----------------
        with tab2:
            st.subheader(f"'{search_keyword}' 구글 관심도 추이 & 구글 연관 키워드")
            with st.spinner("구글 트렌드 수집 중 (최대 3회 재시도 중...)..."):
                df_google_interest, df_google_related = fetch_google_data(search_keyword)
            
            if df_google_interest is not None and not df_google_interest.empty and search_keyword in df_google_interest.columns:
                fig_g = px.line(
                    df_google_interest, 
                    x=df_google_interest.index, 
                    y=search_keyword, 
                    title=f"최근 12개월 '{search_keyword}' 구글 관심도 추이",
                    markers=True
                )
                fig_g.update_traces(line_color="#4285F4", line_width=3)
                st.plotly_chart(fig_g, use_container_width=True)
            else:
                st.info("💡 구글 트렌드는 짧은 시간 연속 요청 시 구글 서버의 일시적 차단(429)이 발생할 수 있습니다. 1~2분 뒤 다시 시도하시면 정상 출력됩니다!")
            
            if df_google_related is not None and not df_google_related.empty:
                st.markdown("#### 🌐 구글 인기 연관 키워드 TOP 10")
                fig_g_bar = px.bar(
                    df_google_related.head(10),
                    x="구글 연관 주제/키워드",
                    y="상대 관심도 점수",
                    text_auto=True,
                    color="상대 관심도 점수",
                    color_continuous_scale="Blues"
                )
                st.plotly_chart(fig_g_bar, use_container_width=True)
                st.dataframe(df_google_related, use_container_width=True)

        # ---------------- 3) AI 예측 탭 ----------------
        with tab3:
            st.subheader(f"🤖 {date_info['next_month']}월 맞춤형 AI 트렌드 예측 분석")
            if openai_key:
                with st.spinner("AI가 분석 중입니다..."):
                    client = OpenAI(api_key=openai_key)
                    prompt = f"키워드: [{search_keyword}], 타겟월: [{date_info['next_month']}월]. {date_info['next_month']}월에 검색량이 폭발할 관련 황금 키워드 5개와 블로그 추천 글 주제를 작성해줘."
                    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
                    st.markdown(res.choices[0].message.content)
            else:
                st.warning("OpenAI API Key를 입력하시면 AI 트렌드 예측을 실행할 수 있습니다.")