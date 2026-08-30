import streamlit as st
import requests
from datetime import datetime

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="比特币实时价格",
    page_icon="₿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------- 自定义样式 ----------
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: white;
    }
    .stApp {
        background: transparent;
    }
    .price-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        border-radius: 1rem;
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .stMetric {
        background: transparent !important;
    }
    .stMetric label {
        color: #ccc !important;
        font-size: 1rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stMetric .value {
        font-size: 3rem !important;
        font-weight: 700 !important;
    }
    .stMetric .delta {
        font-size: 1.3rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- 辅助函数 ----------
def get_bitcoin_price(version: int = 0):
    """
    从 CoinGecko API 获取比特币价格数据。
    version 参数用于使缓存失效。
    返回字典：{price, change_pct, change_abs, timestamp}
    失败时返回 None。
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        # 处理限流状态码 429
        if response.status_code == 429:
            st.error("⏳ 请求频率过高，请稍后再试")
            return None
        response.raise_for_status()
        data = response.json()
        btc = data.get("bitcoin", {})
        price = btc.get("usd")
        change_pct = btc.get("usd_24h_change")  # 百分比值，如 0.052 代表 5.2%
        if price is None or change_pct is None:
            # 数据不完整，直接返回 None，避免使用异常控制逻辑
            st.error("❌ 获取到的数据异常，请稍后重试")
            return None
        # 计算涨跌额（美元）
        change_abs = price * change_pct / 100.0
        return {
            "price": round(price, 2),
            "change_pct": round(change_pct, 2),
            "change_abs": round(change_abs, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except requests.exceptions.Timeout:
        st.error("⌛ 请求超时，请检查网络连接后重试")
        return None
    except requests.exceptions.RequestException:
        st.error("❌ 无法获取价格，请稍后重试")
        return None
    # 其他意外异常（如 JSON 解析错误）由外层捕获，但这里已经覆盖了主要场景

# 带缓存的版本（30秒内不重复请求）
@st.cache_data(ttl=30, show_spinner=False)
def cached_get_price(version: int):
    return get_bitcoin_price(version)

# ---------- 会话状态初始化 ----------
if "refresh_version" not in st.session_state:
    st.session_state.refresh_version = 0
if "last_price_data" not in st.session_state:
    st.session_state.last_price_data = None

# ---------- 主界面 ----------
st.title("₿ 比特币实时价格")
st.markdown("---")

# 按钮触发刷新
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    if st.button("🔄 刷新数据", use_container_width=True, type="primary"):
        st.session_state.refresh_version += 1

# 显示数据
st.markdown('<div class="price-container">', unsafe_allow_html=True)

with st.spinner("正在获取最新价格..."):
    data = cached_get_price(st.session_state.refresh_version)

if data:
    # 更新最近成功的数据
    st.session_state.last_price_data = data
    # 提取数据
    price = data["price"]
    change_pct = data["change_pct"]
    change_abs = data["change_abs"]
    timestamp = data["timestamp"]

    # 格式化 delta 字符串
    if change_pct >= 0:
        delta_str = f"+${change_abs:,.2f} (+{change_pct:.2f}%)"
        arrow = "🟢"
    else:
        delta_str = f"-${abs(change_abs):,.2f} ({change_pct:.2f}%)"
        arrow = "🔴"

    # 使用 st.metric 展示核心指标
    st.metric(
        label="比特币 (BTC) / 美元",
        value=f"${price:,.2f}",
        delta=f"{delta_str} {arrow}",
        delta_color="normal"  # 自动根据正负变色
    )
    # 显示更新时间
    st.caption(f"最后更新: {timestamp} (数据源: CoinGecko)")
else:
    # 获取失败
    if st.session_state.last_price_data is None:
        # 从未成功获取过
        st.info("⏳ 未能获取初始数据，请点击「刷新数据」按钮重试")
    else:
        # 之前有成功数据，但本次失败，显示旧数据（同时给出警告）
        old = st.session_state.last_price_data
        price = old["price"]
        change_pct = old["change_pct"]
        change_abs = old["change_abs"]
        timestamp = old["timestamp"]
        # 格式化
        if change_pct >= 0:
            delta_str = f"+${change_abs:,.2f} (+{change_pct:.2f}%)"
            arrow = "🟢"
        else:
            delta_str = f"-${abs(change_abs):,.2f} ({change_pct:.2f}%)"
            arrow = "🔴"
        st.metric(
            label="比特币 (BTC) / 美元 (缓存)",
            value=f"${price:,.2f}",
            delta=f"{delta_str} {arrow}",
            delta_color="normal"
        )
        st.caption(f"📡 获取最新数据失败，显示缓存数据 (更新于 {timestamp})")
        st.info("💡 点击「刷新数据」重新获取最新价格")

st.markdown('</div>', unsafe_allow_html=True)

# ---------- 额外说明 ----------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #aaa; font-size: 0.85rem;">
        💡 数据每30秒自动缓存，手动刷新可立即获取最新数据。<br>
        价格包含24小时涨跌幅和涨跌额，绿色表示上涨，红色表示下跌。
    </div>
    """,
    unsafe_allow_html=True
)