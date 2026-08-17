import calendar
from datetime import date, datetime
import html
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from supabase import create_client

# ==================================================
# アプリ設定 & 定数定義
# ==================================================
st.set_page_config(
    page_title="推し活貯金",
    page_icon="💖",
    layout="wide",
)

JST = ZoneInfo("Asia/Tokyo")
API_DAILY_LIMIT = 20
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

TAG_ORDER = [
    "#ROF-MAO", "#剣持刀也", "#叶", "#本間ひまわり", "#葛葉", "#社築", "#緑仙",
    "#春崎エアル", "#夢追翔", "#三枝明那", "#加賀美ハヤト", "#アルス・アルマル",
    "#織姫星", "#星川サラ", "#晴レ星", "#不破湊", "#VΔLZ", "#長尾景",
    "#弦月藤士郎", "#海妹四葉", "#風楽奏斗", "#渡会雲雀", "#四季凪アキラ",
    "#セラフ・ダズルガーデン", "#緋八マナ", "#伊波ライ", "#ミラン・ケストレル",
    "#榊ネス", "#酒寄颯馬", "#渚トラウト", "#皇れお", "#篠宮ゆの",
    "#城瀬いすみ", "#花籠つばさ",
]

TAG_SEARCH_COLORS = [
    "#FFB3BA", "#FFD1A9", "#FFF2A8", "#B8E6B8", "#B8E0F2", "#BFCBFF", "#D8B4E8"
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
# Supabase クライアント生成
# ==================================================
@st.cache_resource
def get_supabase():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_service_role_key"]
    return create_client(url, key)

supabase = get_supabase()

# ==================================================
# 認証
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
# CSS スタイル
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
        position: fixed; right: 24px; bottom: 70px; z-index: 999999;
        display: inline-block; padding: .55rem .9rem; border-radius: 999px;
        background: #E0FFFF; border: 1px solid #00BFFF; color: #4DD7E3 !important;
        font-size: .85rem; font-weight: 700; text-decoration: none !important;
        box-shadow: 0 2px 8px rgba(0,0,0,.15);
    }
    .back-to-top:hover { background:#A8FFFF; color:#66384D !important; transform:translateY(-2px); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# 共通ヘルパー関数
# ==================================================
def now_jst():
    return datetime.now(JST)

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
        t = normalize_tag(tag)
        if t and t not in result:
            result.append(t)
    return " ".join(result)

def get_contrast_text_color(hex_color):
    hex_color = hex_color.lstrip("#")
    try:
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        brightness = .299 * r + .587 * g + .114 * b
        return "#000000" if brightness >= 160 else "#FFFFFF"
    except Exception:
        return "#000000"

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
        html_text += f'<span style="display:inline-block;background:{color};color:{text_color};border-radius:999px;padding:3px 10px;margin:2px 3px 2px 0;font-size:.82rem;font-weight:600;white-space:nowrap;">#{html.escape(name)}</span>'
    return html_text

def format_published_date(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(JST)
        return dt.strftime("%Y/%m/%d")
    except Exception:
        return str(value)[:10]

def parse_iso_jst(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(JST) if dt.tzinfo else dt.replace(tzinfo=JST)
    except Exception:
        return now_jst()

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

def auto_detect_content_type(info, url):
    parsed = urlparse(url)
    title = info.get("title", "")
    description = info.get("description", "")
    text = f"{title}\n{description}"
    lower_text = text.lower()
    
    is_short = parsed.path.startswith("/shorts/") or "#shorts" in lower_text or "#short" in lower_text
    
    if is_short:
        if "歌ってみた" in text:
            return "Short(歌ってみた)", "Shorts + 歌ってみたを検出"
        if "踊ってみた" in text:
            return "Short(踊ってみた)", "Shorts + 踊ってみたを検出"
        return "Short", "Shorts動画を検出"
    if info.get("channel_id") == ROFMAO_CHANNEL_ID:
        return "3D(ろふまお塾)", "ROF-MAO公式チャンネルを検出"
    if "歌ってみた" in text or "cover" in lower_text:
        return "歌ってみた(フル)", "歌ってみたを検出"
    if info.get("channel_id") != KAIDA_CHANNEL_ID:
        return "コラボ配信", "甲斐田晴さんのチャンネルではないためコラボ配信として判定"
    if any(x in text for x in ("3D", "３D", "3ｄ", "３ｄ")):
        return "3D(自枠)", "3D + 甲斐田晴さんの自枠を検出"
    if "オリジナル曲" in text or "original song" in lower_text or "original" in title.lower():
        if any(k in text for k in ["ユニット", "ROF-MAO", "VΔLZ", "ろふまお"]):
            return "オリジナル曲(ユニット, その他)", "オリジナル曲 + ユニット関連語を検出"
        return "オリジナル曲(個人)", "オリジナル曲を検出"
    if "コラボ" in text:
        return "コラボ配信", "タイトルまたは説明欄に「コラボ」を検出"
    return "個人配信", "甲斐田晴さんのチャンネルのその他コンテンツとして仮設定"

def suggest_tags(info):
    text = f"{info.get('channel_name','')}\n{info.get('title','')}\n{info.get('description','')}".lower()
    return [tag for tag, keywords in AUTO_TAG_RULES.items() if any(k.lower() in text for k in keywords)]

# ==================================================
# キャッシュ付き DB/API 操作関数
# ==================================================
@st.cache_data(ttl=600)
def load_settings(user_id: str):
    res = supabase.table("user_settings").select("*").eq("user_id", user_id).limit(1).execute()
    data = {
        "saving_rules": DEFAULT_SAVING_RULES.copy(),
        "content_type_icons": DEFAULT_CONTENT_TYPE_ICONS.copy(),
        "tag_colors": DEFAULT_TAG_COLORS.copy(),
    }
    if res.data:
        row = res.data[0]
        data["saving_rules"].update(row.get("saving_rules") or {})
        data["content_type_icons"].update(row.get("content_type_icons") or {})
        data["tag_colors"].update(row.get("tag_colors") or {})
    else:
        supabase.table("user_settings").insert({"user_id": user_id, **data}).execute()
    return data

@st.cache_data(ttl=600)
def get_user_records(user_id: str):
    res = supabase.table("records") \
        .select("id,url,title,channel_name,content_type,amount,published_at,tags,video_id,description,channel_id,created_at") \
        .eq("user_id", user_id) \
        .order("published_at", desc=True) \
        .execute()
    return res.data or []

@st.cache_data(ttl=600)
def get_calendar_checks(user_id: str):
    res = supabase.table("calendar_checks").select("date,status").eq("user_id", user_id).execute()
    return {row["date"]: row["status"] for row in (res.data or [])}

@st.cache_data(ttl=3600)
def get_shared_video(video_id: str):
    res = supabase.table("youtube_videos").select("*").eq("video_id", video_id).limit(1).execute()
    return res.data[0] if res.data else None

def get_api_usage_today():
    today = now_jst().strftime("%Y-%m-%d")
    res = supabase.table("api_usage").select("count").eq("user_id", USER_ID).eq("usage_date", today).limit(1).execute()
    return int(res.data[0]["count"]) if res.data else 0

def consume_api_quota():
    today = now_jst().strftime("%Y-%m-%d")
    res = supabase.rpc("consume_api_quota", {"p_user_id": USER_ID, "p_usage_date": today, "p_limit": API_DAILY_LIMIT}).execute()
    if res.data is None:
        return False, get_api_usage_today()
    result = res.data[0] if isinstance(res.data, list) and res.data else res.data
    if isinstance(result, dict):
        return bool(result.get("allowed")), int(result.get("count", 0))
    return bool(result), get_api_usage_today()

def fetch_youtube_api_video_info(video_id: str):
    api_key = st.secrets["youtube_api_key"]
    res = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet,liveStreamingDetails", "id": video_id, "key": api_key},
        timeout=10,
    )
    res.raise_for_status()
    data = res.json()
    if not data.get("items"):
        return None
    
    snippet = data["items"][0]["snippet"]
    live = data["items"][0].get("liveStreamingDetails", {})
    published_at = snippet.get("publishedAt")
    actual = live.get("actualStartTime")
    scheduled = live.get("scheduledStartTime")
    
    info = {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "channel_name": snippet.get("channelTitle", ""),
        "channel_id": snippet.get("channelId", ""),
        "published_at": actual or scheduled or published_at,
        "youtube_published_at": published_at,
        "actual_start_time": actual,
        "scheduled_start_time": scheduled,
    }
    supabase.table("youtube_videos").upsert(info, on_conflict="video_id").execute()
    return info

def fetch_video_from_url(url: str, current_records: list):
    video_id = get_youtube_video_id(url)
    if not video_id:
        return None, "YouTube URLを認識できませんでした。"
    
    saved = next((r for r in current_records if r.get("video_id") == video_id), None)
    if saved:
        return saved, "saved"
    
    shared = get_shared_video(video_id)
    if shared:
        return shared, "shared"
    
    allowed, count = consume_api_quota()
    if not allowed:
        return None, f"本日のYouTube API利用上限（{API_DAILY_LIMIT}回）に達しています。明日またお試しください。"
    
    info = fetch_youtube_api_video_info(video_id)
    if not info:
        return None, "動画が見つかりませんでした。"
    return info, f"youtube:{count}"

# 設定データ・ユーザーデータの読み込み
settings = load_settings(USER_ID)
SAVING_RULES = settings["saving_rules"]
CONTENT_TYPE_ICONS = settings["content_type_icons"]
TAG_COLORS = settings["tag_colors"]

records = get_user_records(USER_ID)

# ==================================================
# 設定ポップアップ（ダイアログ）定義
# ==================================================
@st.dialog("⚙️ 推し活ルールの設定", width="large")
def open_settings_dialog():
    # 編集用データのセッション初期化
    if "editing_rules" not in st.session_state:
        st.session_state["editing_rules"] = [
            {
                "name": k,
                "amount": int(SAVING_RULES.get(k, 500)),
                "icon": str(CONTENT_TYPE_ICONS.get(k, "📺")),
            }
            for k in SAVING_RULES
        ]

    rules_list = st.session_state["editing_rules"]
    st.caption("最大12種類まで、推し活の種別・金額・アイコンを自由に変更できます。")

    # トグル形式で一覧表示
    updated_rules = []
    for i, item in enumerate(rules_list):
        expander_title = f"・{item['icon']} {item['name']}（{item['amount']:,}円）"
        with st.expander(expander_title, expanded=False):
            c_name, c_amount, c_icon = st.columns([2, 2, 1])
            with c_name:
                new_name = st.text_input("名称", value=item["name"], key=f"rule_name_{i}")
            with c_amount:
                new_amount = st.number_input("金額 (円)", min_value=0, step=100, value=item["amount"], key=f"rule_amount_{i}")
            with c_icon:
                new_icon = st.text_input("アイコン", value=item["icon"], key=f"rule_icon_{i}")
            
            updated_rules.append({"name": new_name, "amount": new_amount, "icon": new_icon})

    st.session_state["editing_rules"] = updated_rules

    # 項目の増減 (- / +)
    st.write("---")
    c_sub, c_add, _ = st.columns([1, 1, 2])
    with c_sub:
        if st.button("➖ 1つ減らす", disabled=len(st.session_state["editing_rules"]) <= 1, use_container_width=True):
            st.session_state["editing_rules"].pop()
            st.rerun()
    with c_add:
        if st.button("➕ 1つ増やす", disabled=len(st.session_state["editing_rules"]) >= 12, use_container_width=True):
            count = len(st.session_state["editing_rules"]) + 1
            st.session_state["editing_rules"].append({"name": f"新ルール{count}", "amount": 500, "icon": "✨"})
            st.rerun()

    st.divider()

    # 保存 / キャンセル
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 設定を保存", use_container_width=True, type="primary"):
            new_saving_rules = {}
            new_content_icons = {}
            for r in st.session_state["editing_rules"]:
                name = r["name"].strip()
                if name:
                    new_saving_rules[name] = int(r["amount"])
                    new_content_icons[name] = r["icon"]

            supabase.table("user_settings").upsert({
                "user_id": USER_ID,
                "saving_rules": new_saving_rules,
                "content_type_icons": new_content_icons,
                "tag_colors": TAG_COLORS,
            }, on_conflict="user_id").execute()

            st.cache_data.clear()
            st.session_state.pop("editing_rules", None)
            st.success("設定を更新しました！")
            st.rerun()

    with col_cancel:
        if st.button("キャンセル", use_container_width=True):
            st.session_state.pop("editing_rules", None)
            st.rerun()

# ==================================================
# サイドバー
# ==================================================
with st.sidebar:
    st.markdown("### 💖 推し活貯金")
    st.caption(USER_EMAIL or "ログイン中")
    
    if st.button("⚙️ 貯金ルールを設定", use_container_width=True):
        open_settings_dialog()
        
    st.caption(f"YouTube API：本日 {get_api_usage_today()} / {API_DAILY_LIMIT} 回")
    
    if st.button("🚪 ログアウト", use_container_width=True):
        st.logout()

# ==================================================
# メイン画面：ダッシュボード
# ==================================================
# ページの最上部にアンカーを配置
st.markdown('<div id="top"></div>', unsafe_allow_html=True)

st.title("💖 推し活貯金")
st.caption("YouTubeの推し活を記録して、楽しく貯金します ✨")

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
    fig = px.bar(chart_df, x="月表示", y="貯金額", text="貯金額", color_discrete_sequence=["#4DD7E3"])
    fig.update_traces(texttemplate="%{text:,}円", textposition="outside")
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20), xaxis_title=None, yaxis_title=None, showlegend=False)
    fig.update_yaxes(tickformat=",", rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ==================================================
# 動画登録
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
            info, source = fetch_video_from_url(external_url, records)
            if info:
                st.session_state["video_info"] = info
                st.session_state["video_already_saved"] = (source == "saved")
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
                info, source = fetch_video_from_url(url, records)
            if info:
                st.session_state["video_info"] = info
                st.session_state["video_already_saved"] = (source == "saved")
                st.success("YouTube情報を取得しました！" if source != "saved" else "🔖 登録済み動画を確認しました。")
            else:
                st.error(source)
        except requests.exceptions.HTTPError as e:
            st.error(f"YouTube APIエラー: {e}")
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
        detected_type, reason = auto_detect_content_type(info, url)
        if detected_type not in SAVING_RULES:
            detected_type = "個人配信"
        
        st.subheader("🏷️ 推し活の種類")
        st.write(f"🤖 自動判定：**{detected_type}**")
        st.caption(f"判定理由：{reason}")
        
        content_type_keys = list(SAVING_RULES.keys())
        content_type = st.selectbox("必要なら変更してください", content_type_keys, index=content_type_keys.index(detected_type), key="new_content_type")
        amount = int(SAVING_RULES[content_type])
        st.write(f"💰 貯金額：**{amount:,}円**")

        st.subheader("🏷️ タグ")
        tag_counts = {}
        for r in records:
            for tag in (r.get("tags") or "").split():
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        existing_tags = [t for t, _ in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))]
        suggested_tags = [] if detected_type == "個人配信" else suggest_tags(info)
        tag_options = list(existing_tags)
        for t in suggested_tags:
            if t not in tag_options:
                tag_options.append(t)
                
        selected_tags = st.multiselect("タグを選択", tag_options, default=suggested_tags, accept_new_options=True, key="new_record_tags")
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
                
                st.cache_data.clear()
                st.success(f"💖 {content_type}として{amount:,}円を貯金しました！")
                for k in ("video_info", "video_already_saved", "new_record_tags"):
                    st.session_state.pop(k, None)
                st.rerun()
            except Exception as e:
                if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                    st.warning("この動画はすでにあなたの記録に登録されています。")
                else:
                    st.error(f"保存に失敗しました: {e}")

