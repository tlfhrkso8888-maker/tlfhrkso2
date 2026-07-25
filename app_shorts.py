import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import re

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="글로벌 쇼츠 떡상 분석 대시보드",
    page_icon="🎬",
    layout="wide"
)

# 2. 언어 정밀 검증 함수 (해외 낚시 쇼츠 100% 차단)
def is_valid_language(text, lang_code):
    if lang_code == "ja":
        # 히라가나(\u3040-\u309F) 또는 가타카나(\u30A0-\u30FF)가 최소 1글자 이상 포함되어야 일본 현지 쇼츠로 인정
        return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text))
    elif lang_code == "ko":
        # 완성된 한글(가-힣) 포함 여부 검사
        return bool(re.search(r'[가-힣]', text))
    elif lang_code == "vi":
        # 베트남어 특수 문자 검사
        return bool(re.search(r'[àáâãèéêìíòóôõùúýàáảãạầấẩẫậềếểễệỉịỏóổỗộởỡờớợủúủứừứựỳỵỷỹ]', text, re.IGNORECASE))
    elif lang_code == "hi":
        # 힌디어 데바나가리 문자 검사
        return bool(re.search(r'[\u0900-\u097F]', text))
    elif lang_code == "zh-TW":
        # 대만/번체자 한자 범위 검사
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    return True

# 3. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 조건 설정")
    
    # API 키 자동 기본값 설정
    DEFAULT_YT_KEY = "" # 필요 시 키를 직접 넣어두실 수 있습니다.
    DEFAULT_GEMINI_KEY = ""
    
    yt_api_key = st.text_input("🔑 YouTube API Key", value=DEFAULT_YT_KEY, type="password")
    gemini_api_key = st.text_input("🔮 Google Gemini API Key", value=DEFAULT_GEMINI_KEY, type="password")
    
    st.divider()
    
    country_config = {
        "일본 🇯🇵": {
            "region": "JP", "lang": "ja",
            "keywords": ["ショート", "バズ", "おすすめ", "日常", "検証"]
        },
        "대한민국 🇰🇷": {
            "region": "KR", "lang": "ko",
            "keywords": ["쇼츠", "떡상", "일상", "리뷰", "유머"]
        },
        "미국 🇺🇸": {
            "region": "US", "lang": "en",
            "keywords": ["viral shorts", "trending shorts", "funny shorts", "hacks"]
        },
        "인도 🇮🇳": {
            "region": "IN", "lang": "hi",
            "keywords": ["shorts", "viral shorts", "trending shorts", "comedy shorts"]
        },
        "대만 🇹🇼": {
            "region": "TW", "lang": "zh-TW",
            "keywords": ["短影音", "熱門", "搞笑", "推薦"]
        }
    }
    
    selected_country_label = st.selectbox("🌍 대상 국가 선택", list(country_config.keys()))
    c_info = country_config[selected_country_label]
    
    period_days = st.selectbox("📅 게시 기간 선택", [7, 14, 30, 60, 90, 180, 365], index=0, format_func=lambda x: f"최근 {x}일 이내")
    
    sub_filter = st.selectbox(
        "👥 채널 구독자 수 구간",
        ["전체 채널 (모두 보기)", "1만 명 미만 (초기 떡상)", "1만 ~ 10만 명", "10만 ~ 100만 명", "100만 명 이상"]
    )
    
    target_count = st.slider("🏆 수집 상위 순위 (TOP N)", min_value=5, max_value=50, value=20, step=5)
    
    btn_fetch = st.button("🚀 실시간 인기 쇼츠 순위 불러오기")

st.title("🎬 실시간 국가별 떡상 쇼츠 분석기")
st.caption("선택한 국가의 현지 언어 패턴을 정밀 분석하여 타 국가 낚시 영상을 완벽히 차단합니다.")

def get_channel_subscribers(youtube, channel_ids):
    if not channel_ids:
        return {}
    channel_ids = list(set(channel_ids))
    sub_map = {}
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i+50]
        res = youtube.channels().list(part="statistics", id=",".join(chunk)).execute()
        for item in res.get("items", []):
            sub_map[item["id"]] = int(item["statistics"].get("subscriberCount", 0))
    return sub_map

def check_sub_filter(sub_count, filter_type):
    if filter_type == "1만 명 미만 (초기 떡상)":
        return sub_count < 10000
    elif filter_type == "1만 ~ 10만 명":
        return 10000 <= sub_count < 100000
    elif filter_type == "10만 ~ 100만 명":
        return 100000 <= sub_count < 1000000
    elif filter_type == "100만 명 이상":
        return sub_count >= 1000000
    return True

