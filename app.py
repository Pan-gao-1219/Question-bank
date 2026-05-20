"""地球物理知识竞赛刷题系统"""
import json
import os

import streamlit as st

from scores_client import ScoresClient

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

CATEGORIES = ("地震", "测井")
CATEGORY_ICONS = {"地震": "🌊", "测井": "🔩"}
CATEGORY_PREFIX = {"地震": "seismic", "测井": "logging"}
CATEGORY_BY_PREFIX = {v: k for k, v in CATEGORY_PREFIX.items()}
QUESTION_IDS = sorted(QUESTIONS, key=lambda qid: int(qid))

# ── session state defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "username": "",
    "logged_in": False,
    "admin_logged_in": False,
    "sync_ok": False,
    "sync_error": "",
    "user_state": {},
    "main_queue": [],
    "main_idx": 0,
    "main_show": False,
    "main_answered": False,
    "main_last": "",
    "seismic_queue": [],
    "seismic_idx": 0,
    "seismic_show": False,
    "seismic_answered": False,
    "seismic_last": "",
    "logging_queue": [],
    "logging_idx": 0,
    "logging_show": False,
    "logging_answered": False,
    "logging_last": "",
    "wrong_queue": [],
    "wrong_idx": 0,
    "wrong_show": False,
    "wrong_answered": False,
    "wrong_last": "",
    "wrong_category": "全部",
    "nav": "🌊 地震刷题",
}


def init_session():
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_secret_section(name: str):
    try:
        section = st.secrets.get(name, {})
        return section if hasattr(section, "get") else {}
    except Exception:
        return {}


# ── score storage helpers ─────────────────────────────────────────────────────
def get_scores_client():
    try:
        github = get_secret_section("github")
        token = str(github.get("token", st.secrets.get("GITHUB_TOKEN", ""))).strip()
        repo = str(
            github.get("repo", st.secrets.get("GITHUB_REPO", "Pan-gao-1219/Question-bank"))
        ).strip()
        branch = str(github.get("branch", st.secrets.get("GITHUB_BRANCH", "main"))).strip()
        scores_path = str(
            github.get("scores_path", st.secrets.get("SCORES_PATH", "data/scores.json"))
        ).strip()
        invalid_token = (
            token in {"xxxx", "your_token"}
            or token.lower().startswith("your_")
            or token.lower().startswith("your-")
        )
        if token and repo and scores_path and not invalid_token:
            return ScoresClient(token, repo, branch or "main", scores_path)
    except Exception:
        pass
    return None


def get_admin_password() -> str:
    try:
        app = get_secret_section("app")
        return str(app.get("admin_password", st.secrets.get("ADMIN_PASSWORD", ""))).strip()
    except Exception:
        return ""


def load_user_state(username: str) -> dict:
    client = get_scores_client()
    if not client:
        st.session_state.sync_ok = False
        st.session_state.sync_error = "未配置 [github].token，进度只保存在本次会话。"
        return {}
    state = client.load_state(username)
    st.session_state.sync_ok = not bool(client.last_error)
    st.session_state.sync_error = client.last_error
    return state


def load_all_user_states() -> dict:
    client = get_scores_client()
    if not client:
        st.session_state.sync_error = "未配置 [github].token。"
        return {}
    users = client.load_all_states()
    st.session_state.sync_error = client.last_error
    return users


def save_user_state():
    client = get_scores_client()
    if not client:
        st.session_state.sync_ok = False
        st.session_state.sync_error = "未配置 [github].token，进度只保存在本次会话。"
        return False
    ok = client.save_state(st.session_state.username, st.session_state.user_state)
    st.session_state.sync_ok = ok
    st.session_state.sync_error = "" if ok else client.last_error
    return ok


# ── queue builders ────────────────────────────────────────────────────────────
def question_ids(category: str | None = None):
    return [
        qid for qid in QUESTION_IDS
        if category is None or QUESTIONS[qid].get("category") == category
    ]


def build_main_queue():
    return question_ids()


def build_category_queue(category: str):
    return question_ids(category)


def active_wrong_category():
    category = st.session_state.get("wrong_category", "全部")
    return None if category == "全部" else category


def build_wrong_queue(category: str | None = None):
    qids = set(question_ids(category))
    return [
        qid for qid in question_ids(category)
        if qid in qids and st.session_state.user_state.get(qid) == 0
    ]


