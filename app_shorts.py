import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime, timedelta
import re
import requests
import json
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
import edge_tts

# ---------------------------------------------------------
# 1. 페이지 기본 설정 & 모던 UI CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="어비 스타일 AI 크리에이터 스튜디오",
    page_icon="🚀",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 28px;
        font-weight: 800;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 15px;
        color: #888888;
        text-align: center;
        margin-bottom: 25px;
    }
    .card-box {
        background-color: #1E1E2E;
        border-radius: 12px;
        padding: 18px;
        border: 1px solid #313244;
        margin-bottom: 15px;
    }
    .viral-badge {
        background-color: #FF4B4B;
        color: white;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-header'>🚀 AI 크리에이터 올인원 스튜디오</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>실시간 인기급상승 동영상 분석 ➔ 내 채널 맞춤 대본 ➔ 무료 TTS & 썸네일 자동화</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 사이드바 - 설정 및 API 키 관리
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 스튜디오 환경 설정")
    
    # YouTube API Key
    DEFAULT_YT_KEY = "" # 자주 쓰는 유튜브 키가 있다면 여기에 넣으세요
    youtube_api_key = st.text_input("🔑 YouTube API Key", value=DEFAULT_YT_KEY, type="password")
    
    # Gemini API Key
    DEFAULT_GEMINI_KEY = "" # 자주 쓰는 제미나이 키가 있다면 여기에 넣으세요
    gemini_api_key = st.text_input("🔮 Google Gemini API Key", value=DEFAULT_GEMINI_KEY, type="password")
    
    st.divider()
    
    # 내 채널 페르소나 세팅
    st.subheader("👤 내 채널 페르소나 연동")
    my_channel_name = st.text_input("채널명 / 크리에이터 닉네임", value="어비월드")
    my_channel_style = st.text_selectbox if hasattr(st, 'text_selectbox') else st.selectbox(
        "채널 주 말투/톤앤매너",
        ["친근하고 전문적인 설명조 (~입니다/해볼게요)", "빠르고 흥미진진한 쇼츠 텐션 (~했는데요! 실화냐?)", "차분하고 지적인 정보 전달조", "유머러스하고 재치있는 어조"]
    )
    my_main_topic = st.text_input("주요 카테고리/주제", value="IT/AI 신기술 리뷰 & 꿀팁")

# ---------------------------------------------------------
# 3. Helper 함수 (YouTube API / Gemini API / TTS)
# ---------------------------------------------------------
def get_channel_subscribers(youtube, channel_ids):
    if not channel_ids:
        return {}
    channel_ids = list(set(channel_ids))
    sub_map = {}
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i+50]
        res = youtube.channels().list(part="statistics", id=",".join(chunk)).execute()
        for item in res.get("items", []):
            sub_map[item["id"]] = int(item["statistics"].get("subscriberCount", 1))
    return sub_map

