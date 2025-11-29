import dashscope
from dashscope.audio.asr import Transcription


dashscope.api_key  = 'sk-e995ac2840724a45949a672ae9e7f5db'
# mp3_path = r'C:\Users\15857\Downloads\welcome.mp3'

# task_response = Transcription.async_call(
#             model='qwen-audio-turbo',
#             file_urls=[mp3_path],  # 直接传入本地文件路径
#             language_hints=['zh', 'en'],  # 中文和英文
#             sample_rate=16000,  # 采样率（可选）
#         )

# dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# messages = [
#     {
#         "role": "user",
#         "content": [
#             {"audio": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"},
#             {"text": "这段音频在说什么?"}
#         ]
#     }
# ]


# response = dashscope.MultiModalConversation.call(
#     model="qwen-audio-turbo",
#     messages=messages,
#     result_format="message"
#     )
# logging.info("输出结果为：")
# logging.info(response["output"]["choices"][0]["message"].content[0]["text"])



import requests
import base64
import os
from pathlib import Path
import json
from typing import Dict, Optional

class QwenLocalVideoExtractor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def encode_video_to_base64(self, video_path: str) -> str:
        """将本地视频文件编码为base64"""
        try:
            # 检查文件是否存在
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            # 检查文件大小（建议小于10MB）
            file_size = os.path.getsize(video_path)
            if file_size > 10 * 1024 * 1024:  # 10MB
                logging.info(f"警告: 视频文件较大 ({file_size/1024/1024:.1f}MB)，可能影响处理速度")
            
            # 读取并编码视频文件
            with open(video_path, "rb") as video_file:
                video_data = video_file.read()
                base64_encoded = base64.b64encode(video_data).decode('utf-8')
                
            # 根据文件扩展名确定MIME类型
            ext = Path(video_path).suffix.lower()
            mime_types = {
                '.mp4': 'video/mp4',
                '.avi': 'video/avi',
                '.mov': 'video/quicktime',
                '.mkv': 'video/x-matroska',
                '.webm': 'video/webm'
            }
            mime_type = mime_types.get(ext, 'video/mp4')
            
            return f"data:{mime_type};base64,{base64_encoded}"
            
        except Exception as e:
            raise Exception(f"视频文件编码失败: {str(e)}")
    
    def extract_local_video(self, video_path: str, prompt: str = None) -> Dict:
        """提取本地视频内容
        
        Args:
            video_path: 本地视频文件路径
            prompt: 自定义提示词
        """
        if prompt is None:
            prompt = """请详细分析这个视频内容：
            1. 视频主题和核心内容
            2. 关键场景和时间线
            3. 出现的人物、物体、动作
            4. 视觉风格和画面特点
            5. 情感氛围和整体印象
            6. 潜在的应用场景"""
        
        try:
            # 编码视频文件
            logging.info(f"正在编码视频文件: {Path(video_path).name}")
            video_base64 = self.encode_video_to_base64(video_path)
            logging.info("视频编码完成，开始分析...")
            
            # 构建API请求
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "video": video_base64,
                            "type": "video"
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
            
            data = {
                "model": "qwen3-vl-plus",  # 或 qwen2.5-vl-72b-instruct
                "input": {"messages": messages},
                "parameters": {
                    "result_format": "message",
                    "max_tokens": 20000
                }
            }
            
            # 发送请求
            response = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
                headers=self.headers,
                json=data,
                timeout=120  # 视频分析需要更长时间
            )
            response.raise_for_status()
            
            return self._parse_response(response.json())
            
        except Exception as e:
            return {
                "success": False,
                "error": f"分析失败: {str(e)}",
                "video_path": video_path
            }
    
    def _parse_response(self, response: Dict) -> Dict:
        """解析API响应"""
        try:
            if "output" in response and "choices" in response["output"]:
                content = response["output"]["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "content": content,
                    "usage": response.get("usage", {}),
                    "request_id": response.get("request_id", "")
                }
            else:
                error_msg = response.get("message", "未知错误")
                return {
                    "success": False,
                    "error": error_msg,
                    "raw_response": response
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"响应解析失败: {str(e)}",
                "raw_response": response
            }

# 使用示例
def main():
    # 初始化提取器
    extractor = QwenLocalVideoExtractor(api_key=dashscope.api_key )
    
    # 分析本地视频文件
    video_path = r"C:\Users\15857\Downloads\flower.webm"  # 替换为实际路径
    
    result = extractor.extract_local_video(video_path)
    
    if result["success"]:
        logging.info("✅ 视频分析成功!")
        logging.info("\n" + "="*50)
        logging.info(result["content"])
        logging.info("="*50)
        
        # 显示使用统计
        if "usage" in result:
            usage = result["usage"]
            logging.info(f"\n使用统计: 输入token: {usage.get('input_tokens', 'N/A')}, "
                  f"输出token: {usage.get('output_tokens', 'N/A')}")
    else:
        logging.info(f"❌ 分析失败: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    main()