# ── state helpers ─────────────────────────────────────────────────────────────
def mark_correct(qid: str):
    st.session_state.user_state[qid] = 1
    save_user_state()


def mark_wrong(qid: str):
    st.session_state.user_state[qid] = 0
    save_user_state()


def summarize_state(state: dict, category: str | None = None) -> dict:
    qids = set(question_ids(category))
    correct = sum(1 for qid in qids if state.get(qid) == 1)
    wrong = sum(1 for qid in qids if state.get(qid) == 0)
    return {
        "total": len(qids),
        "done": correct + wrong,
        "correct": correct,
        "wrong": wrong,
    }


def resume_index(queue: list[str]) -> int:
    """Return the first question that has not been mastered yet."""
    state = st.session_state.user_state
    for idx, qid in enumerate(queue):
        if state.get(qid) != 1:
            return idx
    return len(queue)


def reset_practice(prefix: str, queue: list[str], resume: bool = False):
    st.session_state[f"{prefix}_queue"] = queue
    st.session_state[f"{prefix}_idx"] = resume_index(queue) if resume else 0
    st.session_state[f"{prefix}_show"] = False
    st.session_state[f"{prefix}_answered"] = False
    st.session_state[f"{prefix}_last"] = ""


def reset_all_queues():
    for category in CATEGORIES:
        reset_practice(CATEGORY_PREFIX[category], build_category_queue(category), resume=True)
    reset_practice("wrong", build_wrong_queue(active_wrong_category()))


# ── UI components ─────────────────────────────────────────────────────────────
def show_stats():
    state = st.session_state.user_state
    all_summary = summarize_state(state)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总题数", all_summary["total"])
    col2.metric("已做", all_summary["done"])
    col3.metric("✅ 已掌握", all_summary["correct"])
    col4.metric("❌ 错题", all_summary["wrong"])
    st.markdown("**分类进度**")
    for category in CATEGORIES:
        summary = summarize_state(state, category)
        icon = CATEGORY_ICONS[category]
        st.caption(
            f"{icon} {category}：{summary['done']} / {summary['total']}，"
            f"错题 {summary['wrong']}"
        )


