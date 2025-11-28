import dashscope
from dashscope.audio.asr import Transcription


dashscope.api_key  = 'sk-e995ac2840724a45949a672ae9e7f5db'
mp3_path = r'C:\Users\15857\Downloads\welcome.mp3'

task_response = Transcription.async_call(
            model='qwen-audio-turbo',
            file_urls=[mp3_path],  # 直接传入本地文件路径
            language_hints=['zh', 'en'],  # 中文和英文
            sample_rate=16000,  # 采样率（可选）
        )

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

messages = [
    {
        "role": "user",
        "content": [
            {"audio": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"},
            {"text": "这段音频在说什么?"}
        ]
    }
]


response = dashscope.MultiModalConversation.call(
    model="qwen-audio-turbo",
    messages=messages,
    result_format="message"
    )
print("输出结果为：")
print(response["output"]["choices"][0]["message"].content[0]["text"])