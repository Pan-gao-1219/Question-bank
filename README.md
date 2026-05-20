# 地球物理知识竞赛刷题系统

基于 Streamlit 的在线刷题网站，专为 2024 创新杯地球物理知识竞赛备赛设计。

## 题库

| 分类 | 题数 |
|---|---|
| 地震勘探 | 141 题 |
| 测井 | 20 题 |
| **合计** | **161 题** |

题型包括：选择题（单选）、填空题、简答题。

## 功能

- **📚 主线刷题**：顺序刷全部 161 题，选择题即时判断，填空题自评对错
- **🔥 错题轰炸**：专攻错题本，答对即消除，答错继续保留
- **⚡ 赛前复活**：一键将已掌握题目重置回错题本，进行极限速刷
- **多端同步**：用户名绑定 GitHub Gist，任意设备登录同步进度

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 部署到 Streamlit Cloud

1. Fork 本仓库
2. 在 [share.streamlit.io](https://share.streamlit.io) 中连接仓库，主文件选 `app.py`
3. 在 **Secrets** 中配置（可选，开启多端同步）：
   ```toml
   GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"
   GIST_ID = "your_gist_id"
   ```

## 文件说明

| 文件 | 说明 |
|---|---|
| `app.py` | Streamlit 主应用 |
| `gist_client.py` | GitHub Gist 读写（用户进度云端存储） |
| `questions_data.json` | 161 道题的完整题库 |
| `parse_questions.py` | 从 docx 解析题目的一次性脚本 |
| `.streamlit/config.toml` | 主题与服务器配置 |
