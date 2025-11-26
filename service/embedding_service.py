import faiss
import numpy as np
import dashscope
from dashscope import TextEmbedding
from typing import List, Dict, Any
import json
import os


def get_dashscope_embedding(text: str) -> np.ndarray:
    """
    使用DashScope获取文本向量
    
    Args:
        text: 输入文本
        
    Returns:
        numpy数组表示的向量
    """
    try:
        resp = TextEmbedding.call(
            model=TextEmbedding.Models.text_embedding_v4,
            input=text,
            dimension=2048
        )
        
        if resp.status_code == 200:
            # 提取嵌入向量
            embedding = resp.output['embeddings'][0]['embedding']
            return embedding
        else:
            print(f"获取嵌入失败: {resp.message}")
            return None
            
    except Exception as e:
        print(f"DashScope API调用异常: {e}")
        return None
    

if __name__ == '__main__':
    import dashscope
    dashscope.api_key  = 'sk-e995ac2840724a45949a672ae9e7f5db'
    get_dashscope_embedding('hi')