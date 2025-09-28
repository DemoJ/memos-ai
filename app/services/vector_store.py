
import chromadb
import numpy as np
from typing import List, Tuple
import requests
from app.core.config import settings

class VectorStore:
    def __init__(self):
        # 初始化 ChromaDB 客户端，并指定数据持久化路径
        self.client = chromadb.PersistentClient(path=settings.vector_db_path)
        # 获取或创建名为 "memos" 的集合
        self.collection = self.client.get_or_create_collection(name="memos")
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """通过外部 API 获取文本的嵌入向量"""
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
        """添加或更新文档到向量数据库"""
        if not documents:
            return
        
        embeddings = self._get_embeddings(documents)
        # ChromaDB 要求 ID 是字符串
        str_doc_ids = [str(id) for id in doc_ids]
        
        # 使用 upsert，如果 ID 已存在则更新，否则插入
        self.collection.upsert(
            ids=str_doc_ids,
            embeddings=embeddings.tolist(),
            documents=documents  # 存储原始文档内容
        )
    
    def search(self, query: str, k: int = 5) -> List[Tuple[int, float]]:
        """根据查询文本搜索最相似的文档"""
        if self.collection.count() == 0:
            return []
        
        query_embedding = self._get_embeddings([query])
        
        # 在集合中查询
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=k
        )
        
        # 解析结果以匹配旧的输出格式 (memo_id, score)
        # ChromaDB 返回的 distance 是 L2 距离，我们可以直接用它作为分数（值越小越相关）
        if not results['ids'][0]:
            return []

        ids = [int(id) for id in results['ids'][0]]
        distances = [float(dist) for dist in results['distances'][0]]
        
        return list(zip(ids, distances))
    
    def delete_documents(self, doc_ids: List[int]):
        """从向量数据库中删除文档"""
        if not doc_ids:
            return
        
        str_doc_ids = [str(id) for id in doc_ids]
        self.collection.delete(ids=str_doc_ids)

# 实例化 VectorStore，供应用其他部分使用
vector_store = VectorStore()
