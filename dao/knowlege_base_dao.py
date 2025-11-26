from utils.db_util import PostgreSQLConnector



pg = PostgreSQLConnector()


def get_knowledeg_base_list():
    sql = """select id, name, content from knowledge_base"""
    return pg.query_to_dict(sql)


def update_knowledge_base(id, name, content):
    if not id:
        sql = """INSERT INTO knowledge_base (name, content) VALUES
        (%s, %s);"""
        params = [name, content]
    else:
        sql = "update knowledge_base set name = %s, content = %s where id = %s"
        params = [name, content, id]

    return pg.execute_sql(sql, params)


def delete_knowledge_base(id):
    sql = """Delete from knowledge_base where id = %s"""
    params = [id]

    return pg.execute_sql(sql, params)