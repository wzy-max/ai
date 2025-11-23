import psycopg2
import numpy as np
from typing import List, Dict, Any, Optional

class VectorSearchManager:
    def __init__(self, connection_string):
        self.connection_string = connection_string
    
    def create_vector_index(self, index_type='ivfflat', lists=100):
        """创建向量索引"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # 确保vector扩展已安装
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            if index_type == 'ivfflat':
                index_sql = f"""
                CREATE INDEX IF NOT EXISTS idx_documents_embedding_ivfflat 
                ON documents 
                USING ivfflat (embedding vector_cosine_ops) 
                WITH (lists = {lists});
                """
            elif index_type == 'hnsw':
                index_sql = """
                CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw 
                ON documents 
                USING hnsw (embedding vector_cosine_ops) 
                WITH (m = 16, ef_construction = 64);
                """
            else:
                raise ValueError("索引类型必须是 'ivfflat' 或 'hnsw'")
            
            cursor.execute(index_sql)
            conn.commit()
            print(f"✅ {index_type.upper()} 向量索引创建成功!")
            
        except Exception as e:
            print(f"❌ 索引创建失败: {e}")
        finally:
            if conn:
                conn.close()
    
    def search_similar_documents(self, 
                               query_embedding: List[float], 
                               collection_name: str = None,
                               top_k: int = 10,
                               similarity_threshold: float = 0.0) -> List[Dict]:
        """
        相似度搜索
        
        Args:
            query_embedding: 查询向量（2048维）
            collection_name: 集合名称过滤
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
        """
        # 将向量转换为PostgreSQL格式
        embedding_str = self._format_vector(query_embedding)
        
        query = """
        SELECT 
            id,
            collection_name,
            subject,
            content,
            metadata,
            created_at,
            1 - (embedding <=> %s) as similarity
        FROM documents 
        {collection_filter}
        {similarity_filter}
        ORDER BY embedding <=> %s
        LIMIT %s
        """
        
        # 构建查询条件
        params = [embedding_str]
        conditions = []
        
        if collection_name:
            conditions.append("collection_name = %s")
            params.append(collection_name)
        
        collection_filter = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        if similarity_threshold > 0:
            similarity_filter = f"AND 1 - (embedding <=> %s) > %s"
            params.extend([embedding_str, similarity_threshold])
        else:
            similarity_filter = ""
        
        # 格式化查询
        query = query.format(
            collection_filter=collection_filter,
            similarity_filter=similarity_filter
        )
        params.extend([embedding_str, top_k])
        
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            
            # 转换为字典列表
            columns = [desc[0] for desc in cursor.description]
            documents = []
            
            for row in results:
                doc = dict(zip(columns, row))
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _format_vector(self, embedding: List[float]) -> str:
        """将Python列表格式化为PostgreSQL向量字符串"""
        if len(embedding) != 2048:
            raise ValueError(f"向量维度必须是2048，当前是{len(embedding)}")
        
        return '[' + ','.join(map(str, embedding)) + ']'
    
    def batch_search(self, 
                    query_embeddings: List[List[float]], 
                    collection_name: str = None,
                    top_k: int = 5) -> Dict[int, List[Dict]]:
        """批量相似度搜索"""
        results = {}
        
        for i, embedding in enumerate(query_embeddings):
            similar_docs = self.search_similar_documents(
                embedding, collection_name, top_k
            )
            results[i] = similar_docs
        
        return results
    
    def get_index_info(self):
        """获取索引信息"""
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # 查询索引信息
            cursor.execute("""
                SELECT 
                    indexname, 
                    indexdef 
                FROM pg_indexes 
                WHERE tablename = 'documents' 
                AND indexdef LIKE '%embedding%'
            """)
            
            indexes = cursor.fetchall()
            print("📊 向量索引信息:")
            for idx in indexes:
                print(f"  索引名: {idx[0]}")
                print(f"  定义: {idx[1][:100]}...")
                print()
            
            return indexes
            
        except Exception as e:
            print(f"❌ 获取索引信息失败: {e}")
            return []
        finally:
            if conn:
                conn.close()

# 高级搜索功能
class AdvancedVectorSearch(VectorSearchManager):
    def hybrid_search(self, 
                    query_embedding: List[float],
                    keyword: str = None,
                    collection_name: str = None,
                    top_k: int = 10,
                    similarity_weight: float = 0.7,
                    keyword_weight: float = 0.3) -> List[Dict]:
        """
        混合搜索：向量相似度 + 关键词匹配
        
        Args:
            query_embedding: 查询向量
            keyword: 关键词
            similarity_weight: 向量相似度权重
            keyword_weight: 关键词匹配权重
        """
        embedding_str = self._format_vector(query_embedding)
        
        query = """
        WITH vector_scores AS (
            SELECT 
                id,
                1 - (embedding <=> %s) as vector_score
            FROM documents
            {collection_filter}
        ),
        keyword_scores AS (
            SELECT 
                id,
                CASE 
                    WHEN subject ILIKE %s OR content ILIKE %s THEN 1.0
                    ELSE 0.0
                END as keyword_score
            FROM documents
            {collection_filter}
        )
        SELECT 
            d.id,
            d.collection_name,
            d.subject,
            d.content,
            d.metadata,
            (vs.vector_score * %s + ks.keyword_score * %s) as combined_score,
            vs.vector_score,
            ks.keyword_score
        FROM documents d
        JOIN vector_scores vs ON d.id = vs.id
        JOIN keyword_scores ks ON d.id = ks.id
        ORDER BY combined_score DESC
        LIMIT %s
        """
        
        collection_filter = f"WHERE collection_name = %s" if collection_name else ""
        keyword_pattern = f"%{keyword}%" if keyword else "%%"
        
        params = [embedding_str]
        if collection_name:
            params.extend([collection_name, collection_name])
        
        params.extend([keyword_pattern, keyword_pattern, similarity_weight, keyword_weight, top_k])
        
        try:
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            query = query.format(collection_filter=collection_filter)
            cursor.execute(query, tuple(params))
            
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            return [dict(zip(columns, row)) for row in results]
            
        except Exception as e:
            print(f"❌ 混合搜索失败: {e}")
            return []
        finally:
            if conn:
                conn.close()