import faiss
import numpy as np
import dashscope
from dashscope import TextEmbedding
from typing import List, Dict, Any
import json
import os

class DashScopeFAISSVectorDB:
    def __init__(self, dimension=1536, index_path=None):
        """
        初始化向量数据库
        
        Args:
            dimension: 向量维度（text-embedding-v2模型是1536维）
            index_path: FAISS索引保存路径
        """
        self.dimension = dimension
        self.index_path = index_path
        
        # 初始化FAISS索引（使用内积相似度）
        self.index = faiss.IndexFlatIP(dimension)
        
        # 存储文档内容
        self.documents = []
        self.metadatas = []
        
        # 加载已有索引
        if index_path and os.path.exists(index_path):
            self.load_index(index_path)
    
    def get_dashscope_embedding(self, text: str) -> np.ndarray:
        """
        使用DashScope获取文本向量
        
        Args:
            text: 输入文本
            
        Returns:
            numpy数组表示的向量
        """
        try:
            resp = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v2,
                input=text
            )
            
            if resp.status_code == 200:
                # 提取嵌入向量
                embedding = np.array(resp.output['embeddings'][0]['embedding'], dtype='float32')
                return embedding
            else:
                print(f"获取嵌入失败: {resp.message}")
                return None
                
        except Exception as e:
            print(f"DashScope API调用异常: {e}")
            return None
    
    def get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量获取嵌入向量（更高效）
        
        Args:
            texts: 文本列表
            
        Returns:
            向量矩阵
        """
        try:
            resp = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v2,
                input=texts
            )
            
            if resp.status_code == 200:
                embeddings = []
                for item in resp.output['embeddings']:
                    embeddings.append(np.array(item['embedding'], dtype='float32'))
                
                return np.vstack(embeddings)
            else:
                print(f"批量获取嵌入失败: {resp.message}")
                return None
                
        except Exception as e:
            print(f"DashScope API批量调用异常: {e}")
            return None
    
    def add_documents(self, documents: List[str], metadatas: List[Dict] = None):
        """
        添加文档到向量数据库
        
        Args:
            documents: 文档列表
            metadatas: 元数据列表
        """
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        if len(documents) != len(metadatas):
            raise ValueError("文档和元数据数量不匹配")
        
        print("正在生成文本嵌入...")
        embeddings = self.get_embeddings_batch(documents)
        
        if embeddings is not None:
            # 添加到FAISS索引
            self.index.add(embeddings)
            
            # 存储文档和元数据
            self.documents.extend(documents)
            self.metadatas.extend(metadatas)
            
            print(f"成功添加 {len(documents)} 个文档")
        else:
            print("添加文档失败")
    
    def search(self, query: str, k: int = 5, score_threshold: float = 0.7) -> List[Dict]:
        """
        搜索相似文档
        
        Args:
            query: 查询文本
            k: 返回结果数量
            score_threshold: 相似度阈值
            
        Returns:
            相似文档列表
        """
        # 获取查询向量
        query_embedding = self.get_dashscope_embedding(query)
        
        if query_embedding is None:
            return []
        
        # 重塑为2D数组
        query_embedding = query_embedding.reshape(1, -1)
        
        # 搜索相似向量
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.documents) and score >= score_threshold:
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadatas[idx],
                    'score': float(score),
                    'rank': i + 1
                })
        
        return results
    
    def save_index(self, path: str = None):
        """保存FAISS索引"""
        save_path = path or self.index_path
        if save_path:
            faiss.write_index(self.index, save_path)
            
            # 保存文档和元数据
            data = {
                'documents': self.documents,
                'metadatas': self.metadatas
            }
            
            with open(save_path + '.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"索引已保存到: {save_path}")
    
    def load_index(self, path: str):
        """加载FAISS索引"""
        try:
            self.index = faiss.read_index(path)
            
            # 加载文档和元数据
            with open(path + '.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.documents = data['documents']
                self.metadatas = data['metadatas']
            
            print(f"索引已从 {path} 加载")
        except Exception as e:
            print(f"加载索引失败: {e}")
    
    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        return {
            'total_documents': len(self.documents),
            'index_size': self.index.ntotal,
            'vector_dimension': self.dimension
        }