# ==================================================
# カレンダー機能
# ==================================================
st.divider()
st.subheader("📅 配信・動画カレンダー")

if "calendar_month" not in st.session_state:
    st.session_state["calendar_month"] = now_jst().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
calendar_month = st.session_state["calendar_month"]

a, b, c = st.columns([1, 2, 1])
with a:
    if st.button("← 前月", use_container_width=True, key="calendar_prev"):
        year, month = calendar_month.year, calendar_month.month - 1
        if month == 0:
            year, month = year - 1, 12
        st.session_state["calendar_month"] = calendar_month.replace(year=year, month=month)
        st.rerun()
with b:
    st.markdown(f'<div style="text-align:center;font-size:1.2rem;font-weight:700;padding-top:.35rem;color:#00BFFF;">📅 {calendar_month.year}年 {calendar_month.month}月</div>', unsafe_allow_html=True)
with c:
    if st.button("次月 →", use_container_width=True, key="calendar_next"):
        year, month = calendar_month.year, calendar_month.month + 1
        if month == 13:
            year, month = year + 1, 1
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

calendar_checks_map = get_calendar_checks(USER_ID)

if st.session_state.get("calendar_action") == "confirm":
    st.markdown("**✓ 配信・動画がなかったことを確認**")
    year, month = calendar_month.year, calendar_month.month
    selectable = []
    for d in range(1, calendar.monthrange(year, month)[1] + 1):
        d_obj = date(year, month, d)
        d_str = d_obj.strftime("%Y-%m-%d")
        has_record = any(str(r.get("published_at", ""))[:10] == d_str for r in records)
        if not has_record and calendar_checks_map.get(d_str) != "confirmed_none":
            selectable.append(d_obj)
            
    options = {f"{d:%m/%d}（{'月火水木金土日'[d.weekday()]}）": d.strftime("%Y-%m-%d") for d in selectable}
    if options:
        selected = st.multiselect("確認する日付", list(options), key="calendar_confirm_dates")
        x, y = st.columns(2)
        with x:
            if st.button("✓ 選択した日を確認済みにする", use_container_width=True, key="confirm_calendar_dates"):
                updates = [{"user_id": USER_ID, "date": options[lbl], "status": "confirmed_none"} for lbl in selected]
                if updates:
                    supabase.table("calendar_checks").upsert(updates, on_conflict="user_id,date").execute()
                    st.cache_data.clear()
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
        edit_options = {f"{CONTENT_TYPE_ICONS.get(r['content_type'],'📺')} {format_published_date(r['published_at'])} {r['title']}": r for r in records}
        label = st.selectbox("編集する動画・配信", list(edit_options), key="calendar_edit_record")
        selected = edit_options[label]
        
        dt = parse_iso_jst(selected["published_at"])
        d1, d2 = st.columns(2)
        with d1:
            edited_date = st.date_input("日付", dt.date(), key=f"calendar_edit_date_{selected['id']}")
        with d2:
            edited_time = st.time_input("開始時刻", dt.time(), key=f"calendar_edit_time_{selected['id']}")
            
        x, y = st.columns(2)
        with x:
            if st.button("💾 日付・時刻を保存", use_container_width=True, key=f"save_calendar_edit_{selected['id']}"):
                edited = datetime.combine(edited_date, edited_time).replace(tzinfo=JST).isoformat()
                supabase.table("records").update({"published_at": edited}).eq("id", selected["id"]).eq("user_id", USER_ID).execute()
                st.cache_data.clear()
                st.session_state.pop("calendar_action", None)
                st.rerun()
        with y:
            if st.button("キャンセル", use_container_width=True, key="cancel_calendar_edit"):
                st.session_state.pop("calendar_action", None)
                st.rerun()

