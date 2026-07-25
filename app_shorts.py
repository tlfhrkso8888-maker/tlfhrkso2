import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re

# 페이지 기본 설정
st.set_page_config(
    page_title="유튜브 실시간 국가별 떡상 쇼츠 대시보드",
    page_icon="🔥",
    layout="wide"
)

# 커스텀 UI 스타일
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #FF0000;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        height: 3em;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔥 실시간 국가별 떡상 쇼츠 순위 대시보드")
st.caption("선택한 국가의 순수 현지 유튜버 쇼츠만 정밀 검증하여 실시간 순위대로 표출합니다.")

# 대표님의 기본 YouTube API Key 자동 세팅
DEFAULT_YOUTUBE_API_KEY = "AIzaSyAT-UjhI6JB4TaS1mPfUVw-uCln_7bnLQ4"

# 언어 검증 함수 (해외 낚시 영상 차단 및 현지 언어 적합성 판별)
def is_valid_language(text, lang_code):
    if lang_code == "ko":
        # 완성된 한글(가-힣) 포함 여부 검사
        return bool(re.search(r'[가-힣]', text))
    elif lang_code == "ja":
        # 히라가나/가타카나 포함 여부 검사
        return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text))
    elif lang_code == "vi":
        # 베트남어 특수 문자 포함 여부 검사
        return bool(re.search(r'[àáâãèéêìíòóôõùúýàáảãạầấẩẫậềếểễệỉịỏóổỗộởỡờớợủúủứừứựỳỵỷỹ]', text, re.IGNORECASE))
    elif lang_code == "hi":
        # 힌디어 데바나가리 문자(\u0900-\u097F) 또는 영문(Hinglish) 포함 검사
        return bool(re.search(r'[\u0900-\u097Fa-zA-Z]', text))
    return True

# ==================== 🛠️ 사이드바 ====================
with st.sidebar:
    st.header("⚙️ 분석 조건 설정")
    
    # 1. API 키 입력 (기본값으로 대표님 Key 자동 채움)
    api_key = st.text_input(
        "🔑 YouTube API Key", 
        value=DEFAULT_YOUTUBE_API_KEY, 
        type="password", 
        help="자동으로 설정된 API 키입니다."
    )
    
    st.divider()
    
    # 2. 국가별 언어 및 검색 키워드 타겟팅 설정
    country_config = {
        "대한민국 🇰🇷": {
            "region": "KR", "lang": "ko", 
            "keywords": ["쇼츠", "떡상", "일상", "리뷰", "유머", "꿀팁"]
        },
        "미국 🇺🇸": {
            "region": "US", "lang": "en", 
            "keywords": ["viral shorts", "trending shorts", "funny shorts", "hacks"]
        },
        "일본 🇯🇵": {
            "region": "JP", "lang": "ja", 
            "keywords": ["ショート", "バズ", "おすすめ", "日常"]
        },
        "인도 🇮🇳": {
            "region": "IN", "lang": "hi",
            "keywords": ["shorts", "viral shorts", "trending shorts", "comedy shorts", "funny"]
        },
        "영국 🇬🇧": {
            "region": "GB", "lang": "en", 
            "keywords": ["uk shorts", "viral shorts", "trending"]
        },
        "베트남 🇻🇳": {
            "region": "VN", "lang": "vi", 
            "keywords": ["shorts hài", "xu hướng", "review"]
        }
    }
    
    selected_country_label = st.selectbox("🌍 국가 선택", list(country_config.keys()))
    c_info = country_config[selected_country_label]
    
    # 3. 수량 선택 (기본 20위)
    target_count = st.slider("🏆 수집 상위 순위 (TOP N개)", min_value=5, max_value=50, value=20, step=5)
    
    # 4. 최근 기간 선택
    period_days = st.selectbox("📅 게시 기간 (최근 N일 이내)", [3, 7, 14, 30], index=1)
    
    # 5. 구독자 수 구간 선택
    sub_filter = st.selectbox(
        "👥 채널 구독자 수 구간",
        ["전체 채널 (모두 보기)", "1만 명 미만 (초기 떡상 채널)", "1만 ~ 10만 명", "10만 ~ 100만 명", "100만 명 이상 (메가 채널)"]
    )
    
    st.divider()
    
    search_button = st.button("🚀 실시간 인기 쇼츠 순위 불러오기")

# ==================== 📊 데이터 수집 로직 ====================

def get_channel_subscriber_count(youtube, channel_ids):
    if not channel_ids:
        return {}
    channel_ids = list(set(channel_ids))
    channel_sub_map = {}
    
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i+50]
        res = youtube.channels().list(
            part="statistics",
            id=",".join(chunk)
        ).execute()
        
        for item in res.get("items", []):
            c_id = item["id"]
            sub_count = int(item["statistics"].get("subscriberCount", 0))
            channel_sub_map[c_id] = sub_count
            
    return channel_sub_map