def render_sync_status():
    error = st.session_state.get("sync_error", "")
    if error:
        st.warning(f"云同步未成功：{error[:220]}")
    elif st.session_state.get("sync_ok"):
        st.success("✅ 云同步已连接")
    elif get_scores_client():
        st.info("☁️ 成绩文件已配置，答题后会保存")
    else:
        st.info("💡 未配置云同步，进度只在本次会话有效")


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
                reset_practice(prefix, build_wrong_queue(active_wrong_category()))
                st.rerun()
        else:
            st.success("🎉 全部题目刷完！")
            if st.button("重头再刷", key=f"{prefix}_restart"):
                category = CATEGORY_BY_PREFIX.get(prefix)
                queue = build_category_queue(category) if category else build_main_queue()
                reset_practice(prefix, queue)
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
    st.markdown(
        f"共 **{TOTAL} 道题**"
        f"（地震 {len(question_ids('地震'))} 题 · 测井 {len(question_ids('测井'))} 题）"
    )
    st.markdown("---")
    st.caption("作者：潘高 · 中国海洋大学 2023 级勘查技术与工程 · 📮 18306376923@163.com")

    student_tab, admin_tab = st.tabs(["学生入口", "管理员入口"])

    with student_tab:
        username = st.text_input(
            "请输入用户名（同一用户名在任意设备可同步进度）",
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
                reset_all_queues()
                st.rerun()
        if not get_scores_client():
            st.info("💡 未配置成绩文件写入，进度仅在本次会话有效。")
        elif st.session_state.sync_error:
            st.warning(f"云同步读取失败：{st.session_state.sync_error[:220]}")

    with admin_tab:
        admin_password = get_admin_password()
        if not admin_password:
            st.warning("管理员入口未启用：请在 Streamlit Secrets 里配置 [app].admin_password。")
        else:
            password = st.text_input("管理员密码", type="password")
            if st.button("管理员登录", type="primary"):
                if password == admin_password:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("管理员密码不正确")


def main_screen():
    with st.sidebar:
        st.markdown(f"👤 **{st.session_state.username}**")
        st.markdown("---")
        nav_options = ["🌊 地震刷题", "🔩 测井刷题", "🔥 错题轰炸", "⚙️ 设置"]

        if st.session_state.nav not in nav_options:
            st.session_state.nav = nav_options[0]
        st.radio("导航", nav_options, key="nav")
        st.markdown("---")
        render_sync_status()
        st.markdown("---")
        show_stats()
        st.markdown("---")
        st.caption("潘高 · 中国海洋大学\n2023级勘查技术与工程\n📮 18306376923@163.com")

    nav = st.session_state.nav

    if nav in ("🌊 地震刷题", "🔩 测井刷题"):
        category = "地震" if nav.startswith("🌊") else "测井"
        prefix = CATEGORY_PREFIX[category]
        st.header(nav)
        if not st.session_state[f"{prefix}_queue"]:
            reset_practice(prefix, build_category_queue(category))
        practice_panel(prefix)

    elif nav == "🔥 错题轰炸":
        st.header("🔥 错题轰炸区")
        st.radio("错题范围", ["全部", "地震", "测井"], horizontal=True, key="wrong_category")
        wq = build_wrong_queue(active_wrong_category())
        if not wq:
            st.info("🎉 目前没有错题！先去主线刷题积累错题吧。")
        else:
            cur = set(st.session_state.wrong_queue)
            if not cur or cur != set(wq):
                reset_practice("wrong", wq)
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
            reset_all_queues()
            st.success(f"已将 {len(correct_ids)} 道题重置回错题本！")
            st.rerun()
        st.markdown("---")
        st.subheader("🗑️ 完全重置")
        if st.button("清空所有进度（不可恢复）"):
            st.session_state.user_state = {}
            save_user_state()
            reset_all_queues()
            st.success("进度已清空！")
            st.rerun()
        st.markdown("---")
        if st.button("退出登录"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.markdown("---")
        st.subheader("☁️ 云同步")
        render_sync_status()
        st.markdown("---")
        if get_scores_client():
            st.success("✅ GitHub 成绩文件已配置，多端同步已开启")
        else:
            st.warning("⚠️ GitHub 成绩文件未配置，进度仅在当前会话有效")


def admin_screen():
    st.title("🛡️ 管理员后台")
    client = get_scores_client()

    with st.sidebar:
        st.markdown("🛡️ **管理员**")
        if st.button("退出管理员"):
            st.session_state.admin_logged_in = False
            st.rerun()

    if not client:
        st.warning("需要先配置 [github].token，管理员才能读取所有用户答题情况。")
        return

    with st.spinner("正在读取用户进度…"):
        users = load_all_user_states()

    if st.session_state.sync_error:
        st.error(st.session_state.sync_error)
        return

    if not users:
        st.info("暂时没有读取到用户进度。学生答题并保存后，这里会出现统计。")
        return

    rows = []
    for username, state in sorted(users.items()):
        all_summary = summarize_state(state)
        seismic = summarize_state(state, "地震")
        logging = summarize_state(state, "测井")
        rows.append({
            "用户": username,
            "已做": f"{all_summary['done']}/{all_summary['total']}",
            "正确": all_summary["correct"],
            "错题": all_summary["wrong"],
            "地震": f"{seismic['done']}/{seismic['total']}",
            "地震错题": seismic["wrong"],
            "测井": f"{logging['done']}/{logging['total']}",
            "测井错题": logging["wrong"],
        })

    st.subheader("用户总览")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("用户明细")
    selected_user = st.selectbox("选择用户", [row["用户"] for row in rows])
    selected_category = st.radio(
        "题目范围",
        ["全部", "地震", "测井"],
        horizontal=True,
        key="admin_category",
    )
    category = None if selected_category == "全部" else selected_category
    state = users.get(selected_user, {})
    summary = summarize_state(state, category)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("题数", summary["total"])
    c2.metric("已做", summary["done"])
    c3.metric("正确", summary["correct"])
    c4.metric("错题", summary["wrong"])

    detail_rows = []
    for qid in question_ids(category):
        value = state.get(qid)
        status = "正确" if value == 1 else "错误" if value == 0 else "未做"
        q = QUESTIONS[qid]
        detail_rows.append({
            "题号": qid,
            "分类": q.get("category", ""),
            "题型": {"fill": "填空", "choice": "选择", "judge": "判断"}.get(q.get("type"), "简答"),
            "状态": status,
            "题目": q.get("q", ""),
        })
    st.dataframe(detail_rows, use_container_width=True, hide_index=True)


# ── run ───────────────────────────────────────────────────────────────────────
init_session()
if st.session_state.admin_logged_in:
    admin_screen()
elif not st.session_state.logged_in:
    login_screen()
else:
    main_screen()
