# -*- coding: utf-8 -*-
"""
测试缓存改进功能
"""
import requests
import json
import time

def test_cache_improvements():
    """测试缓存改进功能"""
    base_url = "http://localhost:8000"
    headers = {"X-Access-Token": "your_access_token_here"}

    print("=" * 60)
    print("测试缓存改进功能")
    print("=" * 60)

    # 测试数据
    test_question = "中国的首都是哪个城市？"
    test_data = {
        "title": test_question,
        "type": "single",
        "options": "A. 上海\nB. 北京\nC. 广州\nD. 深圳"
    }

    try:
        # 1. 测试缓存统计（初始状态）
        print("\n1. 获取初始缓存统计...")
        response = requests.get(f"{base_url}/api/cache/stats", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print("✅ 缓存统计API正常工作")
            print(f"   缓存类型: {stats['stats']['cache_type']}")
            print(f"   缓存大小: {stats['stats']['size']}")
            print(f"   命中率: {stats['stats']['hit_rate']:.1f}%")
            print(f"   总请求数: {stats['stats']['total_requests']}")
        else:
            print(f"❌ 缓存统计API失败: {response.status_code}")

        # 2. 第一次搜索请求（应该缓存）
        print("\n2. 第一次搜索请求...")
        start_time = time.time()
        response = requests.get(f"{base_url}/api/search", params=test_data, headers=headers)
        first_request_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print("✅ 第一次搜索成功")
            print(f"   响应时间: {first_request_time:.2f}秒")
            print(f"   答案: {result.get('answer', 'N/A')[:50]}...")
        else:
            print(f"❌ 第一次搜索失败: {response.status_code}")
            return

        # 3. 第二次相同请求（应该命中缓存）
        print("\n3. 第二次相同请求（测试缓存命中）...")
        start_time = time.time()
        response = requests.get(f"{base_url}/api/search", params=test_data, headers=headers)
        second_request_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print("✅ 第二次搜索成功")
            print(f"   响应时间: {second_request_time:.2f}秒")
            print(f"   答案: {result.get('answer', 'N/A')[:50]}...")

            # 比较响应时间
            if second_request_time < first_request_time * 0.5:
                print("🎯 缓存命中！响应时间显著缩短")
            else:
                print("⚠️  缓存可能未命中或响应时间差异不明显")
        else:
            print(f"❌ 第二次搜索失败: {response.status_code}")

        # 4. 获取更新后的缓存统计
        print("\n4. 获取更新后的缓存统计...")
        response = requests.get(f"{base_url}/api/cache/stats", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print("✅ 更新后缓存统计:")
            print(f"   缓存大小: {stats['stats']['size']}")
            print(f"   命中率: {stats['stats']['hit_rate']:.1f}%")
            print(f"   命中次数: {stats['stats']['hits']}")
            print(f"   未命中次数: {stats['stats']['misses']}")
            print(f"   存储次数: {stats['stats']['sets']}")
            print(f"   总请求数: {stats['stats']['total_requests']}")

            # 验证统计数据
            if stats['stats']['total_requests'] >= 2:
                print("✅ 统计数据正确记录")
            else:
                print("⚠️  统计数据可能有问题")
        else:
            print(f"❌ 获取缓存统计失败: {response.status_code}")

        # 5. 测试缓存清除
        print("\n5. 测试缓存清除...")
        response = requests.post(f"{base_url}/api/cache/clear", headers=headers)
        if response.status_code == 200:
            result = response.json()
            print("✅ 缓存清除成功")
            print(f"   消息: {result.get('message', 'N/A')}")
        else:
            print(f"❌ 缓存清除失败: {response.status_code}")

        print("\n" + "=" * 60)
        print("缓存改进功能测试完成！")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务，请确保服务正在运行")
        print("   尝试运行: python main.py")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_cache_improvements()