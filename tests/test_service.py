# -*- coding: utf-8 -*-
"""
测试脚本
用于测试AI题库服务是否正常工作
"""
import requests
import json
import sys
import os
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 服务URL
SERVICE_URL = os.getenv("SERVICE_URL", "http://localhost:5000")

def test_health():
    """测试健康检查接口"""
    logger.info("测试健康检查接口...")
    try:
        response = requests.get(f"{SERVICE_URL}/api/health")
        logger.info(f"状态码: {response.status_code}")
        logger.info(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        logger.info("健康检查接口测试成功！")
        return True
    except Exception as e:
        logger.error(f"健康检查接口测试失败: {str(e)}")
        return False

def test_search(question, question_type=None, options=None):
    """测试搜索接口"""
    logger.info(f"测试搜索接口: {question}")
    
    params = {
        "title": question
    }
    
    if question_type:
        params["type"] = question_type
        
    if options:
        params["options"] = options
    
    try:
        logger.info("发送请求...")
        logger.info(f"参数: {json.dumps(params, indent=2, ensure_ascii=False)}")
        
        response = requests.get(f"{SERVICE_URL}/api/search", params=params)
        
        logger.info(f"状态码: {response.status_code}")
        result = response.json()
        logger.info(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("code") == 1:
            logger.info("搜索接口测试成功！")
            return True
        else:
            logger.error(f"搜索接口测试失败: {result.get('msg', '未知错误')}")
            return False
    except Exception as e:
        logger.error(f"搜索接口测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    logger.info("=" * 50)
    logger.info("AI题库服务测试脚本")
    logger.info("=" * 50)
    
    # 测试健康检查接口
    if not test_health():
        logger.error("健康检查失败，请确认服务是否正常运行。")
        sys.exit(1)
    
    # 测试单选题
    test_search(
        "中国的首都是哪个城市？", 
        "single",
        "A. 上海\nB. 北京\nC. 广州\nD. 深圳"
    )
    
    # 测试多选题
    test_search(
        "以下哪些是中国的一线城市？", 
        "multiple",
        "A. 北京\nB. 上海\nC. 广州\nD. 深圳\nE. 成都\nF. 杭州"
    )
    
    # 测试判断题
    test_search(
        "地球是太阳系中第三颗行星。", 
        "judgement"
    )
    
    # 测试填空题
    test_search(
        "《红楼梦》的作者是_______。",
        "completion"
    )

    # 新增：测试阅读理解题
    reading_comprehension_question = """1. (Reading Comprehension, 20.0 points) The Starry Night by Vincent van Gogh has risen to the peak(顶峰) of artistic achievements. Although Van Gogh sold only one painting in his life, the aftermath of his work is enormous. The Starry Night is one of the most well-known images in modern culture as well as being one of the most replicated and sought-after prints. From Don McLean’s song “Vincent” (Starry Starry Night), to the endless number of merchandise products sporting this image, it is nearly impossible to shy away from this amazing painting.
One may begin to ask what features within the painting are responsible for its ever growing popularity. There are actually several main aspects that intrigue those who view this image, and each factor affects each individual differently.
There is the night sky filled with swirling clouds, stars ablaze with their own luminescence, and a bright crescent moon. Although the features are exaggerated, this is a scene we can all relate to, and also one that most individuals feel comfortable and at ease with. This sky keeps the viewer’s eyes moving about the painting, following the curves and creating a visual dot to dot with the stars. This movement keeps the onlooker involved in the painting while the other factors take hold.
Below the rolling hills of the horizon lies a small town. There is a peaceful essence flowing from the structures. Perhaps the cool dark colours and the fiery windows spark(激起) memories of our own warm childhood years filled with imagination of what exists in the night and dark starry skies. The center point of the town is the tall steeple(尖塔) of the church, reigning largely over the smaller buildings. This steeple casts down a sense of stability onto the town, and also creates a sense of size and seclusion.
To the left of the painting there is a massive dark structure that develops an even greater sense of size and isolation. This structure is magnificent when compared to the scale of other objects in the painting. The curving lines mirror that of the sky and create the sensation of depth in the painting. This structure also allows the viewer to interpret what it is. From a mountain to a leafy bush, the analysis of this formation is wide and full of variety(多样性).
Van Gogh painted The Starry Night while in a mental hospital at Saint-Remy in 1889. During Van Gogh’s younger years (1876–1880) he wanted to dedicate his life to helping the poor people develop an intimate relationship with God. Many believe that this religious endeavour may be reflected in the eleven stars of the painting. In Genesis 37:9, the following statement is made: “And he dreamed yet another dream, and told it his brethren, and said, Behold, I have dreamed a dream more; and, behold, the sun and the moon and the eleven stars made homage to me.”
Whether or not this religious inspiration is true, many features of The Starry Night have made it a popular painting. For instance, the stars in the night sky are surrounded with their own sphere of light. The reflection of artificial light (new to the time period) from Arles in the river makes one’s eyes move around the painting, thus keeping the viewer visually involved. There are structures in the distant lit up in a warm glow of light. Although we may never know how Vincent himself truly felt about this painting, mankind still embraces(拥护) its greatness.
(1) (Single Choice 4.0points) What makes The Starry Night’s sky visually engaging?( )
A. The accurate depiction of constellations(星座).
B. The swirling clouds and luminous stars that guide the viewer’s eyes.
C. The absence of the moon to emphasize darkness.
D. The use of straight lines to create order."""
    test_search(reading_comprehension_question)
    
    logger.info("=" * 50)
    logger.info("测试完成！")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()