def generate_gemini_text(api_key, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            result = res.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            # Fallback to gemini-1.5-flash
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
            res_fb = requests.post(fallback_url, headers=headers, json=payload, timeout=30)
            if res_fb.status_code == 200:
                return res_fb.json()['candidates'][0]['content']['parts'][0]['text']
            return f"❌ AI 생성 실패 (오류 코드: {res.status_code}): {res.text}"
    except Exception as e:
        return f"❌ 통신 오류 발생: {e}"

async def text_to_speech_edge(text, voice="ko-KR-SunHiNeural", output_file="speech.mp3"):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def create_thumbnail_image(title_text, category_text):
    img = Image.new('RGB', (1280, 720), color=(24, 24, 37))
    draw = ImageDraw.Draw(img)
    
    # 상단 카테고리 테두리 박스
    draw.rectangle([80, 100, 380, 160], fill=(255, 75, 75))
    draw.text((100, 115), category_text, fill=(255, 255, 255))
    
    # 메인 타이틀 (줄바꿈 처리)
    lines = [title_text[i:i+12] for i in range(0, len(title_text), 12)]
    y_offset = 260
    for line in lines[:3]:
        draw.text((80, y_offset), line, fill=(255, 255, 255))
        y_offset += 100
        
    draw.text((80, 600), "🔥 지금 바로 확인하세요!", fill=(255, 215, 0))
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

# ---------------------------------------------------------
# 4. 메인 대시보드 탭 구획
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 인급동 떡상 스튜디오", "🎙️ AI 대본 & 무료 TTS / 썸네일", "✂️ CapCut 연동 / 영상 분석"])

# =========================================================
# TAB 1: 인급동 떡상 스튜디오 (Viral Score 분석)
# =========================================================
with tab1:
    st.subheader("🔥 실시간 급상승 & 떡상 배수(Viral Score) 분석기")
    st.caption("단순 조회수가 아닌, 해당 채널의 평균 구독자 체급 대비 얼마나 폭발(떡상)했는지 정밀 추적합니다.")
    
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        country_code = st.selectbox("🌍 대상 국가", ["대한민국 (KR)", "미국 (US)", "일본 (JP)", "인도 (IN)"], index=0)
        c_code = country_code.split("(")[1].replace(")", "").strip()
    with col_b:
        video_type = st.radio("🎬 영상 타입", ["쇼츠 (Shorts)", "롱폼 (Long-form)"], horizontal=True)
    with col_c:
        time_frame = st.selectbox("📅 게시 타임라인", ["최근 24시간 이내", "최근 3일 이내", "최근 7일 이내"], index=1)
        days_map = {"최근 24시간 이내": 1, "최근 3일 이내": 3, "최근 7일 이내": 7}
        
    btn_fetch = st.button("🚀 실시간 떡상 콘텐츠 및 트렌드 수집")
    
    if btn_fetch:
        if not youtube_api_key:
            st.error("⚠️ 왼쪽 사이드바에 YouTube API Key를 먼저 입력해 주세요!")
        else:
            try:
                youtube = build('youtube', 'v3', developerKey=youtube_api_key)
                with st.spinner("🔍 실시간 유튜브 인급동 알고리즘 분석 중..."):
                    pub_after = (datetime.utcnow() - timedelta(days=days_map[time_frame])).strftime('%Y-%m-%dT%H:%M:%SZ')
                    
                    # 1. 인기 급상승 수집
                    dur_param = "short" if "쇼츠" in video_type else "medium"
                    
                    search_res = youtube.search().list(
                        part="snippet",
                        type="video",
                        videoDuration=dur_param,
                        order="viewCount",
                        publishedAfter=pub_after,
                        regionCode=c_code,
                        maxResults=40
                    ).execute()
                    
                    v_ids = [item['id']['videoId'] for item in search_res.get('items', []) if 'videoId' in item['id']]
                    
                    if v_ids:
                        v_details = youtube.videos().list(part="snippet,statistics", id=",".join(v_ids)).execute()
                        c_ids = [v['snippet']['channelId'] for v in v_details.get('items', [])]
                        sub_map = get_channel_subscribers(youtube, c_ids)
                        
                        viral_results = []
                        for v in v_details.get('items', []):
                            v_id = v['id']
                            snippet = v['snippet']
                            stats = v['statistics']
                            
                            views = int(stats.get('viewCount', 0))
                            c_id = snippet['channelId']
                            subs = sub_map.get(c_id, 1)
                            
                            # 떡상 배수 계산 (Viral Score = 조회수 / 구독자 수)
                            viral_ratio = round(views / subs, 2) if subs > 0 else 0
                            
                            viral_results.append({
                                'v_id': v_id,
                                'title': snippet['title'],
                                'channel': snippet['channelTitle'],
                                'views': views,
                                'subs': subs,
                                'viral_ratio': viral_ratio,
                                'thumb': snippet['thumbnails'].get('medium', {}).get('url', ''),
                                'published': snippet['publishedAt'][:10]
                            })
                        
                        # 떡상 배수 순 정렬
                        viral_results = sorted(viral_results, key=lambda x: x['viral_ratio'], reverse=True)
                        st.session_state['viral_results'] = viral_results
                        st.success(f"✅ 총 {len(viral_results)}개의 실시간 떡상 영상을 성공적으로 추출했습니다!")
            except Exception as e:
                st.error(f"❌ 데이터 수집 중 오류가 발생했습니다: {e}")

    # 결과 표출
    if 'viral_results' in st.session_state:
        st.divider()
        st.subheader("🏆 [떡상 배수 순] 실시간 인급동 랭킹 Top 10")
        
        for idx, item in enumerate(st.session_state['viral_results'][:10], start=1):
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    if item['thumb']:
                        st.image(item['thumb'], use_container_width=True)
                with col2:
                    st.markdown(f"#### {idx}위. {item['title']}")
                    st.markdown(f"📺 **채널**: {item['channel']} | 👥 **구독자**: {item['subs']:,}명 | 🔥 **조회수**: {item['views']:,}회")
                    st.markdown(f"⚡ **떡상 배수**: <span class='viral-badge'>체급 대비 x{item['viral_ratio']}배 떡상!</span>", unsafe_allow_html=True)
                    st.markdown(f"👉 [유튜브에서 영상 보기](https://www.youtube.com/watch?v={item['v_id']})")
                st.divider()

# =========================================================
# TAB 2: AI 대본 & 무료 TTS / 썸네일 생성기
# =========================================================
with tab2:
    st.subheader("🔮 내 채널 맞춤 AI 대본 & 무료 TTS/썸네일 결합기")
    st.caption("실시간 트렌드 주제와 내 채널 페르소나를 합성하여 즉시 촬영/편집 가능한 대본과 음성을 생성합니다.")
    
    topic_input = st.text_input("💡 포스팅/영상으로 만들 주제 입력", value="2026년 AI 신기술로 방구석에서 월 500만 원 버는 자동화 시스템")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        script_format = st.radio("포맷 선택", ["쇼츠 대본 (60초 규격)", "롱폼 대본 (3분~5분 규격)"], horizontal=True)
    with col_d2:
        include_tts = st.checkbox("🎙️ 대본 생성 후 무료 AI 나레이션(TTS) 파일 자동 추출", value=True)
        
    btn_make_script = st.button("✨ 내 말투가 적용된 원클릭 대본 생성")
    
    if btn_make_script:
        if not gemini_api_key:
            st.error("⚠️ 왼쪽 사이드바에 Google Gemini API Key를 입력해 주세요!")
        else:
            prompt = f"""
            당신은 구독자 270만 유튜버이자 AI 콘텐츠 전문가입니다.
            다음 조건에 따라 유튜브 대본을 작성하세요.

            [크리에이터 페르소나]
            - 채널명: {my_channel_name}
            - 말투/톤앤매너: {my_channel_style}
            - 주요 카테고리: {my_main_topic}

            [제작 주제]
            - 주제: {topic_input}
            - 포맷: {script_format}

            [대본 작성 지침]
            1. 오프닝: 시청자의 시선을 3초 만에 사로잡는 강력한 후킹 문구 (내 채널 시그니처 인사말 포함)
            2. 본론: 3가지 핵심 꿀팁/핵심 내용으로 명확히 구분
            3. 클로징: 구독과 좋아요를 유도하는 마무리 인사
            4. 지문 표기: 화면에 띄울 자막 코멘트 및 화면 전환 연출 지시어 [예: (화면자막: ~)] 포함
            """
            
            with st.spinner("🧠 내 채널 말투를 학습하여 오프닝부터 클로징까지 맞춤 대본 작성 중..."):
                script_result = generate_gemini_text(gemini_api_key, prompt)
                st.session_state['generated_script'] = script_result
                st.success("🎉 내 채널 전용 맞춤 대본 작성이 완료되었습니다!")

    if 'generated_script' in st.session_state:
        st.subheader("📄 생성된 원클릭 대본")
        st.text_area("대본 내용 (복사 가능)", value=st.session_state['generated_script'], height=350)
        
        # TTS 자동 변환 및 다운로드
        if include_tts:
            st.subheader("🎙️ Edge-TTS 기반 무료 AI 나레이션 음성 파일")
            with st.spinner("🎧 AI 나레이션 음성을 생성하는 중입니다..."):
                # 지문 특수문자 제거 후 순수 텍스트만 추출
                clean_text = re.sub(r'\[.*?\]|\(.*?\)', '', st.session_state['generated_script'])
                clean_text = clean_text.replace('\n', ' ')[:500] # 슬라이싱 안전장치
                
                asyncio.run(text_to_speech_edge(clean_text, voice="ko-KR-SunHiNeural", output_file="speech.mp3"))
                
                audio_file = open('speech.mp3', 'rb')
                audio_bytes = audio_file.read()
                st.audio(audio_bytes, format='audio/mp3')
                st.download_button("💾 음성 파일 다운로드 (.mp3)", data=audio_bytes, file_name="script_speech.mp3", mime="audio/mp3")

        st.divider()
        st.subheader("🎨 맞춤형 대표 썸네일 이미지 제작")
        thumb_bytes = create_thumbnail_image(topic_input, my_main_topic)
        st.image(thumb_bytes, caption="실시간 생성된 고화질 블로그/유튜브 대표 썸네일", width=500)
        st.download_button("🖼️ 썸네일 이미지 다운로드 (.png)", data=thumb_bytes, file_name="thumbnail.png", mime="image/png")

# =========================================================
# TAB 3: CapCut 연동 & 영상 URL 분석기
# =========================================================
with tab3:
    st.subheader("✂️ CapCut(캡컷) 자동 편집 & 타사 영상 분석 스튜디오")
    st.caption("타사 영상 URL을 넣으면 AI가 타임라인 구조를 정밀 분석해주며, 캡컷 프로젝트 연동 가이드를 제공합니다.")
    
    target_url = st.text_input("🔗 분석할 타깃 유튜브 영상 URL", value="https://www.youtube.com/watch?v=c8fMl6Oqle4")
    
    if st.button("🔎 타깃 영상 구조 및 떡상 요소 AI 정밀 분석"):
        if not gemini_api_key:
            st.error("⚠️ 왼쪽 사이드바에 Google Gemini API Key를 입력해 주세요!")
        else:
            prompt_analyze = f"""
            다음 유튜브 영상 URL({target_url})에 대해 시청률을 극대화한 구조 분석 보고서를 작성하세요.
            1. 예상 썸네일 및 카피 문구 전략
            2. 초반 5초 후킹 방식 분석
            3. 영상의 전개 구조 (서론-본론-결론 타임라인 분석)
            4. 우리가 벤치마킹하여 적용할 수 있는 3가지 떡상 포인트
            """
            with st.spinner("📊 타깃 영상 알고리즘 구조 파싱 중..."):
                analysis_res = generate_gemini_text(gemini_api_key, prompt_analyze)
                st.markdown(analysis_res)

    st.divider()
    st.subheader("🎬 CapCut(캡컷) 자동 편집 프로젝트(.draft) 연동 안내")
    st.info("""
    **💡 1초 만에 CapCut 자동 자막/편집 프로젝트 만드는 원리:**
    1. 위의 **[Tab 2]**에서 추출한 `.mp3` 음성 파일과 생성된 썸네일 이미지를 다운로드합니다.
    2. CapCut PC 프로그램을 실행하고 **[음성 자막 자동 생성 (Auto Captions)]** 기능 버튼을 클릭합니다.
    3. AI 나레이션 속도에 맞춰 자막 위치와 텍스트 스타일이 1초 만에 100% 자동으로 정렬 및 타임라인 생성 완료됩니다!
    """)
