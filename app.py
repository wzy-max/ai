# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import logging
from dao import knowlege_base_dao

from werkzeug.utils import secure_filename

from service.document_service import pdf_to_images,image_to_base64, analyze_image_with_llm, summarize_content_with_llm
import dashscope
from service import store_service

# 创建Flask应用
app = Flask(__name__)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB限制
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMP_IMAGES'] = 'temp_images'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# 创建必要的目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_IMAGES'], exist_ok=True)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dashscope.api_key  = 'sk-e995ac2840724a45949a672ae9e7f5db'


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 首页路由
@app.route('/api/vession')
def index():
    """首页"""
    return "1.0"

@app.get('/api/knowledge-base')
def get_knowledeg_base_list():
    return jsonify(knowlege_base_dao.get_knowledeg_base_list())


@app.post('/api/knowledge-base')
def update_knowledeg_base_list():
    param = request.get_json()
    id, title, description = param.get('id'), param.get('title'), param.get('description'), 
    row_count = knowlege_base_dao.update_knowledge_base(id, title, description)
    if row_count > 0:
        return "True"
    else:
        return "False"


@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """处理PDF上传和解析的主接口"""
    try:
        knowledge_base_id = int(request.args.get('knowledge_base_id'))

        # 检查文件是否存在
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({'error': '只支持PDF文件'}), 400
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        logger.info(f"文件已保存: {pdf_path}")
        
        # 转换PDF为图片
        images = pdf_to_images(pdf_path)
        
        # 分析每一页
        page_contents = []
        for i, image in enumerate(images):
            logger.info(f"正在分析第 {i+1}/{len(images)} 页...")
            
            # 转换图片为base64
            image_base64 = image_to_base64(image)
            
            # 使用LLM分析图片内容
            page_content = analyze_image_with_llm(image_base64)
            page_contents.append(page_content)
            
            logger.info(f"第 {i+1} 页分析完成")
        
        # 汇总所有内容
        logger.info("正在汇总所有页面内容...")
        markdown_content = summarize_content_with_llm(page_contents)
        store_service.store(knowledge_base_id, filename, markdown_content)

        
        # 清理临时文件
        try:
            os.remove(pdf_path)
            logger.info("临时文件已清理")
        except:
            pass
        
        return jsonify({
            'success': True,
            'page_count': len(images),
            'markdown_content': markdown_content,
            'message': 'PDF解析完成'
        })
        
    except Exception as e:
        logger.error(f"处理过程出错: {str(e)}")
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


# 运行应用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)