records_by_date = {}
for r in records:
    d = parse_iso_jst(r["published_at"]).strftime("%Y-%m-%d")
    records_by_date.setdefault(d, []).append(r)

cal = calendar.Calendar(firstweekday=6)
weeks = cal.monthdayscalendar(calendar_month.year, calendar_month.month)

for col, wd in zip(st.columns(7), ["日", "月", "火", "水", "木", "金", "土"]):
    col.markdown(f'<div style="text-align:center;font-weight:700;padding:.4rem 0;color:#4DD7E3;">{wd}</div>', unsafe_allow_html=True)

for week in weeks:
    cols = st.columns(7)
    for i, day_num in enumerate(week):
        with cols[i]:
            if day_num == 0:
                st.markdown('<div style="height:115px"></div>', unsafe_allow_html=True)
                continue
            
            d_str = date(calendar_month.year, calendar_month.month, day_num).strftime("%Y-%m-%d")
            day_records = records_by_date.get(d_str, [])
            check_status = calendar_checks_map.get(d_str)
            
            if day_records:
                cards = ""
                for item in day_records:
                    icon = html.escape(CONTENT_TYPE_ICONS.get(item["content_type"], "📺"))
                    typ = html.escape(str(item["content_type"]))
                    title = str(item["title"])
                    short_title = title[:27] + "…" if len(title) > 28 else title
                    safe_title = html.escape(short_title)
                    safe_url = html.escape(str(item["url"]), quote=True)
                    cards += f'<div style="margin-top:.25rem;padding:.1rem 0;text-align:center;"><div style="font-size:.88rem;font-weight:600;color:#4DD7E3;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{icon} {typ}</div><div style="font-size:.65rem;margin-top:.18rem;line-height:1.25;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;"><a href="{safe_url}" target="_blank" style="color:#4DD7E3;text-decoration:none;">{safe_title}</a></div></div>'
                st.html(f'<div style="background:#E0FFFF;border:1px solid #00BFFF;border-radius:12px;min-height:105px;padding:.4rem .3rem;text-align:center;margin-bottom:.35rem;box-sizing:border-box;"><div style="display:inline-flex;align-items:center;justify-content:center;width:1.65rem;height:1.65rem;border-radius:50%;background:#FFFFFF;color:#4DD7E3;font-size:.78rem;font-weight:700;margin-bottom:.1rem;">{day_num}</div>{cards}</div>')
            elif check_status == "confirmed_none":
                st.html(f'<div style="background:#F3F8F3;border:1px solid #C7DEC7;border-radius:12px;min-height:105px;padding:.4rem .3rem;text-align:center;margin-bottom:.35rem;"><div style="font-weight:700;color:#5A4650;">{day_num}</div><div style="font-size:1.25rem;margin-top:.55rem;color:#719471;">✓</div><div style="font-size:.68rem;color:#718071;">配信なし確認済み</div></div>')
            else:
                st.html(f'<div style="background:#FFFFFF;border:1px solid #E8E8E8;border-radius:12px;min-height:105px;padding:.4rem .3rem;text-align:center;margin-bottom:.35rem;"><div style="font-weight:600;font-size:.82rem;color:#4DD7E3;">{day_num}</div></div>')

