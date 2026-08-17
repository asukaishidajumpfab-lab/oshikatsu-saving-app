import streamlit as st
import requests
import html
import calendar
from datetime import datetime, date
from zoneinfo import ZoneInfo
from urllib.parse import urlparse, parse_qs
import pandas as pd
import plotly.express as px
from supabase import create_client

# ==================================================
# アプリ設定
# ==================================================

st.set_page_config(
    page_title="推し活貯金",
    page_icon="💖",
    layout="wide",
)

JST = ZoneInfo("Asia/Tokyo")
API_DAILY_LIMIT = 20  # 将来変更する場合はここだけ変更

KAIDA_CHANNEL_ID = "UCo2N7C-Z91waaR6lF3LL_jw"
ROFMAO_CHANNEL_ID = "UCwi4P78SVunSYAGrvC9aKcw"

DEFAULT_SAVING_RULES = {
    "個人配信": 500,
    "コラボ配信": 1000,
    "Short": 100,
    "Short(踊ってみた)": 500,
    "歌ってみた(フル)": 5000,
    "Short(歌ってみた)": 2000,
    "3D(自枠)": 10000,
    "3D(他枠ゲスト)": 1000,
    "3D(ろふまお塾)": 200,
    "オリジナル曲(個人)": 3000,
    "オリジナル曲(ユニット, その他)": 1500,
}

DEFAULT_CONTENT_TYPE_ICONS = {
    "個人配信": "🎙️",
    "コラボ配信": "🤝",
    "Short": "📱",
    "Short(踊ってみた)": "💃",
    "歌ってみた(フル)": "🎤",
    "Short(歌ってみた)": "🎵",
    "3D(自枠)": "✨",
    "3D(他枠ゲスト)": "🌟",
    "3D(ろふまお塾)": "🎪",
    "オリジナル曲(個人)": "🎼",
    "オリジナル曲(ユニット, その他)": "🎶",
}

DEFAULT_TAG_COLORS = {
    "長尾景": "#625DA1",
    "弦月藤士郎": "#B43246",
    "加賀美ハヤト": "#B9ADB9",
    "不破湊": "#BF69F4",
    "剣持刀也": "#A590AF",
    "星川サラ": "#FAB80D",
    "本間ひまわり": "#FBE340",
    "海妹四葉": "#FFE632",
    "VΔLZ": "#FFFFFF",
    "晴レ星": "#FFFF89",
}

# 表・記録内タグの表示順。ここはユーザー自身で変更できます。
# 「タグから探す」の順番には影響しません。
TAG_ORDER = [
    "#ROF-MAO",
    "#剣持刀也",
    "#叶",
    "#本間ひまわり",
    "#葛葉",
    "#社築",
    "#緑仙",
    "#春崎エアル",
    "#夢追翔",
    "#三枝明那",
    "#加賀美ハヤト",
    "#アルス・アルマル",
    "#織姫星",
    "#星川サラ",
    "#晴レ星",
    "#不破湊",
    "#VΔLZ",
    "#長尾景",
    "#弦月藤士郎",
    "#海妹四葉",
    "#風楽奏斗",
    "#渡会雲雀",
    "#四季凪アキラ",
    "#セラフ・ダズルガーデン",
    "#緋八マナ",
    "#伊波ライ",
    "#ミラン・ケストレル",
    "#榊ネス",
    "#酒寄颯馬",
    "#渚トラウト",
    "#皇れお",
    "#篠宮ゆの",
    "#城瀬いすみ",
    "#花籠つばさ",
]

TAG_SEARCH_COLORS = [
    "#FFB3BA", "#FFD1A9", "#FFF2A8", "#B8E6B8",
    "#B8E0F2", "#BFCBFF", "#D8B4E8",
]

AUTO_TAG_RULES = {
    "#長尾景": ["長尾景", "Nagao Kei"],
    "#弦月藤士郎": ["弦月藤士郎", "Genzuki Tojiro"],
    "#加賀美ハヤト": ["加賀美ハヤト", "Kagami Hayato"],
    "#不破湊": ["不破湊", "Fuwa Minato"],
    "#剣持刀也": ["剣持刀也", "Kenmochi Toya"],
    "#星川サラ": ["星川サラ", "Hoshikawa Sara"],
    "#VΔLZ": ["VΔLZ", "VOLTACTION", "ヴァルツ"],
    "#ROF-MAO": ["ROF-MAO", "ろふまお", "ROFMAO"],
}

# ==================================================
# Supabase
# ==================================================

@st.cache_resource

def get_supabase():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_service_role_key"]
    return create_client(url, key)


supabase = get_supabase()

