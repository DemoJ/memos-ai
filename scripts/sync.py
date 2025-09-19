#!/usr/bin/env python3
"""
Memos AI Sync Script
自动同步 Memos 笔记到向量数据库 (独立运行版)
"""

import os
import sys
import time
import re
import pickle
from datetime import datetime
from typing import List, Tuple, Optional

import faiss
import numpy as np
import requests
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# --- 独立配置 ---
# 从 scripts/.env 文件加载配置
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


# --- 从 app.models.database 复制过来的模型 ---
Base = declarative_base()

class Memo(Base):
    __tablename__ = "memo"
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    created_ts = Column(Integer, nullable=False)
    updated_ts = Column(Integer, nullable=False)
    row_status = Column(String, default="NORMAL")
    visibility = Column(String, default="PRIVATE")


# --- 从 app.services.vector_store 复制过来的服务 ---
class VectorStore:
    def __init__(self):
        self.model = None
        self.dimension = None # Will be set on first embedding
        self.index = None
        self.id_map = {}
        self.load_or_create_index()

    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        headers = {
            'Authorization': f'Bearer {settings.embedding_api_key}',
            'Content-Type': 'application/json'
        }
        # The user's example shows sending one text at a time.
        # However, many APIs support batching in the 'input' field.
        # Let's try batching first for efficiency.
        payload = {
            "model": settings.embedding_model,
            "input": texts
        }
        try:
            # Combine base URL from settings with the specific endpoint path
            url = f"{settings.embedding_api_url.rstrip('/')}/v1/embeddings"
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Based on OpenAI format, response should have a 'data' field which is a list of embedding objects
            embeddings = np.array([item['embedding'] for item in data['data']])
            return embeddings

        except requests.exceptions.RequestException as e:
            print(f"Error calling embedding API: {e}")
            raise
        except (KeyError, IndexError) as e:
            print(f"Failed to parse API response. Unexpected format: {e}")
            raise

    def load_or_create_index(self):
        index_path = os.path.join(settings.vector_db_path, "faiss.index")
        map_path = os.path.join(settings.vector_db_path, "id_map.pkl")
        
        if os.path.exists(index_path) and os.path.exists(map_path):
            self.index = faiss.read_index(index_path)
            if self.dimension is None:
                self.dimension = self.index.d
            with open(map_path, 'rb') as f:
                self.id_map = pickle.load(f)
        else:
            os.makedirs(settings.vector_db_path, exist_ok=True)
            if self.dimension:
                self.index = faiss.IndexFlatIP(self.dimension)
    
    def add_documents(self, documents: List[str], doc_ids: List[int]) -> List[int]:
        if not documents:
            return []
        
        embeddings = self._get_embeddings(documents)
        
        if self.index is None:
            self.dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(self.dimension)

        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        start_idx = self.index.ntotal
        self.index.add(embeddings.astype(np.float32))
        
        for i, doc_id in enumerate(doc_ids):
            self.id_map[start_idx + i] = doc_id
        
        self.save_index()
        return [start_idx + i for i in range(len(documents))]
    
    def search(self, query: str, k: int = 5) -> List[Tuple[int, float]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        
        query_embedding = self._get_embeddings([query])
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        scores, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx in self.id_map and idx != -1:
                memo_id = self.id_map[idx]
                results.append((memo_id, float(score)))
        
        return results
    
    def delete_documents(self, doc_ids: List[int]):
        # 查找与 doc_ids 对应的 faiss 索引
        indices_to_remove = [k for k, v in self.id_map.items() if v in doc_ids]
        
        if indices_to_remove:
            # 更新 id_map：创建一个新的 map，只包含不需要删除的条目
            new_id_map = {k: v for k, v in self.id_map.items() if k not in indices_to_remove}
            
            # 重建索引
            # 1. 获取所有剩余的向量
            remaining_indices = sorted(list(new_id_map.keys()))
            if not remaining_indices:
                 # 如果没有剩余的向量，则创建一个新的空索引
                self.index = faiss.IndexFlatIP(self.dimension)
                self.id_map = {}
            else:
                remaining_vectors = self.index.reconstruct_n(0, self.index.ntotal)
                # 过滤掉要删除的向量
                vectors_to_keep = np.delete(remaining_vectors, indices_to_remove, axis=0)

                # 创建一个新的索引并添加剩余的向量
                new_index = faiss.IndexFlatIP(self.dimension)
                new_index.add(vectors_to_keep)
                self.index = new_index

                # 更新 id_map，重新映射索引
                self.id_map = {i: new_id_map[old_idx] for i, old_idx in enumerate(remaining_indices)}

            self.save_index()

    def save_index(self):
        index_path = os.path.join(settings.vector_db_path, "faiss.index")
        map_path = os.path.join(settings.vector_db_path, "id_map.pkl")
        
        faiss.write_index(self.index, index_path)
        with open(map_path, 'wb') as f:
            pickle.dump(self.id_map, f)

# 实例化向量存储
vector_store = VectorStore()


def filter_sensitive_memos(memos: list) -> list:
    """过滤掉包含敏感信息的笔记"""
    sensitive_keywords = ["密码", "password","密钥", "token"]
    sensitive_tags = ["#密码"]
    
    def is_sensitive(memo_content: str) -> bool:
        # 检查关键词
        if any(keyword in memo_content.lower() for keyword in sensitive_keywords):
            return True
        # 检查标签
        if any(re.search(rf'{tag}\b', memo_content, re.IGNORECASE) for tag in sensitive_tags):
            return True
        return False

    original_count = len(memos)
    filtered_memos = [memo for memo in memos if not is_sensitive(memo.content)]
    
    # 打印过滤日志
    num_filtered = original_count - len(filtered_memos)
    if num_filtered > 0:
        print(f"已过滤 {num_filtered} 条包含敏感信息的笔记")
        
    return filtered_memos


class MemosSync:
    def __init__(self):
        # 确保 memos_db_path 是绝对路径或相对于当前工作目录的正确路径
        db_path = os.path.abspath(settings.memos_db_path)
        if not os.path.exists(db_path):
            print(f"错误: 数据库文件不存在于 '{db_path}'")
            print("请确保 memos_db_path 在 .env 文件中配置正确，或者数据库文件在当前目录中。")
            sys.exit(1)
            
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
            
            changed_memos = filter_sensitive_memos(changed_memos)
            
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
                
                all_memos = filter_sensitive_memos(all_memos)
                
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