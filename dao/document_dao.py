from utils.db_util import PostgreSQLConnector

from typing import List, Dict

pg = PostgreSQLConnector()


def save_document_vb(knowledge_base_id, content, embedding):
    sql = """INSERT INTO document_vb (knowledge_base_id, content, embedding) VALUES
        (%s, %s, %s);"""
    params = [knowledge_base_id, content, embedding]

    return pg.execute_sql(sql, params)
    

    
def delete_document_vb(knowledge_base_id):
    sql = """Delete from document_vb where knowledge_base_id = %s"""
    params = [knowledge_base_id]
    pg.execute_sql(sql, params)


def search_similar_documents(query_embedding: List[float], 
                               knowledge_base_id: str = None,
                               top_k: int = 10,
                               similarity_threshold: float = 0.0) -> List[Dict]:
        """
        相似度搜索
        
        Args:
            query_embedding: 查询向量（2048维）
            knowledge_base_id: 集合名称过滤
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值
        """
        # 将向量转换为PostgreSQL格式
        embedding_str = _format_vector(query_embedding)
        
        query = """
        SELECT 
            v.id,
            v.content,
            d.name knowledge_base_name,
            d.id knowledge_base_id,
            1 - (embedding <=> %s) as similarity
        FROM knowledge_base d
        left join document_vb v on d.id = v.knowledge_base_id
        {collection_filter}
        {similarity_filter}
        ORDER BY embedding <=> %s
        LIMIT %s
        """
        
        # 构建查询条件
        params = [embedding_str]
        conditions = []
        
        if knowledge_base_id:
            conditions.append("d.knowledge_base_id = %s")
            params.append(knowledge_base_id)
        
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

        return pg.query_to_dict(query, params)
        


def _format_vector(embedding: List[float]) -> str:
        """将Python列表格式化为PostgreSQL向量字符串"""
        if len(embedding) != 2048:
            raise ValueError(f"向量维度必须是2048，当前是{len(embedding)}")
        
        return '[' + ','.join(map(str, embedding)) + ']'