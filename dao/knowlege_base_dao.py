from utils.db_util import PostgreSQLConnector
from dao import document_dao 
import logging

pg = PostgreSQLConnector()


def get_knowledeg_base_list(type='raw'):
    sql = """select id::TEXT as id, name, content from knowledge_base where "type" = %s order by id desc"""
    params =[type]
    logging.info(params)
    return pg.query_to_dict(sql, params)


def get_knowledge_base_by_ids(id_list):
    id_replace_str = ','.join( len(id_list) * ["%s"])
    sql = f"""select id, name, content from knowledge_base where id in ({id_replace_str}) """
    return pg.query_to_dict(sql, id_list)


def update_knowledge_base(id, name, content, type='raw'):
    if not id:
        sql = """INSERT INTO knowledge_base (name, content, "type") VALUES
        (%s, %s, %s) RETURNING id;"""
        params = [name, content, type]
    else:
        document_dao.delete_document_vb(id)
        sql = """update knowledge_base set name = %s, content = %s, "type" = %s where id = %s"""
        params = [name, content, type, id]

    return pg.execute_sql(sql, params)


def delete_knowledge_base(id):
    ## delete document_vb
    document_dao.delete_document_vb(knowledge_base_id=id)

    ## delete knowledge_base
    sql = """Delete from knowledge_base where id = %s"""
    params = [id]
    return pg.execute_sql(sql, params)
