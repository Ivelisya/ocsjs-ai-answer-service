# -*- coding: utf-8 -*-
import json
import requests
import time
import sys
import os
from typing import List, Dict

# 添加父目录到路径以便导入 utils (如果需要)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_URL = "http://localhost:8000/api/search"
TEST_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_questions.json")

def load_test_questions(filepath: str) -> List[Dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("questions", [])

def test_question(question: Dict) -> bool:
    payload = {
        "title": question["title"],
        "type": question["type"],
        "options": question["options"],
        "context": ""  # 可选
    }
    
    # 模拟 OCS 客户端行为，使用 POST
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 1: # 假设 code 1 为成功，或者直接检查 data
                 # 注意：app.py 返回的格式是 format_answer_for_ocs, key 是 'answer'
                ai_answer = result.get("answer", "").strip()
                expected = question["expected_answer"].strip()
                
                print(f"题目: {question['title'][:20]}...")
                print(f"  预期: {expected}")
                print(f"  实际: {ai_answer}")
                
                # 标准化处理：如果是多选题返回 "A. xxx#B. xxx"，尝试提取 A,B
                normalized_ai = ai_answer
                if "#" in ai_answer and "A." in ai_answer:
                    # 提取选项字母
                    import re
                    # 查找 A., B. 等形式
                    matches = re.findall(r"([A-Z])\.", ai_answer)
                    if matches:
                        normalized_ai = ",".join(sorted(matches))
                        print(f"  (标准化为: {normalized_ai})")

                # 简单匹配：包含即可 (对于多选可能需要更复杂的判断)
                if expected == ai_answer or expected == normalized_ai:
                    print("  [通过]")
                    return True
                else:
                    # 尝试宽松匹配
                    if len(expected) > 0 and (expected in ai_answer or expected in normalized_ai):
                         print("  [宽松通过]")
                         return True
                    print("  [失败]")
                    return False
            else:
                 print(f"  [API错误] {result.get('msg')}")
                 return False
        else:
            print(f"  [HTTP错误] {response.status_code}")
            return False
    except Exception as e:
        print(f"  [请求异常] {e}")
        return False

def run_evaluation():
    print(f"开始加载测试题目: {TEST_FILE}")
    try:
        questions = load_test_questions(TEST_FILE)
    except FileNotFoundError:
        print(f"错误: 找不到测试题目文件 {TEST_FILE}")
        print("尝试生成测试题目...")
        import subprocess
        subprocess.run(["python", "generate_test_questions.py"], check=True)
        questions = load_test_questions(TEST_FILE)

    print(f"共加载 {len(questions)} 道题目")
    
    passed = 0
    total = len(questions)
    
    start_time = time.time()
    for i, q in enumerate(questions):
        print(f"\n--- 测试 {i+1}/{total} ---")
        if test_question(q):
            passed += 1
        time.sleep(0.5) # 避免过快
    
    duration = time.time() - start_time
    accuracy = (passed / total) * 100 if total > 0 else 0
    
    print("\n" + "="*30)
    print(f"测试完成")
    print(f"耗时: {duration:.2f}秒")
    print(f"通过率: {passed}/{total} ({accuracy:.1f}%)")
    print("="*30)

if __name__ == "__main__":
    # 简单的检查服务是否运行
    try:
        requests.get("http://localhost:8000/api/health", timeout=2)
        run_evaluation()
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到服务 (http://localhost:8000)。请确保 'main.py' 正在运行且端口为 8000。")
