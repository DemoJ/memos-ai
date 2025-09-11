#!/bin/bash
# Memos AI 自动同步脚本
# 将此脚本添加到 crontab 实现定时同步

# 每小时执行一次
# 在 crontab 中添加：
# 0 * * * * /path/to/memos-ai/scripts/auto_sync.sh >> /path/to/memos-ai/logs/sync.log 2>&1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 进入项目目录
cd "$PROJECT_DIR"

# 激活虚拟环境（如果使用）
# source venv/bin/activate

# 执行同步
python scripts/sync.py

echo "同步完成于 $(date)"