#!/usr/bin/env python3
"""
Memos AI Sync Script
自动同步 Memos 笔记到向量数据库
"""

import os
import sys
import time
import re
from datetime import datetime

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models.database import Memo
from app.services.vector_store import vector_store
from app.services.memos_service import MemosService


# --- 辅助函数 ---
def filter_sensitive_memos(memos: list) -> list:
    """过滤掉包含敏感信息的笔记"""
    sensitive_keywords = ["密码", "password", "密钥", "token"]
    sensitive_tags = ["#密码"]
    
    def is_sensitive(memo_content: str) -> bool:
        if any(keyword in memo_content.lower() for keyword in sensitive_keywords):
            return True
        if any(re.search(rf'{tag}\b', memo_content, re.IGNORECASE) for tag in sensitive_tags):
            return True
        return False

    original_count = len(memos)
    filtered_memos = [memo for memo in memos if not is_sensitive(memo.content)]
    
    num_filtered = original_count - len(filtered_memos)
    if num_filtered > 0:
        print(f"已过滤 {num_filtered} 条包含敏感信息的笔记")
        
    return filtered_memos


# --- 同步逻辑 ---
class MemosSync:
    def __init__(self):
        memos_service = MemosService()
        self.SessionLocal = memos_service.SessionLocal
        
        # 检查数据库文件是否存在
        db_path = os.path.abspath(settings.memos_db_path)
        if not os.path.exists(db_path):
            print(f"错误: 数据库文件不存在于 '{db_path}'")
            sys.exit(1)
        
        self.sync_state_file = os.path.join(settings.vector_db_path, "sync_state.txt")
        self.last_sync_time = self.load_last_sync_time()
    
    def load_last_sync_time(self) -> int:
        if os.path.exists(self.sync_state_file):
            with open(self.sync_state_file, 'r') as f:
                try:
                    return int(f.read().strip())
                except (ValueError, TypeError):
                    return 0
        return 0
    
    def save_last_sync_time(self, timestamp: int):
        os.makedirs(os.path.dirname(self.sync_state_file), exist_ok=True)
        with open(self.sync_state_file, 'w') as f:
            f.write(str(timestamp))
    
    def get_changed_memos(self) -> tuple:
        with self.SessionLocal() as session:
            changed_memos = session.query(Memo).filter(
                Memo.row_status == "NORMAL",
                Memo.visibility == "PRIVATE",
                Memo.updated_ts > self.last_sync_time
            ).all()
            
            changed_memos = filter_sensitive_memos(changed_memos)
            
            current_db_ids = {str(memo.id) for memo in session.query(Memo).filter(
                Memo.row_status == "NORMAL",
                Memo.visibility == "PRIVATE"
            ).all()}
            
            vector_db_ids = set(vector_store.get_all_ids())
            
            deleted_memo_ids = list(vector_db_ids - current_db_ids)
            
            return changed_memos, deleted_memo_ids
    
    def sync_memos(self):
        """执行增量同步操作"""
        print(f"[{datetime.now()}] 开始增量同步笔记...")
        
        try:
            changed_memos, deleted_memo_ids = self.get_changed_memos()
            
            if not changed_memos and not deleted_memo_ids:
                print("没有需要同步的变更")
                return
            
            if deleted_memo_ids:
                print(f"检测到 {len(deleted_memo_ids)} 条笔记被删除，正在从向量库移除...")
                vector_store.delete_documents([str(id) for id in deleted_memo_ids])
            
            if changed_memos:
                print(f"检测到 {len(changed_memos)} 条笔记新增或更新，正在同步到向量库...")
                documents = [memo.content for memo in changed_memos]
                doc_ids = [str(memo.id) for memo in changed_memos]
                vector_store.upsert_documents(documents, doc_ids)
            
            current_time = int(time.time())
            self.save_last_sync_time(current_time)
            self.last_sync_time = current_time
            
            print(f"[{datetime.now()}] 增量同步完成")
            
        except Exception as e:
            print(f"同步失败: {str(e)}")
            raise
    
    def full_sync(self):
        """执行全量同步所有笔记"""
        print(f"[{datetime.now()}] 开始全量同步...")
        
        try:
            with self.SessionLocal() as session:
                all_memos = session.query(Memo).filter(
                    Memo.row_status == "NORMAL",
                    Memo.visibility == "PRIVATE"
                ).all()
                
                all_memos = filter_sensitive_memos(all_memos)
                
                print("正在重置向量数据库...")
                vector_store.reset_collection()
                
                if all_memos:
                    print(f"同步 {len(all_memos)} 条笔记到向量库...")
                    documents = [memo.content for memo in all_memos]
                    doc_ids = [str(memo.id) for memo in all_memos]
                    vector_store.upsert_documents(documents, doc_ids)
                
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
    
    # 如果是第一次运行（同步状态文件不存在），或者用户明确要求，则执行全量同步
    if not os.path.exists(sync.sync_state_file) or \
       (len(sys.argv) > 1 and sys.argv[1] == "--full-sync"):
        sync.full_sync()
    else:
        sync.sync_memos()

if __name__ == "__main__":
    main()