if btn_fetch:
    if not yt_api_key.strip():
        st.error("⚠️ YouTube API Key를 입력해 주세요.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=yt_api_key.strip())
            
            with st.spinner(f"🚀 {selected_country_label} 현지 쇼츠 정밀 수집 및 검증 중..."):
                published_after = (datetime.utcnow() - timedelta(days=period_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
                raw_video_ids = []
                
                # 1단계: 현지 키워드 및 언어/지역 조합 검색
                for kw in c_info["keywords"]:
                    if len(raw_video_ids) >= 150:
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
                    
                    for item in s_res.get("items", []):
                        if 'videoId' in item['id']:
                            raw_video_ids.append(item['id']['videoId'])
                
                if not raw_video_ids:
                    st.warning("⚠️ 해당 기간 내 검색된 쇼츠가 없습니다. 게시 기간을 넓혀보세요.")
                else:
                    # 2단계: 비디오 세부 정보 가져오기
                    raw_video_ids = list(set(raw_video_ids))
                    video_items = []
                    for i in range(0, len(raw_video_ids), 50):
                        chunk = raw_video_ids[i:i+50]
                        v_res = youtube.videos().list(
                            part="snippet,statistics,contentDetails",
                            id=",".join(chunk)
                        ).execute()
                        video_items.extend(v_res.get("items", []))
                    
                    # 3단계: 채널 구독자 정보 수집
                    ch_ids = [v['snippet']['channelId'] for v in video_items if 'snippet' in v and 'channelId' in v['snippet']]
                    sub_map = get_channel_subscribers(youtube, ch_ids)
                    
                    # 4단계: 현지 언어 정밀 필터링 및 데이터 가공
                    final_results = []
                    for v in video_items:
                        snippet = v.get('snippet', {})
                        stats = v.get('statistics', {})
                        content_details = v.get('contentDetails', {})
                        
                        title = snippet.get('title', '')
                        ch_title = snippet.get('channelTitle', '')
                        
                        # [핵심] 현지 문자가 제목이나 채널명에 들어갔는지 검증하여 타 국가 낚시 쇼츠 차단
                        if not is_valid_language(title + ch_title, c_info["lang"]):
                            continue
                        
                        # 재생시간 검증 (60초 이하 쇼츠)
                        duration = content_details.get("duration", "")
                        if "M" in duration and duration != "PT1M":
                            continue
                        
                        ch_id = snippet.get('channelId', '')
                        sub_count = sub_map.get(ch_id, 0)
                        
                        if check_sub_filter(sub_count, sub_filter):
                            views = int(stats.get('viewCount', 0))
                            likes = int(stats.get('likeCount', 0))
                            pub_at = snippet.get('publishedAt', '')[:10]
                            thumbs = snippet.get('thumbnails', {})
                            thumb_url = thumbs.get('medium', {}).get('url', thumbs.get('default', {}).get('url', ''))
                            
                            final_results.append({
                                "v_id": v['id'],
                                "title": title,
                                "ch_title": ch_title,
                                "views": views,
                                "likes": likes,
                                "subs": sub_count,
                                "pub_at": pub_at,
                                "thumb": thumb_url,
                                "url": f"https://www.youtube.com/shorts/{v['id']}"
                            })
                    
                    # 조회수 순 정렬
                    final_results = sorted(final_results, key=lambda x: x['views'], reverse=True)[:target_count]
                    
                    if not final_results:
                        st.warning("⚠️ 언어 및 구독자 조건에 일치하는 순수 현지 쇼츠가 없습니다. 구독자 수 구간을 '전체 채널'로 설정해 보세요.")
                    else:
                        st.success(f"✅ {selected_country_label} 순수 현지 떡상 쇼츠 TOP {len(final_results)} 수집 완료!")
                        
                        for rank, item in enumerate(final_results, start=1):
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                if item['thumb']:
                                    st.image(item['thumb'], use_container_width=True)
                            with col2:
                                st.subheader(f"🏆 {rank}위. {item['title']}")
                                st.write(f"📺 **채널명**: {item['ch_title']} | 👥 **구독자 수**: {item['subs']:,}명 | 📅 **게시일**: {item['pub_at']}")
                                st.write(f"🔥 **조회수**: {item['views']:,}회 | 👍 **좋아요**: {item['likes']:,}개")
                                st.markdown(f"[👉 쇼츠 영상 바로가기]({item['url']})")
                            st.divider()

        except Exception as e:
            st.error(f"❌ 수집 중 오류가 발생했습니다: {e}")
