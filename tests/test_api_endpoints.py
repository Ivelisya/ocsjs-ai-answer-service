import requests
import json

def test_apis():
    print("🔍 测试AI回答服务API端点...\n")

    # 测试统计API
    try:
        response = requests.get('http://localhost:8000/api/stats', headers={'X-Access-Token': 'your_access_token_here'})
        print(f'统计API状态码: {response.status_code}')
        if response.status_code == 200:
            stats = response.json()
            print('✅ 统计API正常工作')
            print(f'   版本: {stats.get("version")}')
            print(f'   缓存大小: {stats.get("cache_size")}')
            print(f'   问答记录数: {stats.get("qa_records_count")}')
        else:
            print(f'❌ 统计API错误: {response.status_code}')
            print(response.text[:200])
    except Exception as e:
        print(f'❌ 统计API连接失败: {e}')

    print()

    # 测试缓存统计API
    try:
        response = requests.get('http://localhost:8000/api/cache/stats', headers={'X-Access-Token': 'your_access_token_here'})
        print(f'缓存统计API状态码: {response.status_code}')
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print('✅ 缓存统计API正常工作')
                stats = result.get('stats', {})
                print(f'   缓存类型: {stats.get("cache_type")}')
                print(f'   缓存大小: {stats.get("size")}')
                print(f'   命中率: {stats.get("hit_rate"):.1f}%')
            else:
                print('❌ 缓存统计API返回失败')
        else:
            print(f'❌ 缓存统计API错误: {response.status_code}')
            print(response.text[:200])
    except Exception as e:
        print(f'❌ 缓存统计API连接失败: {e}')

    print()

    # 测试问答记录API
    try:
        response = requests.get('http://localhost:8000/api/qa-records?page=1&per_page=10', headers={'X-Access-Token': 'your_access_token_here'})
        print(f'问答记录API状态码: {response.status_code}')
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print('✅ 问答记录API正常工作')
                print(f'   记录数量: {len(result.get("records", []))}')
                print(f'   总页数: {result.get("total_pages", 0)}')
            else:
                print('❌ 问答记录API返回失败')
        else:
            print(f'❌ 问答记录API错误: {response.status_code}')
            print(response.text[:200])
    except Exception as e:
        print(f'❌ 问答记录API连接失败: {e}')

if __name__ == "__main__":
    test_apis()