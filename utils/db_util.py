import psycopg2
from psycopg2 import sql
import pandas as pd

import psycopg2
from psycopg2 import pool
import pandas as pd
import threading

from argparse import Namespace

class PostgreSQLConnector:
    def __init__(self, connection_string=None, min_conn=2, max_conn=10):
        self.connection_string = connection_string or "postgresql://neondb_owner:npg_OfmVx6R5pDjA@ep-shy-salad-a459v8qo-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
        self.min_conn = min_conn
        self.max_conn = max_conn
        self.connection_pool = None
        self._local = Namespace()  # 线程本地存储
        self.connect_pool()
    
    def connect_pool(self):
        """创建连接池"""
        try:
            self.connection_pool = pool.SimpleConnectionPool(
                self.min_conn,
                self.max_conn,
                self.connection_string
            )
            print(f"✅ PostgreSQL连接池创建成功! 连接数: {self.min_conn}-{self.max_conn}")
            return True
        except psycopg2.Error as e:
            print(f"❌ 连接池创建失败: {e}")
            return False
    
    def get_connection(self):
        """从连接池获取连接"""
        try:
            if not hasattr(self._local, 'conn') or self._local.conn.closed:
                self._local.conn = self.connection_pool.getconn()
                self._local.cursor = self._local.conn.cursor()
            return self._local.conn, self._local.cursor
        except psycopg2.Error as e:
            print(f"❌ 获取连接失败: {e}")
            return None, None
    
    def release_connection(self):
        """释放连接回连接池"""
        try:
            if hasattr(self._local, 'cursor') and self._local.cursor:
                self._local.cursor.close()
                self._local.cursor = None
            
            if hasattr(self._local, 'conn') and self._local.conn:
                self.connection_pool.putconn(self._local.conn)
                self._local.conn = None
        except Exception as e:
            print(f"❌ 释放连接失败: {e}")
    
    def execute_sql(self, query, params=None):
        """执行查询语句"""
        conn, cursor = self.get_connection()
        if not conn or not cursor:
            return None
        
        try:
            cursor.execute(query, params or ())
            query_upper = query.strip().upper()
            
            if query_upper.startswith('SELECT'):
                results = cursor.fetchall()
                return results
            else:
                conn.commit()
                if query_upper.startswith('INSERT') and 'RETURNING' in query_upper:
                    result = cursor.fetchone()
                    return result[0] if result else None
                else:
                    return cursor.rowcount
                
        except psycopg2.Error as e:
            conn.rollback()
            print(f"❌ 执行查询失败: {e}")
            return None
        finally:
            # 注意：这里不释放连接，保持连接在请求生命周期内
            pass
    
    def execute_sql_with_connection(self, query, params=None):
        """执行SQL并立即释放连接（适合短查询）"""
        conn, cursor = self.get_connection()
        if not conn or not cursor:
            return None
        
        try:
            cursor.execute(query, params or ())
            query_upper = query.strip().upper()
            
            if query_upper.startswith('SELECT'):
                results = cursor.fetchall()
                return results
            else:
                conn.commit()
                if query_upper.startswith('INSERT') and 'RETURNING' in query_upper:
                    result = cursor.fetchone()
                    return result[0] if result else None
                else:
                    return cursor.rowcount
                
        except psycopg2.Error as e:
            conn.rollback()
            print(f"❌ 执行查询失败: {e}")
            return None
        finally:
            self.release_connection()
    
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
        conn, _ = self.get_connection()
        if not conn:
            return []
        
        try:
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                return []
            
            # 将DataFrame转为字典
            if orient == 'records':
                return df.to_dict('records')
            elif orient == 'dict':
                return df.to_dict()
            else:
                return df.to_dict(orient)
                
        except Exception as e:
            print(f"❌ 查询转字典失败: {e}")
            return []
        finally:
            # self.release_connection()
            pass
    
    def disconnect(self):
        """关闭所有连接"""
        if self.connection_pool:
            self.connection_pool.closeall()
            print("✅ 数据库连接池已关闭")
    
    def get_pool_status(self):
        """获取连接池状态"""
        if self.connection_pool:
            return {
                'min_connections': self.min_conn,
                'max_connections': self.max_conn,
                'current_connections': len(self.connection_pool._used),
                'available_connections': len(self.connection_pool._rlist)
            }
        return None

# 上下文管理器版本
class PostgreSQLConnection:
    def __init__(self, connector):
        self.connector = connector
        self.conn = None
        self.cursor = None
    
    def __enter__(self):
        self.conn, self.cursor = self.connector.get_connection()
        return self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.conn:
                self.conn.rollback()
        self.connector.release_connection()

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

        sql = """CREATE TABLE knowledge_base (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            content TEXT
        );"""

        # sql = """INSERT INTO knowledge_base (title, description) VALUES
        # ('Flask Web开发', '使用Flask框架构建Web应用程序'),
        # ('PostgreSQL数据库', '学习关系型数据库PostgreSQL的使用'),
        # ('机器学习基础', '人工智能和机器学习的基本概念');"""

        sql = """CREATE TABLE IF NOT EXISTS document_vb (
            id SERIAL PRIMARY KEY,
            knowledge_base_id INT NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR(2048)  -- 使用vector扩展
        );"""

        # sql = """CREATE TABLE IF NOT EXISTS document (
        #     id SERIAL PRIMARY KEY,
        #     knowledge_base_id INT NOT NULL,
        #     file_name VARCHAR(1024) NOT NULL,
        #     content TEXT NOT NULL
        # );"""

        sql = "select * from document_vb"
        # sql = "drop table document"
        # sql = "TRUNCATE TABLE document_vb"

        pg.execute_sql(sql)
        
        pg.disconnect()