def filter_by_subscribers(sub_count, filter_type):
    if filter_type == "1만 명 미만 (초기 떡상 채널)":
        return sub_count < 10000
    elif filter_type == "1만 ~ 10만 명":
        return 10000 <= sub_count < 100000
    elif filter_type == "100만 명 이상 (메가 채널)":
        return sub_count >= 1000000
    elif filter_type == "10만 ~ 100만 명":
        return 100000 <= sub_count < 1000000
    return True

if search_button:
    if not api_key:
        st.error("⚠️ 왼쪽 사이드바에 YouTube API Key를 입력해 주세요!")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            with st.spinner(f"🚀 {selected_country_label} (최근 {period_days}일 이내) 현지 쇼츠 TOP {target_count} 분석 중..."):
                
                published_after = (datetime.utcnow() - timedelta(days=period_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
                raw_items = []
                
                # 해당 국가 현지 전용 키워드로 타겟 수집
                for kw in c_info["keywords"]:
                    if len(raw_items) >= 200:
                        break
                    s_res = youtube.search().list(
                        part="snippet",
                        q=kw,
                        type="video",
                        videoDuration="short",
                        order="viewCount",
                        publishedAfter=published_after,
                        regionCode=c_info["region"],
                        relevanceLanguage=c_info["lang"],
                        maxResults=50
                    ).execute()
                    
                    add_ids = [s_item['id']['videoId'] for s_item in s_res.get("items", []) if 'videoId' in s_item['id']]
                    if add_ids:
                        add_v_res = youtube.videos().list(
                            part="snippet,statistics,contentDetails",
                            id=",".join(add_ids)
                        ).execute()
                        raw_items.extend(add_v_res.get("items", []))

                # 채널 정보 및 구독자 수 조회
                channel_ids = [v['snippet']['channelId'] for v in raw_items if 'snippet' in v and 'channelId' in v['snippet']]
                channel_sub_map = get_channel_subscriber_count(youtube, channel_ids)
                
                results = []
                seen_ids = set()
                
                for v in raw_items:
                    v_id = v['id']
                    if v_id in seen_ids:
                        continue
                    
                    snippet = v.get('snippet', {})
                    stats = v.get('statistics', {})
                    content_details = v.get('contentDetails', {})
                    
                    title = snippet.get('title', '')
                    channel_title = snippet.get('channelTitle', '')
                    
                    # 언어 정밀 검증
                    if not is_valid_language(title + channel_title, c_info["lang"]):
                        continue
                    
                    # 60초 이하 쇼츠 필터링 (PT1M 이하)
                    duration = content_details.get("duration", "")
                    if "M" in duration and duration != "PT1M":
                        continue
                        
                    channel_id = snippet.get('channelId', '')
                    sub_count = channel_sub_map.get(channel_id, 0)
                    
                    # 구독자 조건 필터링
                    if filter_by_subscribers(sub_count, sub_filter):
                        seen_ids.add(v_id)
                        pub_at = snippet.get('publishedAt', '')[:10]
                        
                        thumbs = snippet.get('thumbnails', {})
                        thumb_url = thumbs.get('medium', {}).get('url', thumbs.get('default', {}).get('url', ''))
                        
                        view_count = int(stats.get('viewCount', 0))
                        like_count = int(stats.get('likeCount', 0))
                        
                        results.append({
                            "v_id": v_id,
                            "썸네일": thumb_url,
                            "제목": title,
                            "채널명": channel_title,
                            "조회수": view_count,
                            "좋아요 수": like_count,
                            "구독자 수": sub_count,
                            "게시일": pub_at,
                            "링크": f"https://www.youtube.com/shorts/{v_id}"
                        })

                # 조회수 순 정렬 후 TOP N개 추출
                results = sorted(results, key=lambda x: x['조회수'], reverse=True)[:target_count]
                
                if not results:
                    st.warning("⚠️ 선택하신 조건에 맞는 현지 쇼츠가 없습니다. '채널 구독자 수 구간'을 '전체 채널 (모두 보기)'로 변경해 보세요!")
                else:
                    st.success(f"✅ {selected_country_label} (최근 {period_days}일 이내) 떡상 쇼츠 TOP {len(results)} 수집 완료!")
                    
                    # 1위부터 순서대로 출력
                    for rank, row in enumerate(results, start=1):
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            if row['썸네일']:
                                st.image(row['썸네일'], use_container_width=True)
                            
                        with col2:
                            st.subheader(f"🏆 {rank}위. {row['제목']}")
                            st.write(f"📺 **채널명**: {row['채널명']} | 👥 **구독자 수**: {row['구독자 수']:,}명 | 📅 **게시일**: {row['게시일']}")
                            st.write(f"🔥 **조회수**: {row['조회수']:,}회 | 👍 **좋아요**: {row['좋아요 수']:,}개")
                            st.markdown(f"[👉 유튜브에서 쇼츠 바로보기]({row['링크']})")
                        st.divider()

        except Exception as e:
            st.error(f"❌ 데이터 조회 중 오류가 발생했습니다: {e}")