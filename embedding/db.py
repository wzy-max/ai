import faiss
import numpy as np
import dashscope
from dashscope import TextEmbedding
from typing import List, Dict, Any
import json
import os
import logging


class DashScopeFAISSVectorDB:
    def __init__(self, dimension=1536, index_path=None):
        """
        
        Args:
            dimension: 
            index_path: 
        """
        self.dimension = dimension
        self.index_path = index_path
        

        self.index = faiss.IndexFlatIP(dimension)
        
        self.documents = []
        self.metadatas = []
        

        if index_path and os.path.exists(index_path):
            self.load_index(index_path)
    
    def get_dashscope_embedding(self, text: str) -> np.ndarray:
        """
        
        Args:
            text: 
            
        Returns:
            numpy
        """
        try:
            resp = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v2,
                input=text
            )
            
            if resp.status_code == 200:
                embedding = np.array(resp.output['embeddings'][0]['embedding'], dtype='float32')
                return embedding
            else:
                logging.info(f"get embedding : {resp.message}")
                return None
                
        except Exception as e:
            logging.info(f"DashScope API invoke error: {e}")
            return None
    
    def get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """
        
        Args:
            texts:
            
        Returns:

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
                logging.info(f"批量获取嵌入失败: {resp.message}")
                return None
                
        except Exception as e:
            logging.info(f"DashScope API批量调用异常: {e}")
            return None
    
    def add_documents(self, documents: List[str], metadatas: List[Dict] = None):
        """
        
        Args:
            documents: 
            metadatas: 
        """
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        if len(documents) != len(metadatas):
            raise ValueError("metadata not match")
        
        logging.info("genering embedding ...")
        embeddings = self.get_embeddings_batch(documents)
        
        if embeddings is not None:
            # 添加到FAISS索引
            self.index.add(embeddings)
            
            # 存储文档和元数据
            self.documents.extend(documents)
            self.metadatas.extend(metadatas)
            
            logging.info(f"success add {len(documents)} documents")
        else:
            logging.info("add document failed")
    
    def search(self, query: str, k: int = 5, score_threshold: float = 0.7) -> List[Dict]:
        """
        
        Args:
            query: 
            k: 
            score_threshold: 
            
        Returns:
        """

        query_embedding = self.get_dashscope_embedding(query)
        
        if query_embedding is None:
            return []
        

        query_embedding = query_embedding.reshape(1, -1)
        

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

        save_path = path or self.index_path
        if save_path:
            faiss.write_index(self.index, save_path)
            

            data = {
                'documents': self.documents,
                'metadatas': self.metadatas
            }
            
            with open(save_path + '.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"index save to: {save_path}")
    
    def load_index(self, path: str):
        try:
            self.index = faiss.read_index(path)
            
            with open(path + '.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.documents = data['documents']
                self.metadatas = data['metadatas']
            
            logging.info(f"indix load {path} ")
        except Exception as e:
            logging.info(f"load index failed: {e}")
    
    def get_stats(self) -> Dict:
        return {
            'total_documents': len(self.documents),
            'index_size': self.index.ntotal,
            'vector_dimension': self.dimension
        }