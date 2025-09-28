#!/usr/bin/env python3
"""
Memos AI Sync Script
自动同步 Memos 笔记到向量数据库 (独立运行版)
"""

import os
import sys
import time
import re
from datetime import datetime
from typing import List

import chromadb
import numpy as np
import requests
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# --- 独立配置 ---
class Settings(BaseSettings):
    memos_db_path: str = "./memos_prod.db"
    vector_db_path: str = "./vector_db"
    embedding_model: str
    embedding_api_url: str
    embedding_api_key: str

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        env_file_encoding = 'utf-8'

settings = Settings()


# --- Memos数据库模型 ---
Base = declarative_base()

class Memo(Base):
    __tablename__ = "memo"
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    created_ts = Column(Integer, nullable=False)
    updated_ts = Column(Integer, nullable=False)
    row_status = Column(String, default="NORMAL")
    visibility = Column(String, default="PRIVATE")


# --- 向量存储服务 (ChromaDB 版本) ---
class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.vector_db_path)
        self.collection = self.client.get_or_create_collection(name="memos")

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        headers = {
            'Authorization': f'Bearer {settings.embedding_api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            "model": settings.embedding_model,
            "input": texts
        }
        try:
            url = f"{settings.embedding_api_url.rstrip('/')}/v1/embeddings"
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            embeddings = np.array([item['embedding'] for item in data['data']])
            return embeddings
        except requests.exceptions.RequestException as e:
            print(f"Error calling embedding API: {e}")
            raise
        except (KeyError, IndexError) as e:
            print(f"Failed to parse API response. Unexpected format: {e}")
            raise

    def upsert_documents(self, documents: List[str], doc_ids: List[int]):
        if not documents:
            return
        embeddings = self._get_embeddings(documents)
        str_doc_ids = [str(id) for id in doc_ids]
        self.collection.upsert(
            ids=str_doc_ids,
            embeddings=embeddings.tolist(),
            documents=documents
        )

    def delete_documents(self, doc_ids: List[int]):
        if not doc_ids:
            return
        str_doc_ids = [str(id) for id in doc_ids]
        self.collection.delete(ids=str_doc_ids)

    def get_all_ids(self) -> List[int]:
        """获取向量数据库中所有文档的ID"""
        ids = self.collection.get(include=[])['ids']
        return [int(id) for id in ids]

    def reset_collection(self):
        """清空并重建集合，用于全量同步"""
        self.client.delete_collection(name="memos")
        self.collection = self.client.get_or_create_collection(name="memos")

vector_store = VectorStore()


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
        db_path = os.path.abspath(settings.memos_db_path)
        if not os.path.exists(db_path):
            print(f"错误: 数据库文件不存在于 '{db_path}'")
            sys.exit(1)
            
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        self.sync_state_file = os.path.join(settings.vector_db_path, "sync_state.txt")
        self.last_sync_time = self.load_last_sync_time()
    
    def load_last_sync_time(self) -> int:
        if os.path.exists(self.sync_state_file):
            with open(self.sync_state_file, 'r') as f:
                return int(f.read().strip())
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
            
            current_db_ids = {memo.id for memo in session.query(Memo).filter(
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
                vector_store.delete_documents(deleted_memo_ids)
            
            if changed_memos:
                print(f"检测到 {len(changed_memos)} 条笔记新增或更新，正在同步到向量库...")
                documents = [memo.content for memo in changed_memos]
                doc_ids = [memo.id for memo in changed_memos]
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
                    doc_ids = [memo.id for memo in all_memos]
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
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full-sync":
        sync.full_sync()
    else:
        sync.sync_memos()

if __name__ == "__main__":
    main()
