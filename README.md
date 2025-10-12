# Memos AI 个人笔记智能问答助手

## 项目概述

这是一个基于个人 Memos 笔记的智能问答助手，能够理解你的问题并仅根据你的笔记内容给出准确回答。

## 更新说明
经实际实验后，在线向量模型api消耗较小，故全部改为使用在线向量模型api，以减小打包大小。

如需要本地向量模型，之前的代码已经备份到：https://github.com/DemoJ/memos-ai-cpu


## 功能特点

- **智能问答**：基于语义搜索 + LLM 生成准确回答
- **自动同步**：容器启动时自动执行全量或增量同步，无需手动干预。
- **实时同步**：通过 Webhook 支持 Memos 笔记的实时创建、更新和删除，变更即时同步。
- **数据本地**：Memos 数据库和向量索引通过 Docker volumes 存储在本地，保护隐私。
- **Docker 部署**：提供 Docker Compose 配置，实现一键部署和启动。

## Docker 部署 (推荐)

本项目已完全容器化，推荐使用 Docker 进行部署，无需在宿主机上安装 Python 环境。

### 1. 准备工作

```bash
# 克隆项目
git clone https://github.com/your-repo/memos-ai.git
cd memos-ai
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的配置
# 确保至少填写了所有必需的 API Key 和模型名称
nano .env
```

**重要**:
- 将你的 Memos 数据库文件 `memos_prod.db` 放置在项目根目录下。
- `MEMOS_DB_PATH` 和 `VECTOR_DB_PATH` 环境变量在 Docker 环境下通常无需修改，它们指向容器内的路径。

### 3. 启动服务

```bash
# 使用 Docker Compose 构建并启动服务
docker-compose up --build -d
```
服务启动后，容器会自动执行以下操作：
- **首次启动**：检查发现 `vector_db` 目录不存在，会自动执行一次**全量同步**，为所有笔记建立索引。
- **后续启动**：检查发现 `vector_db` 目录已存在，会自动执行一次**增量同步**，只处理自上次同步以来的变更。

现在，你可以访问 `http://localhost:9877` 开始使用。

### 4. 查看日志

```bash
# 查看服务日志，包括同步过程和应用日志
docker-compose logs -f
```

## 配置说明

### 环境变量 (.env)

```bash
# --- 必需配置 ---

# OpenAI API 配置 (用于语言模型)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 在线 Embedding 服务配置 (用于向量化)
# 兼容 OpenAI Embedding API 格式
EMBEDDING_API_URL=your_embedding_api_url_here
EMBEDDING_API_KEY=your_embedding_api_key_here
EMBEDDING_MODEL=your_embedding_model_name # 例如: bge-m3

# Memos Webhook 密钥 (用于实时同步)
MEMOS_WEBHOOK_SECRET=your_secret_string_here

# --- 可选配置 ---

# 数据库路径 (在 Docker 环境下通常无需修改)
MEMOS_DB_PATH=./memos_prod.db
VECTOR_DB_PATH=./vector_db

# 搜索结果数量
MAX_SEARCH_RESULTS=5

# 检索分数阈值
RETRIEVAL_SCORE_THRESHOLD=0.7
```

### Webhook 配置 (用于实时同步)

为了实现笔记的实时同步，您需要在 Memos 中配置 Webhook。

1.  在 `.env` 文件中设置 `MEMOS_WEBHOOK_SECRET` 为一个复杂的随机字符串。
2.  在 Memos 的 `设置` > `Webhook` 中，添加一个新的 Webhook。
3.  将 URL 设置为 `http://<你的服务地址>:<端口>/api/v1/webhook/memos?secret=<你在.env中设置的密钥>`。
    -   例如: `http://your-server-ip:9877/api/v1/webhook/memos?secret=a_very_strong_and_secret_string_12345`

配置完成后，您在 Memos 中的所有变更都会被即时同步到 AI 知识库中。

## 项目结构

```
memos-ai/
├── app/
│   ├── api/           # API 路由
│   ├── core/          # 核心配置
│   ├── models/        # 数据模型
│   ├── services/      # 业务逻辑
│   ├── templates/     # HTML 模板
│   └── main.py        # FastAPI 应用入口
├── scripts/
│   └── sync.py        # 同步脚本 (由容器自动调用)
├── .env.example       # 环境变量模板
├── docker-compose.yaml # Docker Compose 配置文件
├── Dockerfile         # Docker 镜像定义
├── docker-entrypoint.sh # Docker 入口脚本
├── requirements.txt   # 依赖列表
└── README.md          # 项目文档
```

## TODO (后续优化)

- **文本分块 (Chunking)**：实现更智能的文本分块策略（例如按 Markdown 结构或语义分块），以提升检索单元的语义完整性，避免破坏上下文。
- **检索增强 (Retrieval Enhancement)**：
  - **混合搜索 (Hybrid Search)**：结合传统的关键词搜索（如 BM25）与向量语义搜索，提高对特定术语、代码片段或缩写的召回准确率。
  - **重排 (Re-ranking)**：在初步检索后，引入 Cross-Encoder 等更精确的模型对结果进行重排序，以提升最终上下文的精度和相关性。
- **Prompt 工程 (Prompt Engineering)**：根据具体使用场景，持续优化和迭代向 LLM 提问的 Prompt 模板，以获得更稳定、更符合预期的回答质量。

## 技术栈

- **后端**: FastAPI + SQLAlchemy
- **向量搜索**: ChromaDB + 在线 Embedding 服务
- **LLM**: OpenAI GPT-3.5/4
- **数据库**: SQLite (Memos)
- **前端**: 原生 HTML/CSS/JS
- **部署**: Docker

## 安全说明

- Memos 数据库和生成的向量索引通过 Docker Volume 映射，完全存储在本地宿主机上。
- 笔记内容会发送至你配置的在线 Embedding 服务以生成向量。
- 笔记内容和相关向量会发送至你配置的 LLM 服务（如 OpenAI）以生成回答。
- API 密钥完全由你本地保管，仅用于调用你指定的 API 服务。
- 建议定期备份 `memos_prod.db` 和 `vector_db` 目录。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 特别致谢

X-AIO和[李寻欢](https://github.com/lixh00)提供API额度供本项目研究使用，特别感谢!

X - All in one ：基于分布式AI算力的 LLM API 平台

官网地址：https://www.x-aio.com

## 许可证

MIT License
