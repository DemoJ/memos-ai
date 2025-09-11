#!/usr/bin/env python3
"""
Memos AI Sync Script
自动同步 Memos 笔记到向量数据库
"""

import os
import sys
import time
from datetime import datetime, timedelta

import faiss
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到 Python 路径，以确保可以正确导入 app 模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.core.config import settings  # noqa: E402
from app.models.database import Memo  # noqa: E402
from app.services.vector_store import vector_store  # noqa: E402

class MemosSync:
    def __init__(self):
        db_path = os.path.abspath(settings.memos_db_path)
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # 跟踪同步状态
        self.sync_state_file = os.path.join(settings.vector_db_path, "sync_state.txt")
        self.last_sync_time = self.load_last_sync_time()
    
    def load_last_sync_time(self) -> int:
        """加载上次同步时间戳"""
        if os.path.exists(self.sync_state_file):
            with open(self.sync_state_file, 'r') as f:
                return int(f.read().strip())
        return 0
    
    def save_last_sync_time(self, timestamp: int):
        """保存同步时间戳"""
        os.makedirs(os.path.dirname(self.sync_state_file), exist_ok=True)
        with open(self.sync_state_file, 'w') as f:
            f.write(str(timestamp))
    
    def get_changed_memos(self) -> tuple:
        """获取新增、修改和删除的笔记"""
        with self.SessionLocal() as session:
            # 获取新增或修改的笔记
            changed_memos = session.query(Memo).filter(
                Memo.row_status == "NORMAL",
                Memo.visibility == "PRIVATE",
                Memo.updated_ts > self.last_sync_time
            ).all()
            
            # 获取所有当前有效的笔记ID
            current_memo_ids = {memo.id for memo in session.query(Memo).filter(
                Memo.row_status == "NORMAL",
                Memo.visibility == "PRIVATE"
            ).all()}
            
            # 获取向量数据库中的笔记ID
            vector_memo_ids = set(vector_store.id_map.values())
            
            # 找出被删除的笔记
            deleted_memo_ids = list(vector_memo_ids - current_memo_ids)
            
            return changed_memos, deleted_memo_ids
    
    def sync_memos(self):
        """执行同步操作"""
        print(f"[{datetime.now()}] 开始同步笔记...")
        
        try:
            changed_memos, deleted_memo_ids = self.get_changed_memos()
            
            if not changed_memos and not deleted_memo_ids:
                print("没有需要同步的变更")
                return
            
            # 处理删除的笔记
            if deleted_memo_ids:
                print(f"删除 {len(deleted_memo_ids)} 条笔记")
                vector_store.delete_documents(deleted_memo_ids)
            
            # 处理新增/修改的笔记
            if changed_memos:
                # 先删除旧版本（如果有）
                changed_ids = [memo.id for memo in changed_memos]
                vector_store.delete_documents(changed_ids)
                
                # 添加新版本
                documents = [memo.content for memo in changed_memos]
                doc_ids = [memo.id for memo in changed_memos]
                
                if documents:
                    vector_store.add_documents(documents, doc_ids)
                    print(f"同步 {len(documents)} 条笔记")
            
            # 更新同步时间
            current_time = int(time.time())
            self.save_last_sync_time(current_time)
            self.last_sync_time = current_time
            
            print(f"[{datetime.now()}] 同步完成")
            
        except Exception as e:
            print(f"同步失败: {str(e)}")
            raise
    
    def full_sync(self):
        """全量同步所有笔记"""
        print(f"[{datetime.now()}] 开始全量同步...")
        
        try:
            with self.SessionLocal() as session:
                all_memos = session.query(Memo).filter(
                    Memo.row_status == "NORMAL",
                    Memo.visibility == "PRIVATE"
                ).all()
                
                # 清空向量数据库
                vector_store.index = faiss.IndexFlatIP(vector_store.dimension)
                vector_store.id_map = {}
                
                # 添加所有笔记
                if all_memos:
                    documents = [memo.content for memo in all_memos]
                    doc_ids = [memo.id for memo in all_memos]
                    vector_store.add_documents(documents, doc_ids)
                    print(f"全量同步 {len(documents)} 条笔记")
                
                # 更新同步时间
                current_time = int(time.time())
                self.save_last_sync_time(current_time)
                self.last_sync_time = current_time
                
                print(f"[{datetime.now()}] 全量同步完成")
                
        except Exception as e:
            print(f"全量同步失败: {str(e)}")
            raise

def main():
    """主函数"""
    sync = MemosSync()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full-sync":
        sync.full_sync()
    else:
        sync.sync_memos()

if __name__ == "__main__":
    main()