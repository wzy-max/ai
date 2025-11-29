from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from dao import document_dao, knowlege_base_dao
from service import embedding_service,document_service
import json
import logging


def update_knowledge_base(knowledge_base_id, name, content, type="raw"):
    final_chunks = split_markdown_document(content)
    # save knowledge base if update: delete document vb
    r = knowlege_base_dao.update_knowledge_base(knowledge_base_id, name, content,type)
    if not knowledge_base_id:
        knowledge_base_id = r

    for chunk in final_chunks:
        page_content, metadata = chunk['page_content'], chunk['metadata']
        content = json.dumps(metadata) + '\n\n' + page_content
        embedding = embedding_service.get_dashscope_embedding(content)
        document_dao.save_document_vb(knowledge_base_id, content, embedding)


def genr_processed_knowledge_base(knowledge_base_id_list, user_advance):
    data_list = knowlege_base_dao.get_knowledge_base_by_ids(knowledge_base_id_list)
    content_list = [d['content'] for d in data_list]
    summary = document_service.summarize_content_with_llm(content_list, user_advance)
    name = document_service.genr_title(summary)
    update_knowledge_base(None, name, summary, "processed")


def split_markdown_document(markdown_text):
    
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



