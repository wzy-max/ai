
from langchain.tools import tool
from langchain_core.documents import Document

from service import embedding_service
from dao import document_dao


@tool(response_format="content_and_artifact")
def retrieve(query: str, knowledge_base_id) -> int:
   """Retrieve infomation"""
   embedding = embedding_service.get_dashscope_embedding(query)
   document_list = document_dao.search_similar_documents(embedding, str(knowledge_base_id))

   retrieved_docs = [Document(page_content=doc['content'], metadata={'source': doc['file_name']}) for doc in document_list]

   serialized = '\n\n'.join(
      (f'Source: {doc.metadata}\nContent: {doc.content}')
      for doc in retrieved_docs
   )
   return serialized, retrieved_docs