# ==================================================
# 検索・一覧画面
# ==================================================
st.divider()
st.subheader("🔎 保存済みデータを検索")
search_text = st.text_input("キーワード", placeholder="タイトル・配信枠・タグなど", key="search_text")

all_tag_counts = {}
for r in records:
    for tag in (r.get("tags") or "").split():
        all_tag_counts[tag] = all_tag_counts.get(tag, 0) + 1
sorted_tags = [t for t, _ in sorted(all_tag_counts.items(), key=lambda x: (-x[1], x[0]))]

st.markdown('<div class="tag-search-title">🎀 タグから探す</div>', unsafe_allow_html=True)
selected_tag = st.session_state.get("selected_search_tag")

if sorted_tags:
    tag_css_list = []
    for i, tag in enumerate(sorted_tags):
        color = TAG_SEARCH_COLORS[i % len(TAG_SEARCH_COLORS)]
        border = "2px solid #555555" if selected_tag == tag else f"1px solid {color}"
        tag_css_list.append(
            f'.st-key-search_tag_{i} button {{ '
            f'background-color: {color} !important; '
            f'border: {border} !important; '
            f'color: #5A4650 !important; '
            f'border-radius: 999px !important; '
            f'font-weight: 600 !important; '
            f'padding: .35rem .8rem !important; '
            f'margin: 0 !important; }}'
        )
    st.markdown(f"<style>{''.join(tag_css_list)}</style>", unsafe_allow_html=True)
    
    for start in range(0, len(sorted_tags), 5):
        row_tags = sorted_tags[start:start+5]
        cols = st.columns(len(row_tags))
        for idx, (col, tag) in enumerate(zip(cols, row_tags)):
            with col:
                if st.button(tag, key=f"search_tag_{start+idx}", use_container_width=True):
                    st.session_state["selected_search_tag"] = None if selected_tag == tag else tag
                    st.rerun()

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
    header = st.columns([4, 1.4, 1.5, 1, 1.2, 1.8, .8])
    for col, label in zip(header, ["**タイトル**", "**配信枠**", "**種別**", "**金額**", "**公開日**", "**タグ**", "**編集**"]):
        col.markdown(label)
    st.divider()

    for r in filtered:
        record_id = r["id"]
        row = st.columns([4, 1.4, 1.5, 1, 1.2, 1.8, .8])
        with row[0]: st.markdown(f"[**{html.escape(str(r['title']))}**]({r['url']})")
        with row[1]: st.write(r["channel_name"])
        with row[2]: st.write(r["content_type"])
        with row[3]: st.write(f"{int(r['amount']):,}円")
        with row[4]: st.write(format_published_date(r["published_at"]))
        with row[5]:
            if r.get("tags"):
                st.markdown(display_tags(r["tags"], TAG_COLORS), unsafe_allow_html=True)
            else:
                st.caption("タグなし")
        with row[6]:
            if st.button("編集", key=f"edit_{record_id}"):
                st.session_state["editing_record_id"] = record_id
                st.rerun()

        if st.session_state.get("editing_record_id") == record_id:
            st.markdown('<div style="background:#FFF8FB;border:1px solid #F0C6D8;border-radius:12px;padding:1rem;margin:.3rem 0 1rem;">', unsafe_allow_html=True)
            st.markdown("### ✏️ 記録を編集")
            st.caption(r["title"])
            
            saving_type_keys = list(SAVING_RULES.keys())
            edited_type = st.selectbox("種別", saving_type_keys, index=saving_type_keys.index(r["content_type"]), key=f"editing_content_type_{record_id}")
            edited_amount = int(SAVING_RULES[edited_type])
            st.write(f"💰 貯金額：**{edited_amount:,}円**")
            
            current_tags = (r.get("tags") or "").split()
            available_tags = list(sorted_tags)
            for t in current_tags:
                if t not in available_tags:
                    available_tags.append(t)
                    
            edited_tags = st.multiselect("タグ", available_tags, default=current_tags, accept_new_options=True, key=f"editing_tags_{record_id}")
            normalized_edited_tags = normalize_tags(edited_tags)
            if normalized_edited_tags:
                st.markdown(display_tags(normalized_edited_tags, TAG_COLORS), unsafe_allow_html=True)
            else:
                st.caption("タグなし")
                
            x, y = st.columns(2)
            with x:
                if st.button("💾 保存", use_container_width=True, key=f"save_record_{record_id}"):
                    supabase.table("records").update({
                        "content_type": edited_type, 
                        "amount": edited_amount, 
                        "tags": normalized_edited_tags
                    }).eq("id", record_id).eq("user_id", USER_ID).execute()
                    
                    st.cache_data.clear()
                    st.session_state.pop("editing_record_id", None)
                    st.rerun()
            with y:
                if st.button("キャンセル", use_container_width=True, key=f"cancel_record_{record_id}"):
                    st.session_state.pop("editing_record_id", None)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

# ==================================================
# 右下固定「一番上へ」ボタン要素
# ==================================================
st.markdown('<a href="#top" class="back-to-top">↑ 一番上へ</a>', unsafe_allow_html=True)
