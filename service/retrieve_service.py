

from service import embedding_service
from dao import document_dao
import logging


def retrieve(query: str):
   """Retrieve infomation"""
   embedding = embedding_service.get_dashscope_embedding(query)
   document_list = document_dao.search_similar_documents(embedding)
   logging.info(query)
   logging.info(document_list)
   return document_list


