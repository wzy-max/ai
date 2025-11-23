from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from dao import document_dao
from service import embedding_service
import json

def store(knowledge_base_id, file_name, content):
    final_chunks = split_markdown_document(content)

    document_id = document_dao.update_document(None, knowledge_base_id, file_name, content)

    for chunk in final_chunks:
        page_content, metadata = chunk['page_content'], chunk['metadata']
        content = json.dumps(metadata) + '\n\n' + page_content
        embedding = embedding_service.get_dashscope_embedding(content)
        document_dao.save_document_vb(document_id, content, embedding)



def split_markdown_document(markdown_text):
    """完整的MD文档拆分流程"""
    
    # 1. 按标题层级拆分
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3")
    ]
    
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=True
    )
    
    header_chunks = markdown_splitter.split_text(markdown_text)
    
    # 2. 对每个标题块进行细粒度拆分
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )
    
    final_chunks = []
    for header_doc in header_chunks:
        chunks = text_splitter.split_text(header_doc.page_content)
        for chunk in chunks:
            final_chunks.append({
                "page_content": chunk,
                "metadata": header_doc.metadata
            })
    
    return final_chunks



