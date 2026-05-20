"""地球物理知识竞赛刷题系统"""
import json
import os

import streamlit as st

from gist_client import GistClient

st.set_page_config(
    page_title="地球物理刷题系统",
    page_icon="🌏",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── load questions (plain file read, no decorator) ────────────────────────────
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(_HERE, "questions_data.json"), encoding="utf-8") as _f:
        QUESTIONS: dict = json.load(_f)
    TOTAL: int = len(QUESTIONS)
except Exception as _load_err:
    st.error(f"题库加载失败：{_load_err}")
    st.stop()

# ── session state defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "username": "",
    "logged_in": False,
    "user_state": {},
    "main_queue": [],
    "main_idx": 0,
    "main_show": False,
    "main_answered": False,
    "main_last": "",
    "wrong_queue": [],
    "wrong_idx": 0,
    "wrong_show": False,
    "wrong_answered": False,
    "wrong_last": "",
    "nav": "📚 主线刷题",
}


def init_session():
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── gist helpers ──────────────────────────────────────────────────────────────
def get_gist_client():
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        gist_id = st.secrets.get("GIST_ID", "")
        if token and gist_id and not token.startswith("your_"):
            return GistClient(token, gist_id)
    except Exception:
        pass
    return None


def load_user_state(username: str) -> dict:
    client = get_gist_client()
    return client.load_state(username) if client else {}


def save_user_state():
    client = get_gist_client()
    if client:
        client.save_state(st.session_state.username, st.session_state.user_state)


# ── queue builders ────────────────────────────────────────────────────────────
def build_main_queue():
    return [str(i) for i in range(1, TOTAL + 1) if str(i) in QUESTIONS]


def build_wrong_queue():
    return [
        str(i) for i in range(1, TOTAL + 1)
        if st.session_state.user_state.get(str(i)) == 0
    ]


# ── state helpers ─────────────────────────────────────────────────────────────
def mark_correct(qid: str):
    st.session_state.user_state[qid] = 1
    save_user_state()


def mark_wrong(qid: str):
    st.session_state.user_state[qid] = 0
    save_user_state()


# ── UI components ─────────────────────────────────────────────────────────────
def show_stats():
    state = st.session_state.user_state
    correct = sum(1 for v in state.values() if v == 1)
    wrong = sum(1 for v in state.values() if v == 0)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总题数", TOTAL)
    col2.metric("已做", correct + wrong)
    col3.metric("✅ 已掌握", correct)
    col4.metric("❌ 错题", wrong)


def render_q_header(q: dict):
    cat = "🌊 地震" if q["category"] == "地震" else "🔩 测井"
    typ = {"fill": "填空", "choice": "选择", "judge": "判断"}.get(q["type"], "简答")
    st.markdown(f"**[{cat} · {typ}]** `Q{q['id']}/{TOTAL}`")
    st.markdown(f"### {q['q']}")


def practice_panel(prefix: str):
    queue = st.session_state[f"{prefix}_queue"]
    idx   = st.session_state[f"{prefix}_idx"]
    show  = f"{prefix}_show"
    done  = f"{prefix}_answered"
    last  = f"{prefix}_last"

    if idx >= len(queue):
        if prefix == "wrong":
            st.success("🎉 错题全部消灭！")
            if st.button("刷新错题列表", key=f"{prefix}_refresh"):
                st.session_state[f"{prefix}_queue"] = build_wrong_queue()
                st.session_state[f"{prefix}_idx"] = 0
                st.session_state[show] = False
                st.session_state[done] = False
                st.rerun()
        else:
            st.success("🎉 全部题目刷完！")
            if st.button("重头再刷", key=f"{prefix}_restart"):
                st.session_state[f"{prefix}_idx"] = 0
                st.session_state[show] = False
                st.session_state[done] = False
                st.rerun()
        return

    qid = queue[idx]
    q = QUESTIONS[qid]
    render_q_header(q)
    st.markdown("---")
    st.caption(f"本轮进度：{idx + 1} / {len(queue)}")

    if q["opts"]:
        # ── multiple choice ───────────────────────────────────────────────────
        if not st.session_state[done]:
            choice = st.radio("选择答案：", q["opts"],
                              key=f"{prefix}_r_{qid}_{idx}", index=None)
            if st.button("提交", key=f"{prefix}_sub_{qid}", type="primary"):
                if choice is None:
                    st.warning("请先选择一个选项")
                else:
                    st.session_state[last] = choice[0]
                    st.session_state[done] = True
                    st.rerun()
        else:
            user_l = st.session_state[last].upper()
            corr_l = q["a"].strip()[0].upper() if q["a"].strip() else ""
            if user_l == corr_l:
                st.success("✅ 回答正确！")
                mark_correct(qid)
            else:
                st.error(f"❌ 错误。你选了 **{user_l}**")
                mark_wrong(qid)
            st.info(f"参考答案：**{q['a']}**")
            if st.button("下一题 →", key=f"{prefix}_nxt_{qid}", type="primary"):
                st.session_state[f"{prefix}_idx"] += 1
                st.session_state[show] = False
                st.session_state[done] = False
                st.session_state[last] = ""
                st.rerun()
    else:
        # ── fill / self-judge ─────────────────────────────────────────────────
        if not st.session_state[show]:
            ans = st.text_input("你的答案（可留空直接查看参考答案）：",
                                key=f"{prefix}_fi_{qid}_{idx}")
            if st.button("查看参考答案", key=f"{prefix}_rev_{qid}", type="primary"):
                st.session_state[last] = ans
                st.session_state[show] = True
                st.rerun()
        else:
            if st.session_state[last]:
                st.info(f"📝 你的回答：**{st.session_state[last]}**")
            st.success(f"✅ 参考答案：**{q['a']}**")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 答对了", key=f"{prefix}_ok_{qid}",
                             type="primary", use_container_width=True):
                    mark_correct(qid)
                    st.session_state[f"{prefix}_idx"] += 1
                    st.session_state[show] = False
                    st.session_state[done] = False
                    st.session_state[last] = ""
                    st.rerun()
            with c2:
                if st.button("❌ 答错了", key=f"{prefix}_fail_{qid}",
                             use_container_width=True):
                    mark_wrong(qid)
                    st.session_state[f"{prefix}_idx"] += 1
                    st.session_state[show] = False
                    st.session_state[done] = False
                    st.session_state[last] = ""
                    st.rerun()


