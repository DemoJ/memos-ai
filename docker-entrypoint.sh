#!/bin/bash

# 如果任何命令失败，立即退出
set -e

# 定义向量数据库路径
VECTOR_DB_PATH="/app/vector_db"
SYNC_STATE_FILE="$VECTOR_DB_PATH/sync_state.txt"

# 检查同步状态文件是否存在，以判断是否为首次初始化
if [ ! -f "$SYNC_STATE_FILE" ]; then
    echo "同步状态文件不存在，判断为首次初始化，开始执行全量同步..."
    python scripts/sync.py --full-sync
else
    echo "发现同步状态文件，开始执行增量同步..."
    python scripts/sync.py
fi

echo "同步流程执行完毕。"

# 执行 Dockerfile 中 CMD 指定的命令 (即启动主应用)
echo "启动 Memos AI 服务..."
exec "$@"