# ==================================================
# 認証
# Streamlit標準OIDC。初期リリースはGoogleログインを想定。
# ==================================================

if not getattr(st.user, "is_logged_in", False):
    st.title("💖 推し活貯金")
    st.write("YouTubeの推し活を記録して、楽しく貯金するアプリです ✨")
    st.info("利用するにはGoogleアカウントでログインしてください。")
    st.button("🔐 Googleでログイン", on_click=st.login)
    st.stop()

USER_ID = str(getattr(st.user, "sub", ""))
USER_EMAIL = str(getattr(st.user, "email", ""))

if not USER_ID:
    st.error("ログイン情報を取得できませんでした。いったんログアウトして再度お試しください。")
    st.stop()

# ==================================================
# CSS
# ==================================================

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    .tag-search-title { font-size: 1rem; font-weight: 600; margin-top: .5rem; margin-bottom: 0; }
    div[data-testid="stButton"] button { border-radius: 999px; border: 1px solid #F0C6D8; background-color: #E0FFFF; color: #4DD7E3; font-weight: 600; }
    div[data-testid="stButton"] button:hover { border-color: #E9A9C4; background-color: #A8FFFF; color: #66384D; }
    [data-testid="stMetricValue"] { font-weight: 700; }
    .back-to-top {
        position: fixed;
        right: 24px;
        bottom: 24px;
        z-index: 999999;
        display: inline-block;
        padding: .55rem .9rem;
        border-radius: 999px;
        background: #E0FFFF;
        border: 1px solid #00BFFF;
        color: #4DD7E3 !important;
        font-size: .85rem;
        font-weight: 700;
        text-decoration: none !important;
        box-shadow: 0 2px 8px rgba(0,0,0,.15);
    }
    .back-to-top:hover { background:#A8FFFF; color:#66384D !important; transform:translateY(-2px); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# 共通ヘルパー
# ==================================================

def now_jst():
    return datetime.now(JST)


def user_query(table, columns="*"):
    return supabase.table(table).select(columns).eq("user_id", USER_ID)


def normalize_tag(tag):
    tag = str(tag).strip()
    if not tag:
        return ""
    return tag if tag.startswith("#") else "#" + tag


def normalize_tags(tags):
    if not tags:
        return ""
    result = []
    for tag in tags:
        tag = normalize_tag(tag)
        if tag and tag not in result:
            result.append(tag)
    return " ".join(result)


def get_contrast_text_color(hex_color):
    hex_color = hex_color.lstrip("#")
    try:
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    except Exception:
        return "#000000"
    brightness = .299*r + .587*g + .114*b
    return "#000000" if brightness >= 160 else "#FFFFFF"


def sort_tags_for_display(tags):
    order = {tag: i for i, tag in enumerate(TAG_ORDER)}
    return sorted(tags, key=lambda tag: (order.get(tag, len(TAG_ORDER)), tag))


def display_tags(tags, tag_colors):
    if not tags:
        return ""
    html_text = ""
    for tag in sort_tags_for_display(tags.split()):
        name = tag.lstrip("#")
        color = tag_colors.get(name, "#F3E8EE")
        text_color = get_contrast_text_color(color)
        html_text += f'''<span style="display:inline-block;background:{color};color:{text_color};border-radius:999px;padding:3px 10px;margin:2px 3px 2px 0;font-size:.82rem;font-weight:600;white-space:nowrap;">#{html.escape(name)}</span>'''
    return html_text


def format_published_date(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(JST)
    return dt.strftime("%Y/%m/%d")


def get_youtube_video_id(url):
    parsed = urlparse(url)
    hostname = parsed.hostname
    if hostname in ("www.youtube.com", "youtube.com"):
        query = parse_qs(parsed.query)
        if "v" in query:
            return query["v"][0]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/shorts/")[1].split("/")[0]
    if hostname == "youtu.be":
        return parsed.path.strip("/").split("/")[0]
    return None


def is_short(info, url):
    parsed = urlparse(url)
    text = f"{info.get('title','')}\n{info.get('description','')}".lower()
    return parsed.path.startswith("/shorts/") or "#shorts" in text or "#short" in text


def has_3d_keyword(info):
    text = f"{info.get('title','')}\n{info.get('description','')}"
    return any(x in text for x in ("3D", "３D", "3ｄ", "３ｄ"))


def auto_detect_content_type(info, url, saving_rules):
    title = info.get("title", "")
    description = info.get("description", "")
    text = f"{title}\n{description}"
    if is_short(info, url):
        if "歌ってみた" in text:
            return "Short(歌ってみた)", "Shorts + 歌ってみたを検出"
        if "踊ってみた" in text:
            return "Short(踊ってみた)", "Shorts + 踊ってみたを検出"
        return "Short", "Shorts動画を検出"
    if info.get("channel_id") == ROFMAO_CHANNEL_ID:
        return "3D(ろふまお塾)", "ROF-MAO公式チャンネルを検出"
    if "歌ってみた" in text or "cover" in text.lower():
        return "歌ってみた(フル)", "歌ってみたを検出"
    if info.get("channel_id") != KAIDA_CHANNEL_ID:
        return "コラボ配信", "甲斐田晴さんのチャンネルではないためコラボ配信として判定"
    if has_3d_keyword(info):
        return "3D(自枠)", "3D + 甲斐田晴さんの自枠を検出"
    if "オリジナル曲" in text or "original song" in text.lower() or "original" in title.lower():
        unit_keywords = ["ユニット", "ROF-MAO", "VΔLZ", "ろふまお"]
        if any(k in text for k in unit_keywords):
            return "オリジナル曲(ユニット, その他)", "オリジナル曲 + ユニット関連語を検出"
        return "オリジナル曲(個人)", "オリジナル曲を検出"
    if "コラボ" in text:
        return "コラボ配信", "タイトルまたは説明欄に「コラボ」を検出"
    return "個人配信", "甲斐田晴さんのチャンネルのその他コンテンツとして仮設定"


def suggest_tags(info):
    text = f"{info.get('channel_name','')}\n{info.get('title','')}\n{info.get('description','')}".lower()
    result = []
    for tag, keywords in AUTO_TAG_RULES.items():
        if any(k.lower() in text for k in keywords):
            result.append(tag)
    return result

# ==================================================
# ユーザー設定
# ==================================================

def default_settings():
    return {
        "saving_rules": DEFAULT_SAVING_RULES.copy(),
        "content_type_icons": DEFAULT_CONTENT_TYPE_ICONS.copy(),
        "tag_colors": DEFAULT_TAG_COLORS.copy(),
    }


def load_settings():
    response = user_query("user_settings").limit(1).execute()
    if not response.data:
        data = default_settings()
        supabase.table("user_settings").insert({
            "user_id": USER_ID,
            "saving_rules": data["saving_rules"],
            "content_type_icons": data["content_type_icons"],
            "tag_colors": data["tag_colors"],
        }).execute()
        return data
    row = response.data[0]
    result = default_settings()
    result["saving_rules"].update(row.get("saving_rules") or {})
    result["content_type_icons"].update(row.get("content_type_icons") or {})
    result["tag_colors"].update(row.get("tag_colors") or {})
    return result


settings = load_settings()
SAVING_RULES = settings["saving_rules"]
CONTENT_TYPE_ICONS = settings["content_type_icons"]
TAG_COLORS = settings["tag_colors"]

# ==================================================
# YouTube情報DB
# ==================================================

def get_shared_video(video_id):
    response = supabase.table("youtube_videos").select("*").eq("video_id", video_id).limit(1).execute()
    return response.data[0] if response.data else None


def get_youtube_video_info(video_id):
    api_key = st.secrets["youtube_api_key"]
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet,liveStreamingDetails", "id": video_id, "key": api_key},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("items"):
        return None
    item = data["items"][0]
    snippet = item["snippet"]
    live = item.get("liveStreamingDetails", {})
    published_at = snippet.get("publishedAt")
    actual = live.get("actualStartTime")
    scheduled = live.get("scheduledStartTime")
    content_start = actual or scheduled or published_at
    info = {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "channel_name": snippet.get("channelTitle", ""),
        "channel_id": snippet.get("channelId", ""),
        "published_at": content_start,
        "youtube_published_at": published_at,
        "actual_start_time": actual,
        "scheduled_start_time": scheduled,
    }
    supabase.table("youtube_videos").upsert(info, on_conflict="video_id").execute()
    return info


def get_saved_video_info(video_id):
    response = user_query("records").select("video_id,title,channel_name,channel_id,published_at,tags").eq("video_id", video_id).limit(1).execute()
    return response.data[0] if response.data else None


def get_api_usage_today():
    today = now_jst().strftime("%Y-%m-%d")
    response = supabase.table("api_usage").select("count").eq("user_id", USER_ID).eq("usage_date", today).limit(1).execute()
    return int(response.data[0]["count"]) if response.data else 0


def consume_api_quota():
    today = now_jst().strftime("%Y-%m-%d")
    response = supabase.rpc("consume_api_quota", {"p_user_id": USER_ID, "p_usage_date": today, "p_limit": API_DAILY_LIMIT}).execute()
    if response.data is None:
        return False, get_api_usage_today()
    result = response.data
    if isinstance(result, list) and result:
        result = result[0]
    if isinstance(result, dict):
        return bool(result.get("allowed")), int(result.get("count", 0))
    return bool(result), get_api_usage_today()


def fetch_video_from_url(url):
    video_id = get_youtube_video_id(url)
    if not video_id:
        return None, "YouTube URLを認識できませんでした。"
    saved = get_saved_video_info(video_id)
    if saved:
        return saved, "saved"
    shared = get_shared_video(video_id)
    if shared:
        return shared, "shared"
    allowed, count = consume_api_quota()
    if not allowed:
        return None, f"本日のYouTube API利用上限（{API_DAILY_LIMIT}回）に達しています。明日またお試しください。"
    info = get_youtube_video_info(video_id)
    if info is None:
        return None, "動画が見つかりませんでした。"
    return info, f"youtube:{count}"

# ==================================================
# カレンダーDB
# ==================================================

def get_calendar_check(date_str):
    response = user_query("calendar_checks").select("status").eq("date", date_str).limit(1).execute()
    return response.data[0]["status"] if response.data else None


def set_calendar_check(date_str, status):
    supabase.table("calendar_checks").upsert({"user_id": USER_ID, "date": date_str, "status": status}, on_conflict="user_id,date").execute()


def get_user_records():
    response = user_query("records").select("id,url,title,channel_name,content_type,amount,published_at,tags,video_id,description,channel_id,created_at").order("published_at", desc=True).execute()
    return response.data or []

# ==================================================
# 設定画面
# ==================================================

with st.sidebar:
    st.markdown("### 💖 推し活貯金")
    st.caption(USER_EMAIL or "ログイン中")
    if st.button("🚪 ログアウト", use_container_width=True):
        st.logout()

    with st.expander("⚙️ 自分用設定"):
        st.caption("金額・アイコンは他の利用者には影響しません。")
        edited_rules = {}
        edited_icons = {}
        for content_type in DEFAULT_SAVING_RULES:
            c1, c2 = st.columns([2, 1])
            with c1:
                edited_rules[content_type] = st.number_input(content_type, min_value=0, step=100, value=int(SAVING_RULES.get(content_type, DEFAULT_SAVING_RULES[content_type])), key=f"rule_{content_type}")
            with c2:
                edited_icons[content_type] = st.text_input("アイコン", value=str(CONTENT_TYPE_ICONS.get(content_type, "📺")), key=f"icon_{content_type}")
        if st.button("💾 設定を保存", use_container_width=True):
            supabase.table("user_settings").upsert({"user_id": USER_ID, "saving_rules": edited_rules, "content_type_icons": edited_icons, "tag_colors": TAG_COLORS}, on_conflict="user_id").execute()
            st.success("設定を保存しました！")
            st.rerun()
        st.caption(f"YouTube API：本日 {get_api_usage_today()} / {API_DAILY_LIMIT} 回")

# ==================================================
# タイトル・貯金状況
# ==================================================

st.title("💖 推し活貯金")
st.caption("YouTubeの推し活を記録して、楽しく貯金します ✨")

records = get_user_records()

total_savings = sum(int(r.get("amount") or 0) for r in records)
current_month = now_jst().strftime("%Y-%m")
monthly_savings = sum(int(r.get("amount") or 0) for r in records if str(r.get("published_at", ""))[:7] == current_month)

st.subheader("💰 貯金状況")
col1, col2 = st.columns(2)
with col1:
    st.metric("🌷 今月の推し活貯金", f"{monthly_savings:,}円")
with col2:
    st.metric("💎 累計貯金額", f"{total_savings:,}円")

monthly_map = {}
for r in records:
    month = str(r.get("published_at", ""))[:7]
    if month:
        monthly_map[month] = monthly_map.get(month, 0) + int(r.get("amount") or 0)
if monthly_map:
    chart_df = pd.DataFrame(sorted(monthly_map.items()), columns=["月", "貯金額"])
    chart_df["月"] = pd.to_datetime(chart_df["月"])
    chart_df["月表示"] = chart_df["月"].dt.strftime("%Y年%m月")
    fig = px.bar(chart_df, x="月表示", y="貯金額", text="貯金額", labels={"月表示":"月", "貯金額":"貯金額"}, color_discrete_sequence=["#4DD7E3"])
    fig.update_traces(texttemplate="%{text:,}円", textposition="outside")
    fig.update_layout(height=400, margin=dict(l=20,r=20,t=30,b=20), xaxis_title=None, yaxis_title=None, showlegend=False)
    fig.update_yaxes(tickformat=",", rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ==================================================
# URL取得・動画登録
# ==================================================

st.divider()
st.subheader("🎬 YouTube動画を登録")

query_params = st.query_params
external_url = query_params.get("url", "")
if external_url:
    st.session_state["external_url"] = external_url
    if st.session_state.get("auto_processed_url") != external_url:
        st.session_state["auto_processed_url"] = external_url
        try:
            info, source = fetch_video_from_url(external_url)
            if info:
                st.session_state["video_info"] = info
                st.session_state["video_already_saved"] = source == "saved"
            else:
                st.session_state["auto_fetch_error"] = source
        except Exception as e:
            st.session_state["auto_fetch_error"] = f"エラーが発生しました: {e}"
    st.query_params.clear()

if st.session_state.get("auto_fetch_error"):
    st.error(st.session_state.pop("auto_fetch_error"))

url = st.text_input("YouTube URL", value=st.session_state.get("external_url", ""), placeholder="https://www.youtube.com/watch?v=...")

if st.button("✨ YouTube情報を取得", use_container_width=True):
    if not url:
        st.warning("YouTube URLを入力してください。")
    else:
        try:
            with st.spinner("🔍 YouTube情報を確認しています..."):
                info, source = fetch_video_from_url(url)
            if info:
                st.session_state["video_info"] = info
                st.session_state["video_already_saved"] = source == "saved"
                st.success("YouTube情報を取得しました！" if source != "saved" else "🔖 登録済み動画を確認しました。")
            else:
                st.error(source)
        except requests.exceptions.HTTPError as e:
            st.error(f"YouTube APIでエラーが発生しました: {e}")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

if "video_info" in st.session_state:
    info = st.session_state["video_info"]
    st.divider()
    st.subheader("📺 動画情報")
    st.write(f"**タイトル:** {info['title']}")
    st.write(f"**チャンネル:** {info['channel_name']}")
    st.write(f"**公開日:** {format_published_date(info['published_at'])}")

    if st.session_state.get("video_already_saved", False):
        st.warning("この動画はすでにあなたの記録に登録されています。")
    else:
        detected_type, reason = auto_detect_content_type(info, url, SAVING_RULES)
        st.subheader("🏷️ 推し活の種類")
        if detected_type not in SAVING_RULES:
            detected_type = "個人配信"
        st.write(f"🤖 自動判定：**{detected_type}**")
        st.caption(f"判定理由：{reason}")
        content_type = st.selectbox("必要なら変更してください", list(SAVING_RULES.keys()), index=list(SAVING_RULES.keys()).index(detected_type), key="new_content_type")
        amount = int(SAVING_RULES[content_type])
        st.write(f"💰 貯金額：**{amount:,}円**")

        st.subheader("🏷️ タグ")
        existing_tag_counts = {}
        for r in records:
            for tag in (r.get("tags") or "").split():
                existing_tag_counts[tag] = existing_tag_counts.get(tag, 0) + 1
        existing_tags = [t for t, _ in sorted(existing_tag_counts.items(), key=lambda x: (-x[1], x[0]))]
        suggested_tags = [] if detected_type == "個人配信" else suggest_tags(info)
        tag_options = list(existing_tags)
        for tag in suggested_tags:
            if tag not in tag_options:
                tag_options.append(tag)
        selected_tags = st.multiselect("タグを選択", tag_options, default=suggested_tags, accept_new_options=True, placeholder="過去のタグから選択 / 新しいタグも入力できます", key="new_record_tags")
        normalized_tags = normalize_tags(selected_tags)
        if normalized_tags:
            st.markdown(display_tags(normalized_tags, TAG_COLORS), unsafe_allow_html=True)

        if st.button("💖 この内容で保存", use_container_width=True):
            try:
                supabase.table("records").insert({
                    "user_id": USER_ID,
                    "url": url,
                    "video_id": info["video_id"],
                    "title": info["title"],
                    "description": info.get("description", ""),
                    "channel_name": info["channel_name"],
                    "channel_id": info["channel_id"],
                    "published_at": info["published_at"],
                    "content_type": content_type,
                    "amount": amount,
                    "tags": normalized_tags,
                    "created_at": now_jst().isoformat(),
                }).execute()
                st.success(f"💖 {content_type}として{amount:,}円を貯金しました！")
                for key in ("video_info", "video_already_saved", "new_record_tags"):
                    st.session_state.pop(key, None)
                st.rerun()
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    st.warning("この動画はすでにあなたの記録に登録されています。")
                else:
                    st.error(f"保存に失敗しました: {e}")

# ==================================================
# カレンダー
# ==================================================

st.divider()
st.subheader("📅 配信・動画カレンダー")

if "calendar_month" not in st.session_state:
    st.session_state["calendar_month"] = now_jst().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
calendar_month = st.session_state["calendar_month"]

a, b, c = st.columns([1,2,1])
with a:
    if st.button("← 前月", use_container_width=True, key="calendar_prev"):
        year, month = calendar_month.year, calendar_month.month - 1
        if month == 0: year, month = year-1, 12
        st.session_state["calendar_month"] = calendar_month.replace(year=year, month=month)
        st.rerun()
with b:
    st.markdown(f'<div style="text-align:center;font-size:1.2rem;font-weight:700;padding-top:.35rem;color:#00BFFF;">📅 {calendar_month.year}年 {calendar_month.month}月</div>', unsafe_allow_html=True)
with c:
    if st.button("次月 →", use_container_width=True, key="calendar_next"):
        year, month = calendar_month.year, calendar_month.month + 1
        if month == 13: year, month = year+1, 1
        st.session_state["calendar_month"] = calendar_month.replace(year=year, month=month)
        st.rerun()

today = now_jst().date()
if (calendar_month.year, calendar_month.month) != (today.year, today.month):
    if st.button("📍 今月へ戻る", key="calendar_today"):
        st.session_state["calendar_month"] = today.replace(day=1)
        st.rerun()

action1, action2 = st.columns(2)
with action1:
    if st.button("✓ なしを確認", use_container_width=True, key="open_calendar_confirm"):
        st.session_state["calendar_action"] = "confirm"
        st.rerun()
with action2:
    if st.button("✎ 日付を編集", use_container_width=True, key="open_calendar_edit"):
        st.session_state["calendar_action"] = "edit"
        st.rerun()

if st.session_state.get("calendar_action") == "confirm":
    st.markdown("**✓ 配信・動画がなかったことを確認**")
    year, month = calendar_month.year, calendar_month.month
    selectable = []
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        d_obj = date(year, month, d)
        d_str = d_obj.strftime("%Y-%m-%d")
        has_record = any(str(r.get("published_at", ""))[:10] == d_str for r in records)
        if not has_record and get_calendar_check(d_str) != "confirmed_none":
            selectable.append(d_obj)
    options = {f"{d:%m/%d}（{'月火水木金土日'[d.weekday()]}）": d.strftime("%Y-%m-%d") for d in selectable}
    if options:
        selected = st.multiselect("確認する日付", list(options), key="calendar_confirm_dates")
        x, y = st.columns(2)
        with x:
            if st.button("✓ 選択した日を確認済みにする", use_container_width=True, key="confirm_calendar_dates"):
                for label in selected:
                    set_calendar_check(options[label], "confirmed_none")
                st.session_state.pop("calendar_action", None)
                st.session_state.pop("calendar_confirm_dates", None)
                st.rerun()
        with y:
            if st.button("キャンセル", use_container_width=True, key="cancel_calendar_confirm"):
                st.session_state.pop("calendar_action", None)
                st.rerun()
    else:
        st.info("この月には、まだ確認できる日付がありません。")

if st.session_state.get("calendar_action") == "edit":
    st.markdown("**✎ 登録済み動画・配信の日付を編集**")
    if records:
        edit_options = {}
        for r in records:
            try: display_date = format_published_date(r["published_at"])
            except Exception: display_date = str(r["published_at"])
            edit_options[f"{CONTENT_TYPE_ICONS.get(r['content_type'],'📺')} {display_date} {r['title']}"] = r
        label = st.selectbox("編集する動画・配信", list(edit_options), key="calendar_edit_record")
        selected = edit_options[label]
        try:
            dt = datetime.fromisoformat(str(selected["published_at"]).replace("Z", "+00:00"))
            if dt.tzinfo: dt = dt.astimezone(JST)
        except Exception:
            dt = now_jst()
        d1, d2 = st.columns(2)
        with d1: edited_date = st.date_input("日付", dt.date(), key=f"calendar_edit_date_{selected['id']}")
        with d2: edited_time = st.time_input("開始時刻", dt.time(), key=f"calendar_edit_time_{selected['id']}")
        x, y = st.columns(2)
        with x:
            if st.button("💾 日付・時刻を保存", use_container_width=True, key=f"save_calendar_edit_{selected['id']}"):
                edited = datetime.combine(edited_date, edited_time).replace(tzinfo=JST).isoformat()
                user_query("records").eq("id", selected["id"]).update({"published_at": edited}).execute()
                st.session_state.pop("calendar_action", None)
                st.rerun()
        with y:
            if st.button("キャンセル", use_container_width=True, key="cancel_calendar_edit"):
                st.session_state.pop("calendar_action", None)
                st.rerun()

# Calendar display
records_by_date = {}
for r in records:
    try:
        dt = datetime.fromisoformat(str(r["published_at"]).replace("Z", "+00:00"))
        if dt.tzinfo: dt = dt.astimezone(JST)
        else: dt = dt.replace(tzinfo=JST)
        d = dt.strftime("%Y-%m-%d")
        records_by_date.setdefault(d, []).append(r)
    except Exception:
        pass

cal = calendar.Calendar(firstweekday=6)
weeks = cal.monthdayscalendar(calendar_month.year, calendar_month.month)
weekday_names = ["日","月","火","水","木","金","土"]
for col, wd in zip(st.columns(7), weekday_names):
    with col: st.markdown(f'<div style="text-align:center;font-weight:700;padding:.4rem 0;color:#4DD7E3;">{wd}</div>', unsafe_allow_html=True)

for week in weeks:
    cols = st.columns(7)
    for i, day_num in enumerate(week):
        with cols[i]:
            if day_num == 0:
                st.markdown('<div style="height:115px"></div>', unsafe_allow_html=True)
                continue
            d = date(calendar_month.year, calendar_month.month, day_num)
            d_str = d.strftime("%Y-%m-%d")
            day_records = records_by_date.get(d_str, [])
            check_status = get_calendar_check(d_str)
            if day_records:
                cards = ""
                for item in day_records:
                    icon = html.escape(CONTENT_TYPE_ICONS.get(item["content_type"], "📺"))
                    typ = html.escape(str(item["content_type"]))
                    title = str(item["title"])
                    short_title = title[:27] + "…" if len(title) > 28 else title
                    safe_title = html.escape(short_title)
                    safe_url = html.escape(str(item["url"]), quote=True)
                    cards += f'''<div style="margin-top:.25rem;padding:.1rem 0;text-align:center;"><div style="font-size:.88rem;font-weight:600;color:#4DD7E3;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{icon} {typ}</div><div style="font-size:.65rem;margin-top:.18rem;line-height:1.25;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;"><a href="{safe_url}" target="_blank" style="color:#4DD7E3;text-decoration:none;">{safe_title}</a></div></div>'''
                st.html(f'''<div style="background:#E0FFFF;border:1px solid #00BFFF;border-radius:12px;min-height:105px;padding:.4rem .3rem;text-align:center;margin-bottom:.35rem;box-sizing:border-box;"><div style="display:inline-flex;align-items:center;justify-content:center;width:1.65rem;height:1.65rem;border-radius:50%;background:#FFFFFF;color:#4DD7E3;font-size:.78rem;font-weight:700;margin-bottom:.1rem;">{day_num}</div>{cards}</div>''')
            elif check_status == "confirmed_none":
                st.html(f'''<div style="background:#F3F8F3;border:1px solid #C7DEC7;border-radius:12px;min-height:105px;padding:.4rem .3rem;text-align:center;margin-bottom:.35rem;"><div style="font-weight:700;color:#5A4650;">{day_num}</div><div style="font-size:1.25rem;margin-top:.55rem;color:#719471;">✓</div><div style="font-size:.68rem;color:#718071;">配信なし確認済み</div></div>''')
            else:
                st.html(f'''<div style="background:#FFFFFF;border:1px solid #E8E8E8;border-radius:12px;min-height:105px;padding:.4rem .3rem;text-align:center;margin-bottom:.35rem;"><div style="font-weight:600;font-size:.82rem;color:#4DD7E3;">{day_num}</div></div>''')

# ==================================================
# 検索・一覧
# ==================================================

st.divider()
st.subheader("🔎 保存済みデータを検索")
search_text = st.text_input("キーワード", placeholder="タイトル・配信枠・タグなど", key="search_text")

# 使用回数順。TAG_ORDERはここには使わない。
tag_counts = {}
for r in records:
    for tag in (r.get("tags") or "").split():
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
sorted_tags = [t for t, _ in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))]

st.markdown('<div class="tag-search-title">🎀 タグから探す</div>', unsafe_allow_html=True)
selected_tag = st.session_state.get("selected_search_tag")

if sorted_tags:
    tag_css = ""
    for i, tag in enumerate(sorted_tags):
        color = TAG_SEARCH_COLORS[i % len(TAG_SEARCH_COLORS)]
        border = "2px solid #555555" if selected_tag == tag else f"1px solid {color}"
        key = f"search_tag_{i}"
        tag_css += f'.st-key-{key} .stButton button{{background-color:{color};border:{border};border-radius:999px;color:#5A4650;font-weight:600;padding:.35rem .8rem;margin:0;}}'
    st.markdown(f"<style>{tag_css}</style>", unsafe_allow_html=True)
    for start in range(0, len(sorted_tags), 5):
        row_tags = sorted_tags[start:start+5]
        cols = st.columns(len(row_tags))
        for idx, (col, tag) in enumerate(zip(cols, row_tags)):
            key = f"search_tag_{start+idx}"
            with col:
                if st.button(tag, key=key, use_container_width=True):
                    st.session_state["selected_search_tag"] = None if selected_tag == tag else tag
                    st.rerun()

selected_tag = st.session_state.get("selected_search_tag")
if selected_tag:
    st.info(f"🏷️ {selected_tag} を表示中")
    if st.button("タグ検索を解除", key="clear_tag"):
        st.session_state["selected_search_tag"] = None
        st.rerun()

content_type_filter = st.selectbox("🎬 種別", ["すべて"] + list(SAVING_RULES.keys()), index=0)

filtered = []
for r in records:
    tags = r.get("tags") or ""
    searchable = f"{r.get('title','')} {r.get('channel_name','')} {r.get('content_type','')} {tags}".lower()
    if search_text and search_text.lower() not in searchable:
        continue
    if content_type_filter != "すべて" and r.get("content_type") != content_type_filter:
        continue
    if selected_tag and selected_tag not in tags.split():
        continue
    filtered.append(r)

st.caption(f"{len(filtered)}件表示")

if not filtered:
    st.info("該当する記録がありません。")
else:
    header = st.columns([4,1.4,1.5,1,1.2,1.8,.8])
    for col, label in zip(header, ["**タイトル**","**配信枠**","**種別**","**金額**","**公開日**","**タグ**","**編集**"]):
        col.markdown(label)
    st.divider()

    for r in filtered:
        record_id = r["id"]
        row = st.columns([4,1.4,1.5,1,1.2,1.8,.8])
        with row[0]: st.markdown(f"[**{html.escape(str(r['title']))}**]({r['url']})")
        with row[1]: st.write(r["channel_name"])
        with row[2]: st.write(r["content_type"])
        with row[3]: st.write(f"{int(r['amount']):,}円")
        with row[4]: st.write(format_published_date(r["published_at"]))
        with row[5]:
            if r.get("tags"): st.markdown(display_tags(r["tags"], TAG_COLORS), unsafe_allow_html=True)
            else: st.caption("タグなし")
        with row[6]:
            if st.button("編集", key=f"edit_{record_id}"):
                st.session_state["editing_record_id"] = record_id
                st.rerun()

        if st.session_state.get("editing_record_id") == record_id:
            st.markdown('<div style="background:#FFF8FB;border:1px solid #F0C6D8;border-radius:12px;padding:1rem;margin:.3rem 0 1rem;">', unsafe_allow_html=True)
            st.markdown("### ✏️ 記録を編集")
            st.caption(r["title"])
            edited_type = st.selectbox("種別", list(SAVING_RULES.keys()), index=list(SAVING_RULES.keys()).index(r["content_type"]), key=f"editing_content_type_{record_id}")
            edited_amount = int(SAVING_RULES[edited_type])
            st.write(f"💰 貯金額：**{edited_amount:,}円**")
            current_tags = (r.get("tags") or "").split()
            available_tags = list(sorted_tags)
            for tag in current_tags:
                if tag not in available_tags: available_tags.append(tag)
            edited_tags = st.multiselect("タグ", available_tags, default=current_tags, accept_new_options=True, key=f"editing_tags_{record_id}")
            normalized_edited_tags = normalize_tags(edited_tags)
            if normalized_edited_tags: st.markdown(display_tags(normalized_edited_tags, TAG_COLORS), unsafe_allow_html=True)
            else: st.caption("タグなし")
            x, y = st.columns(2)
            with x:
                if st.button("💾 保存", use_container_width=True, key=f"save_record_{record_id}"):
                    user_query("records").eq("id", record_id).update({"content_type": edited_type, "amount": edited_amount, "tags": normalized_edited_tags}).execute()
                    st.session_state.pop("editing_record_id", None)
                    st.rerun()
            with y:
                if st.button("キャンセル", use_container_width=True, key=f"cancel_record_{record_id}"):
                    st.session_state.pop("editing_record_id", None)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

# ==================================================
# 右下固定「一番上へ」
# ==================================================

st.markdown('<div id="top"></div><a href="#top" class="back-to-top">↑ 一番上へ</a>', unsafe_allow_html=True)
