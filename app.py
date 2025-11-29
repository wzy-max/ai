# app.py
from flask import Flask,  request, jsonify
import os
from concurrent.futures import ThreadPoolExecutor
import logging
from dao import knowlege_base_dao
from docx import Document
from fpdf import FPDF
from dotenv import load_dotenv

from werkzeug.utils import secure_filename

import dashscope
from service import store_service, retrieve_service
from service.document_service import pdf_to_images,image_to_base64, analyze_image_with_llm, summarize_content_with_llm


# 创建Flask应用
app = Flask(__name__)

thread_pool = ThreadPoolExecutor(max_workers=10)

# set env
load_dotenv()
dashscope.api_key  = os.getenv('dashscope_api_key')

# 配置
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB限制
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_IMAGES'] = 'temp_images'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc', 'txt'}

# 创建必要的目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_IMAGES'], exist_ok=True)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)


# 首页路由
@app.route('/api/vession')
def index():
    """首页"""
    return "1.0"


# 获取knowledge base
@app.get('/api/knowledge-base')
def get_knowledeg_base_list():
    return jsonify(knowlege_base_dao.get_knowledeg_base_list(request.args.get("type", "raw")))


# 保存knowledge base
@app.post('/api/knowledge-base')
def update_knowledeg_base_list():
    param = request.get_json()
    id, name, content = int(param.get('id')), param.get('name'), param.get('content'), 
    store_service.update_knowledge_base(id, name, content)
    return "True"


# 删除knowledge base
@app.delete('/api/knowledge-base/<int:id>')
def delete_knowledge_base(id):
    row_count = knowlege_base_dao.delete_knowledge_base(int(id))
    if row_count > 0:
        return "True"
    else:
        return "False"


@app.post('/api/knowledge-base/summary')
def summary_knowledge_base():
    param = request.get_json()
    knowledge_base_id_list, user_advance = param.get('knowledge_base_id_list'), param.get('user_advance')
    knowledge_base_id_list = [str(d) for d in knowledge_base_id_list]
    thread_pool.submit(store_service.genr_processed_knowledge_base, knowledge_base_id_list, user_advance)
    return "success"

    
@app.post('/api/retrieve')
def retrieve_knowledeg():
    logging.info("====invoke retrieve====")
    param = request.get_json()
    query = param.get('query')
    r = retrieve_service.retrieve(query)
    return jsonify(r)


@app.route('/api/upload-file', methods=['POST'])
def upload_pdf():
     # 检查文件是否存在
    
    files = request.files.values()

    filename_path_list = []

    for file in files:
        # 检查文件名
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({'error': '只支持PDF,DOCX,DOC,TXT文件'}), 400

        # 保存上传的文件
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logging.info(f"文件已保存: {file_path}")

        filename_path_list.append([filename, file_path])

    thread_pool.submit(upload_pdf_method, filename_path_list)

    return "True"
    

def upload_pdf_method(filename_path_list:list):
    """处理PDF上传和解析的主接口"""
    total_page_contents = []
    try:
        for filename, file_path in filename_path_list:
            if filename.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as file:
                    page_contents = [file.read()]
            elif filename.endswith('.pdf') or filename.endswith('.doc') or filename.endswith('.docx'):
                if not filename.endswith('.pdf'):
                    file_path = docx_to_pdf_fpdf(file_path)

                # 转换PDF为图片
                images = pdf_to_images(file_path)
                
                # 分析每一页
                page_contents = []
                for i, image in enumerate(images):
                    logging.info(f"正在分析第 {i+1}/{len(images)} 页...")
                    
                    # 转换图片为base64
                    image_base64 = image_to_base64(image)
                    
                    # 使用LLM分析图片内容
                    page_content = analyze_image_with_llm(image_base64)
                    page_contents.append(page_content)
                    
                    logging.info(f"第 {i+1} 页分析完成")
                
                # 汇总所有内容
                logging.info("正在汇总所有页面内容...")

            total_page_contents.extend(page_contents)

        name = ';'.join([d[0] for d in filename_path_list])
        markdown_content = summarize_content_with_llm(total_page_contents)
        store_service.update_knowledge_base(None, name, markdown_content)

        # 清理临时文件
        try:
            # os.remove(file_path)
            logging.info("临时文件已清理")
        except:
            pass
        
    except Exception as e:
        logging.exception(e)


class PDFConverter(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Converted from DOCX', 0, 1, 'C')
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def docx_to_pdf_fpdf(docx_path, pdf_path=None):
    """
    使用fpdf2将docx转换为pdf
    """
    if pdf_path is None:
        pdf_path = os.path.splitext(docx_path)[0] + '.pdf'
    
    try:
        # 读取docx
        doc = Document(docx_path)
        
        # 创建PDF
        pdf = PDFConverter()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        
        # 添加内容
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                # 处理特殊字符
                text = text.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 10, text)
                pdf.ln(5)
        
        # 保存PDF
        pdf.output(pdf_path)
        logging.info(f"转换成功: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logging.info(f"转换失败: {e}")
        raise e
    finally:
        os.remove(docx_path)
        logging.info("临时文件已清理")


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 运行应用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)