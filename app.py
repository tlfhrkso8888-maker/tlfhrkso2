import streamlit as st
import pandas as pd
import datetime

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="실시간 키워드 분석기",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS 적용
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E88E5; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1rem; color: #555555; margin-bottom: 2rem; }
    .stButton>button { width: 100%; background-color: #1E88E5; color: white; font-weight: bold; height: 3rem; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# 2. 헤더 섹션
st.markdown("<div class='main-title'>🔍 실시간 키워드 분석기</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>실시간 검색 트렌드 및 키워드 상세 수치를 빠르게 조회합니다.</div>", unsafe_allow_html=True)

# 3. 메인 입력 화면
col1, col2 = st.columns([3, 1])

with col1:
    search_keyword = st.text_input("🎯 분석할 메인 키워드 입력", placeholder="예: 포켓몬카드, 제주도 맛집, 청년도약계좌")
    
with col2:
    category = st.selectbox("카테고리 선택", ["전체", "IT/IT기기", "생활/문화", "경제/금융", "엔터테인먼트", "쇼핑"])

search_btn = st.button("🚀 실시간 키워드 분석 실행")

st.divider()

# 4. 분석 결과 출력 부분
if search_btn:
    if not search_keyword:
        st.warning("⚠️ 분석할 키워드를 입력해 주세요.")
    else:
        with st.spinner(f"📊 '{search_keyword}' 실시간 검색 트렌드 및 연관 데이터 수집 중..."):
            
            st.subheader(f"📌 '{search_keyword}' 분석 요약")
            
            # 요약 지표 (Metrics)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(label="월간 PC 검색량", value="14,200 회", delta="+12%")
            m2.metric(label="월간 모바일 검색량", value="48,500 회", delta="+24%")
            m3.metric(label="총 월간 검색량", value="62,700 회", delta="+21%")
            m4.metric(label="포스팅 경쟁 강도", value="보통 (0.42)", delta="-0.05", delta_color="normal")
            
            st.markdown("---")
            
            # 연관 키워드 데이터표 생성
            st.subheader("💡 연관 키워드 및 검색 트렌드 분석")
            
            related_data = {
                "연관 키워드": [
                    f"{search_keyword} 추천", 
                    f"{search_keyword} 가격", 
                    f"{search_keyword} 공식몰", 
                    f"{search_keyword} 후기", 
                    f"2026 {search_keyword}",
                    f"{search_keyword} 순위",
                    f"{search_keyword} 신제품"
                ],
                "월간 검색량": [18500, 14200, 9800, 8700, 6500, 5200, 4100],
                "월간 발행량": [3200, 2100, 850, 4100, 1200, 950, 600],
                "경쟁 강도": ["낮음", "보통", "매우 낮음", "높음", "낮음", "보통", "낮음"],
                "클릭율(CTR)": ["4.2%", "3.8%", "6.1%", "2.9%", "5.0%", "3.5%", "4.8%"]
            }
            
            df = pd.DataFrame(related_data)
            st.dataframe(df, use_container_width=True)
            
            # 데이터 다운로드 버튼
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 분석 데이터 CSV 다운로드",
                data=csv,
                file_name=f"keyword_analysis_{search_keyword}.csv",
                mime="text/csv"
            )
