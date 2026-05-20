"""
地球物理知识竞赛刷题系统
导航方式：侧边栏选择（避免 Streamlit tab 双渲染问题）
"""
import json
import os
import streamlit as st

from gist_client import GistClient

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="地球物理刷题系统",
    page_icon="🌏",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── load questions ─────────────────────────────────────────────────────────────
@st.cache_data
def load_questions():
    path = os.path.join(os.path.dirname(__file__), "questions_data.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

QUESTIONS = load_questions()
TOTAL = len(QUESTIONS)


# ── gist client ───────────────────────────────────────────────────────────────
def get_gist_client():
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        gist_id = st.secrets.get("GIST_ID", "")
        if token and gist_id and token != "your_github_pat_here":
            return GistClient(token, gist_id)
    except Exception:
        pass
    return None


# ── session state defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "username": "",
    "logged_in": False,
    "user_state": {},   # {str(qid): 0|1}
    # main tab state
    "main_queue": [],
    "main_idx": 0,
    "main_show": False,
    "main_answered": False,
    "main_last": "",
    # wrong tab state
    "wrong_queue": [],
    "wrong_idx": 0,
    "wrong_show": False,
    "wrong_answered": False,
    "wrong_last": "",
    # navigation
    "nav": "📚 主线刷题",
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── gist i/o ──────────────────────────────────────────────────────────────────
def load_user_state(username):
    client = get_gist_client()
    return client.load_state(username) if client else {}


def save_user_state():
    client = get_gist_client()
    if client:
        client.save_state(st.session_state.username, st.session_state.user_state)


# ── queue helpers ─────────────────────────────────────────────────────────────
def build_main_queue():
    return [str(i) for i in range(1, TOTAL + 1) if str(i) in QUESTIONS]


def build_wrong_queue():
    return [
        str(i) for i in range(1, TOTAL + 1)
        if st.session_state.user_state.get(str(i)) == 0
    ]


def mark_correct(qid):
    st.session_state.user_state[qid] = 1
    save_user_state()


def mark_wrong(qid):
    st.session_state.user_state[qid] = 0
    save_user_state()


# ── UI components ─────────────────────────────────────────────────────────────
def show_stats():
    state = st.session_state.user_state
    correct = sum(1 for v in state.values() if v == 1)
    wrong = sum(1 for v in state.values() if v == 0)
    done = correct + wrong
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总题数", TOTAL)
    col2.metric("已做", done)
    col3.metric("✅ 已掌握", correct)
    col4.metric("❌ 错题", wrong)


def render_question_header(q):
    cat = "🌊 地震" if q["category"] == "地震" else "🔩 测井"
    typ = {"fill": "填空", "choice": "选择", "judge": "判断"}.get(q["type"], "简答")
    st.markdown(f"**[{cat} · {typ}]** `Q{q['id']}/{TOTAL}`")
    st.markdown(f"### {q['q']}")


def practice_panel(prefix: str):
    """
    Render one practice panel.
    prefix = "main" or "wrong"
    Uses session_state[prefix + "_*"] for all state.
    """
    queue_key = f"{prefix}_queue"
    idx_key = f"{prefix}_idx"
    show_key = f"{prefix}_show"
    answered_key = f"{prefix}_answered"
    last_key = f"{prefix}_last"

    queue = st.session_state[queue_key]
    idx = st.session_state[idx_key]

    if idx >= len(queue):
        if prefix == "wrong":
            st.success("🎉 错题全部消灭！")
            if st.button("刷新错题列表", key=f"{prefix}_refresh"):
                st.session_state[queue_key] = build_wrong_queue()
                st.session_state[idx_key] = 0
                st.session_state[show_key] = False
                st.session_state[answered_key] = False
                st.rerun()
        else:
            st.success("🎉 全部题目刷完！去错题轰炸区巩固吧。")
            if st.button("重头再刷一遍", key=f"{prefix}_restart"):
                st.session_state[idx_key] = 0
                st.session_state[show_key] = False
                st.session_state[answered_key] = False
                st.rerun()
        return

    qid = queue[idx]
    q = QUESTIONS[qid]
    render_question_header(q)
    st.markdown("---")

    # Progress within this queue
    st.caption(f"本轮进度：{idx + 1} / {len(queue)}")

    # ── Choice question with options ──────────────────────────────────────────
    if q["opts"]:  # show radio whenever clean options exist, regardless of section type
        if not st.session_state[answered_key]:
            choice = st.radio(
                "选择答案：",
                q["opts"],
                key=f"{prefix}_choice_{qid}_{idx}",
                index=None,
            )
            if st.button("提交", key=f"{prefix}_submit_{qid}", type="primary"):
                if choice is None:
                    st.warning("请先选择一个选项")
                else:
                    st.session_state[last_key] = choice[0]
                    st.session_state[answered_key] = True
                    st.rerun()
        else:
            user_letter = st.session_state[last_key].upper()
            correct_ans = q["a"].strip()
            correct_letter = correct_ans[0].upper() if correct_ans else ""

            if user_letter == correct_letter:
                st.success(f"✅ 回答正确！")
                st.info(f"参考答案：**{correct_ans}**")
                mark_correct(qid)
            else:
                st.error(f"❌ 错误。你选了 **{user_letter}**")
                st.info(f"正确答案：**{correct_ans}**")
                mark_wrong(qid)

            if st.button("下一题 →", key=f"{prefix}_next_{qid}", type="primary"):
                st.session_state[idx_key] += 1
                st.session_state[show_key] = False
                st.session_state[answered_key] = False
                st.session_state[last_key] = ""
                st.rerun()

    # ── Fill / self-judge ─────────────────────────────────────────────────────
    else:
        if not st.session_state[show_key]:
            user_ans = st.text_input(
                "你的答案（可留空直接查看参考答案）：",
                key=f"{prefix}_fill_{qid}_{idx}",
            )
            if st.button("查看参考答案", key=f"{prefix}_reveal_{qid}", type="primary"):
                st.session_state[last_key] = user_ans
                st.session_state[show_key] = True
                st.rerun()
        else:
            user_ans = st.session_state[last_key]
            if user_ans:
                st.info(f"📝 你的回答：**{user_ans}**")
            st.success(f"✅ 参考答案：**{q['a']}**")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 答对了", key=f"{prefix}_ok_{qid}", type="primary", use_container_width=True):
                    mark_correct(qid)
                    st.session_state[idx_key] += 1
                    st.session_state[show_key] = False
                    st.session_state[answered_key] = False
                    st.session_state[last_key] = ""
                    st.rerun()
            with col2:
                if st.button("❌ 答错了", key=f"{prefix}_fail_{qid}", use_container_width=True):
                    mark_wrong(qid)
                    st.session_state[idx_key] += 1
                    st.session_state[show_key] = False
                    st.session_state[answered_key] = False
                    st.session_state[last_key] = ""
                    st.rerun()


# ── screens ───────────────────────────────────────────────────────────────────
def login_screen():
    st.title("🌏 地球物理知识竞赛刷题系统")
    st.markdown("共 **161 道题**（地震 141 题 · 测井 20 题）")
    st.markdown("---")

    username = st.text_input(
        "请输入用户名（相同用户名在任意设备可同步进度）",
        placeholder="例如：zhangsan",
    )
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
        st.info(
            "💡 **提示**：当前未配置 GitHub Gist，进度仅在本次会话有效。\n\n"
            "配置方法：编辑 `.streamlit/secrets.toml`，填入 `GITHUB_TOKEN` 和 `GIST_ID`。"
        )


def main_screen():
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.username}**")
        st.markdown("---")
        nav = st.radio(
            "导航",
            ["📚 主线刷题", "🔥 错题轰炸", "⚙️ 设置"],
            key="nav",
        )
        st.markdown("---")
        show_stats()

    # ── 主线刷题 ──────────────────────────────────────────────────────────────
    if st.session_state.nav == "📚 主线刷题":
        st.header("📚 主线刷题")
        if not st.session_state.main_queue:
            st.session_state.main_queue = build_main_queue()
        practice_panel("main")

    # ── 错题轰炸 ──────────────────────────────────────────────────────────────
    elif st.session_state.nav == "🔥 错题轰炸":
        st.header("🔥 错题轰炸区")
        wrong_q = build_wrong_queue()
        if not wrong_q:
            st.info("🎉 目前没有错题！先去主线刷题累积错题吧。")
        else:
            # Rebuild queue if it's stale or empty
            if (not st.session_state.wrong_queue or
                    set(st.session_state.wrong_queue) != set(wrong_q)):
                st.session_state.wrong_queue = wrong_q
                st.session_state.wrong_idx = 0
                st.session_state.wrong_show = False
                st.session_state.wrong_answered = False
            practice_panel("wrong")

    # ── 设置 ─────────────────────────────────────────────────────────────────
    elif st.session_state.nav == "⚙️ 设置":
        st.header("⚙️ 设置与重置")
        state = st.session_state.user_state
        correct_ids = [qid for qid, v in state.items() if v == 1]
        wrong_ids = [qid for qid, v in state.items() if v == 0]

        st.markdown(f"**用户名：** `{st.session_state.username}`")
        st.markdown("---")
        st.subheader("🔥 赛前极限复活")
        st.write(
            f"将 **{len(correct_ids)}** 道已掌握题目重新打入错题本，"
            "进行赛前最后一轮高强度突击。"
        )
        if st.button("⚡ 一键复活所有已掌握题目", type="primary"):
            for qid in correct_ids:
                st.session_state.user_state[qid] = 0
            save_user_state()
            # Reset wrong queue
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
        st.subheader("📊 Gist 配置状态")
        client = get_gist_client()
        if client:
            st.success("✅ GitHub Gist 已配置，进度多端同步已开启")
        else:
            st.warning(
                "⚠️ GitHub Gist 未配置，进度仅在当前会话有效\n\n"
                "在 `.streamlit/secrets.toml` 中填入 `GITHUB_TOKEN` 和 `GIST_ID`"
            )


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    if not st.session_state.logged_in:
        login_screen()
    else:
        main_screen()


main()
