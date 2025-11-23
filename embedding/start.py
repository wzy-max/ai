from db import DashScopeFAISSVectorDB
import os
import dashscope

def main():
    # 初始化向量数据库
    vector_db = DashScopeFAISSVectorDB(
        dimension=1536,  # text-embedding-v2的维度
        index_path="./my_faiss_index.index"
    )
    
    # 示例文档数据
    documents = [
        "Python是一种高级编程语言，由Guido van Rossum创建",
        "机器学习是人工智能的重要分支，专注于算法开发",
        "深度学习使用神经网络模拟人脑的学习过程",
        "自然语言处理（NLP）使计算机能够理解人类语言",
        "计算机视觉让机器能够识别和理解图像内容",
        "DashScope是阿里云提供的AI模型服务平台",
        "FAISS是Facebook开发的向量相似性搜索库",
        "向量数据库专门用于存储和检索高维向量数据"
    ]
    
    metadatas = [
        {"category": "programming", "source": "wikipedia"},
        {"category": "ai", "source": "textbook"},
        {"category": "ai", "source": "research_paper"},
        {"category": "nlp", "source": "tutorial"},
        {"category": "cv", "source": "course"},
        {"category": "platform", "source": "official_docs"},
        {"category": "library", "source": "github"},
        {"category": "database", "source": "tech_blog"}
    ]
    
    # 添加文档到向量数据库
    print("正在构建向量数据库...")
    vector_db.add_documents(documents, metadatas)
    
    # 保存索引
    vector_db.save_index()
    
    # 搜索示例
    queries = [
        "什么是机器学习？",
        "阿里云有什么AI服务？",
        "编程语言有哪些？"
    ]
    
    for query in queries:
        print(f"\n🔍 查询: {query}")
        print("-" * 50)
        
        results = vector_db.search(query, k=3)
        
        for result in results:
            print(f"相似度: {result['score']:.3f}")
            print(f"文档: {result['document']}")
            print(f"元数据: {result['metadata']}")
            print()
    
    # 显示统计信息
    stats = vector_db.get_stats()
    print("📊 数据库统计:")
    print(f"文档总数: {stats['total_documents']}")
    print(f"索引大小: {stats['index_size']}")
    print(f"向量维度: {stats['vector_dimension']}")

if __name__ == "__main__":
    # os.environ['DASHSCOPE_API_KEY'] = 'sk-e995ac2840724a45949a672ae9e7f5db'
    dashscope.api_key  = 'sk-e995ac2840724a45949a672ae9e7f5db'
    main()