# ── screens ───────────────────────────────────────────────────────────────────
def login_screen():
    st.title("🌏 地球物理知识竞赛刷题系统")
    st.markdown("共 **161 道题**（地震 141 题 · 测井 20 题）")
    st.markdown("---")
    username = st.text_input("请输入用户名（同一用户名在任意设备可同步进度）",
                             placeholder="例如：zhangsan")
    if st.button("进入系统 →", type="primary"):
        name = username.strip()
        if not name:
            st.warning("用户名不能为空")
        else:
            with st.spinner("同步学习进度中…"):
                state = load_user_state(name)
            st.session_state.username = name
            st.session_state.user_state = state
            st.session_state.logged_in = True
            st.session_state.main_queue = build_main_queue()
            st.session_state.main_idx = 0
            st.session_state.wrong_queue = build_wrong_queue()
            st.session_state.wrong_idx = 0
            st.rerun()
    if not get_gist_client():
        st.info("💡 未配置 GitHub Gist，进度仅在本次会话有效。")


def main_screen():
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.username}**")
        st.markdown("---")
        st.radio("导航", ["📚 主线刷题", "🔥 错题轰炸", "⚙️ 设置"], key="nav")
        st.markdown("---")
        show_stats()

    nav = st.session_state.nav

    if nav == "📚 主线刷题":
        st.header("📚 主线刷题")
        if not st.session_state.main_queue:
            st.session_state.main_queue = build_main_queue()
        practice_panel("main")

    elif nav == "🔥 错题轰炸":
        st.header("🔥 错题轰炸区")
        wq = build_wrong_queue()
        if not wq:
            st.info("🎉 目前没有错题！先去主线刷题积累错题吧。")
        else:
            cur = set(st.session_state.wrong_queue)
            if not cur or cur != set(wq):
                st.session_state.wrong_queue = wq
                st.session_state.wrong_idx = 0
                st.session_state.wrong_show = False
                st.session_state.wrong_answered = False
            practice_panel("wrong")

    elif nav == "⚙️ 设置":
        st.header("⚙️ 设置与重置")
        state = st.session_state.user_state
        correct_ids = [q for q, v in state.items() if v == 1]
        st.markdown(f"**用户名：** `{st.session_state.username}`")
        st.markdown("---")
        st.subheader("🔥 赛前极限复活")
        st.write(f"将 **{len(correct_ids)}** 道已掌握题目重新打入错题本，进行极限速刷。")
        if st.button("⚡ 一键复活所有已掌握题目", type="primary"):
            for qid in correct_ids:
                st.session_state.user_state[qid] = 0
            save_user_state()
            st.session_state.wrong_queue = build_wrong_queue()
            st.session_state.wrong_idx = 0
            st.success(f"已将 {len(correct_ids)} 道题重置回错题本！")
            st.rerun()
        st.markdown("---")
        st.subheader("🗑️ 完全重置")
        if st.button("清空所有进度（不可恢复）"):
            st.session_state.user_state = {}
            save_user_state()
            st.session_state.main_queue = build_main_queue()
            st.session_state.main_idx = 0
            st.session_state.wrong_queue = []
            st.session_state.wrong_idx = 0
            st.success("进度已清空！")
            st.rerun()
        st.markdown("---")
        if st.button("退出登录"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.markdown("---")
        if get_gist_client():
            st.success("✅ GitHub Gist 已配置，多端同步已开启")
        else:
            st.warning("⚠️ GitHub Gist 未配置，进度仅在当前会话有效")


# ── run ───────────────────────────────────────────────────────────────────────
init_session()
if not st.session_state.logged_in:
    login_screen()
else:
    main_screen()
