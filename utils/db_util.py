import psycopg2
from psycopg2 import sql
import pandas as pd

class PostgreSQLConnector:
    def __init__(self, connection_string = "postgresql://neondb_owner:npg_OfmVx6R5pDjA@ep-shy-salad-a459v8qo-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"):
        self.connnection_string = connection_string
        self.conn = None
        self.cursor = None
        self.connect()
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.conn = psycopg2.connect(self.connnection_string)
            self.cursor = self.conn.cursor()
            print("✅ PostgreSQL连接成功!")
            return True
        except psycopg2.Error as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ 数据库连接已关闭")
    
    def execute_sql(self, query, params=None):
        """执行查询语句"""
        try:
            self.cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                results = self.cursor.fetchall()
                return results
            else:
                self.conn.commit()
                if query.strip().upper().startswith('INSERT') and 'RETURNING' in query.strip().upper():
                    return self.cursor.fetchone()[0]
                else:
                    return self.cursor.rowcount
                
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"❌ 执行查询失败: {e}")
            return None
    
    def get_table_info(self, table_name=None):
        """获取表信息"""
        if table_name:
            query = """
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """
            return self.execute_sql(query, (table_name,))
        else:
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """
            return self.execute_sql(query)
        

    def query_to_dict(self, query: str, params: tuple = None, orient: str = 'records'):
        """执行查询并返回Python字典列表"""
        df = pd.read_sql_query(query, self.conn, params=params)
        
        if df.empty:
            return []
        
        # 将DataFrame转为字典
        if orient == 'records':
            return df.to_dict('records')
        elif orient == 'dict':
            return df.to_dict()
        else:
            return df.to_dict(orient)

# 使用示例
if __name__ == '__main__':
    # 创建连接实例
    pg = PostgreSQLConnector(
        connection_string="postgresql://neondb_owner:npg_OfmVx6R5pDjA@ep-shy-salad-a459v8qo-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    
    if pg.connect():
        # 获取所有表
        tables = pg.get_table_info()
        print("数据库中的表:", tables)

        # sql = """CREATE TABLE knowledge_base (
        #     id SERIAL PRIMARY KEY,
        #     title VARCHAR(255) NOT NULL,
        #     description TEXT
        # );"""

        # sql = """INSERT INTO knowledge_base (title, description) VALUES
        # ('Flask Web开发', '使用Flask框架构建Web应用程序'),
        # ('PostgreSQL数据库', '学习关系型数据库PostgreSQL的使用'),
        # ('机器学习基础', '人工智能和机器学习的基本概念');"""

        # sql = """CREATE TABLE IF NOT EXISTS document_vb (
        #     id SERIAL PRIMARY KEY,
        #     document_id INT NOT NULL,
        #     content TEXT NOT NULL,
        #     embedding VECTOR(2048)  -- 使用vector扩展
        # );"""

        # sql = """CREATE TABLE IF NOT EXISTS document (
        #     id SERIAL PRIMARY KEY,
        #     knowledge_base_id INT NOT NULL,
        #     file_name VARCHAR(1024) NOT NULL,
        #     content TEXT NOT NULL
        # );"""

        sql = "select * from document"
        # sql = "drop table document"

        pg.execute_sql(sql)
        
        pg.disconnect()

