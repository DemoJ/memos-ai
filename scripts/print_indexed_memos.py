#!/usr/bin/env python3
"""
Memos AI Print Indexed Memos Script
打印所有已加入向量数据库索引的笔记内容
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.core.config import settings  # noqa: E422
from app.models.database import Memo  # noqa: E422
from app.services.vector_store import vector_store  # noqa: E422


def print_all_indexed_memos():
    """
    查询并打印向量数据库中所有索引的笔记内容
    """
    print("开始查询向量数据库中的笔记...")

    # 1. 从向量存储中获取所有已索引的 memo ID
    indexed_memo_ids = list(vector_store.id_map.values())

    if not indexed_memo_ids:
        print("向量数据库中没有找到任何已索引的笔记。")
        return

    print(f"向量数据库中共有 {len(indexed_memo_ids)} 条笔记。")

    # 2. 连接到 Memos SQLite 数据库
    try:
        db_path = os.path.abspath(settings.memos_db_path)
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
    except Exception as e:
        print(f"数据库连接失败: {e}")
        print(f"请检查 .env 文件中的 MEMOS_DB_PATH 配置是否正确: {settings.memos_db_path}")
        return

    # 3. 查询并打印笔记内容
    with SessionLocal() as session:
        print("正在从 Memos 数据库中检索笔记内容...")
        
        # Memo.id 在 indexed_memo_ids 列表中
        memos = session.query(Memo).filter(Memo.id.in_(indexed_memo_ids)).all()

        if not memos:
            print("未能从数据库中找到与索引匹配的笔记。")
            return
        
        print("=" * 20)
        for i, memo in enumerate(memos, 1):
            print(f"笔记 #{i} (ID: {memo.id})")
            print("-" * 20)
            print(memo.content)
            print("=" * 20)
            
    print(f"查询完成，共打印 {len(memos)} 条笔记。")


if __name__ == "__main__":
    print_all_indexed_memos()