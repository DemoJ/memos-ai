# Memos AI 启动脚本

# 启动 FastAPI 服务
start_server() {
    echo "启动 Memos AI 问答服务..."
    python -m app.main
}

# 同步笔记
sync_notes() {
    echo "同步笔记..."
    python scripts/sync.py
}

# 全量同步
full_sync() {
    echo "全量同步笔记..."
    python scripts/sync.py --full-sync
}

# 显示帮助
show_help() {
    echo "Memos AI 启动脚本"
    echo ""
    echo "使用方法:"
    echo "  ./start.sh server    - 启动问答服务"
    echo "  ./start.sh sync      - 增量同步笔记"
    echo "  ./start.sh full-sync - 全量同步笔记"
    echo "  ./start.sh help      - 显示帮助"
}

# 主逻辑
case "$1" in
    "server")
        start_server
        ;;
    "sync")
        sync_notes
        ;;
    "full-sync")
        full_sync
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo "未知命令: $1"
        show_help
        ;;
esac