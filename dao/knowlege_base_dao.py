from utils.db_util import PostgreSQLConnector



pg = PostgreSQLConnector()


def get_knowledeg_base_list():
    sql = """select id, title, description from knowledge_base"""
    return pg.query_to_dict(sql)


def update_knowledge_base(id, title, description):
    if not id:
        sql = """INSERT INTO knowledge_base (title, description) VALUES
        (%s, %s);"""
        params = [title, description]
    else:
        sql = "update knowledge_base set title = %s, description = %s where id = %s"
        params = [id, title, description]

    return pg.execute_sql(sql, params)
