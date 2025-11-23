from embedding.db import DashScopeFAISSVectorDB
import os
import dashscope

from typing_extensions import Dict

class QAWithRAG:
    """基于检索增强生成（RAG）的问答系统"""
    
    def __init__(self, vector_db):
        self.vector_db = vector_db
        self.dashscope_api_key = dashscope.api_key
    
    def generate_answer(self, question: str, context: str) -> str:
        """使用DashScope生成答案"""
        from dashscope import Generation
        
        prompt = f"""基于以下上下文回答问题。

上下文：
{context}

问题：{question}

答案："""
        
        try:
            response = Generation.call(
                model='qwen-plus',
                prompt=prompt,
                max_tokens=500
            )
            
            if response.status_code == 200:
                return response.output.text
            else:
                return f"生成答案失败: {response.message}"
                
        except Exception as e:
            return f"API调用异常: {e}"
    
    def ask_question(self, question: str, top_k: int = 3) -> Dict:
        """回答问题"""
        # 1. 检索相关文档
        results = self.vector_db.search(question, k=top_k)
        
        if not results:
            return {"answer": "未找到相关信息", "sources": []}
        
        # 2. 构建上下文
        context = "\n".join([result['document'] for result in results])
        
        # 3. 生成答案
        answer = self.generate_answer(question, context)
        
        return {
            "question": question,
            "answer": answer,
            "sources": results
        }

# 使用RAG系统
def demo_qa_system():
    # 初始化向量数据库（假设已存在）
    vector_db = DashScopeFAISSVectorDB(index_path="./my_faiss_index.index")
    
    # 创建QA系统
    qa_system = QAWithRAG(vector_db)
    
    # 测试问答
    questions = [
        "Python是谁创建的？",
        "机器学习是什么？",
        "DashScope有什么功能？"
    ]
    
    for question in questions:
        print(f"\n❓ 问题: {question}")
        result = qa_system.ask_question(question)
        print(f"🤖 答案: {result['answer']}")
        print("📚 参考来源:")
        for source in result['sources']:
            print(f"   - 相似度 {source['score']:.3f}: {source['document'][:50]}...")

            
dashscope.api_key  = 'sk-e995ac2840724a45949a672ae9e7f5db'
demo_qa_system()