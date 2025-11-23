import os
import logging
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import PyPDF2
from pdf2image import convert_from_path
from PIL import Image
import openai
import io
import tempfile
import base64
import fitz 

from openai import OpenAI

client = OpenAI(
    api_key="""sk-e995ac2840724a45949a672ae9e7f5db""",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


logger = logging.getLogger(__name__)


# def pdf_to_images(pdf_path):
#     """将PDF转换为图片列表"""
#     try:
#         images = convert_from_path(pdf_path, dpi=200)
#         logger.info(f"成功转换PDF为 {len(images)} 张图片")
#         return images
#     except Exception as e:
#         logger.error(f"PDF转换图片失败: {str(e)}")
#         raise

def pdf_to_images(pdf_path):
    """使用PyMuPDF将PDF转换为图片列表"""
    try:
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        images = []
        
        for page_num in range(len(pdf_document)):
            # 获取页面
            page = pdf_document.load_page(page_num)
            
            # 设置转换矩阵（提高分辨率）
            mat = fitz.Matrix(2.0, 2.0)  # 200% 缩放，提高清晰度
            
            # 将页面转换为图片
            pix = page.get_pixmap(matrix=mat)
            
            # 将pixmap转换为PIL Image
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data))
            
            # 转换为RGB（确保兼容性）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
        
        pdf_document.close()
        logger.info(f"成功转换PDF为 {len(images)} 张图片")
        return images
    
    except Exception as e:
        logger.error(f"PDF转换图片失败: {str(e)}")
        raise

def image_to_base64(image):
    """将PIL图像转换为base64字符串"""
    try:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    except Exception as e:
        logger.error(f"图片转base64失败: {str(e)}")
        raise

def analyze_image_with_llm(image_base64):
    """使用LLM分析单张图片内容"""
    try:
        response = client.chat.completions.create(
            model="qwen-vl-ocr-2025-11-20",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请详细分析这张图片中的内容。如果包含文字，请准确提取所有文本；如果是图表或图像，请描述其内容和含义。请用英文回复。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        logger.info(f"图片分析完成，字符数: {len(content)}")
        return content
    except Exception as e:
        logger.error(f"LLM图片分析失败: {str(e)}")
        raise

def summarize_content_with_llm(page_contents):
    """使用LLM汇总所有页面内容"""
    try:
        # 构建提示词
        system_prompt = """你是一个专业的文档分析助手。请将以下PDF各页面的内容进行整合、总结，生成一个结构清晰、内容完整的Markdown文档。要求：
        1. 保持原文的重要信息
        2. 组织结构合理，使用适当的标题层级
        3. 如果有图表描述，请合理组织
        4. 使用英文输出
        5. 格式规范，符合Markdown语法"""

        user_content = "\n\n".join([f"第{i+1}页内容:\n{content}" for i, content in enumerate(page_contents)])
        
        # 如果内容太长，进行截断（根据token限制调整）
        if len(user_content) > 12000:
            user_content = user_content[:12000] + "\n\n[内容已截断...]"
        
        response = client.chat.completions.create(
            model="qwen3-max",  # 使用支持长文本的模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=4000
        )
        
        summary = response.choices[0].message.content
        logger.info(f"内容汇总完成，字符数: {len(summary)}")
        return summary
    except Exception as e:
        logger.error(f"LLM内容汇总失败: {str(e)}")
        raise


