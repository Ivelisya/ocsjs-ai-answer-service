import os
import json
import time
import asyncio
import aiohttp
from typing import List, Dict, Any
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

# --- 配置 ---
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000") # 修改端口为 5000
SEARCH_ENDPOINT = f"{API_BASE_URL}/api/search"
GOLDEN_SET_PATH = os.getenv("GOLDEN_SET_PATH", "evaluation/golden_set_expert.json")
REPORT_PATH = "evaluation/evaluation_report_async.md"
CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", 40))
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

console = Console(record=True)

def load_golden_set(path: str) -> List[Dict[str, Any]]:
    """加载黄金标准数据集"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        console.print(f"[bold red]错误: 评估集文件未找到 at '{path}'[/bold red]")
        exit(1)
    except json.JSONDecodeError:
        console.print(f"[bold red]错误: 无法解析JSON文件 at '{path}'[/bold red]")
        exit(1)

async def call_api(session: aiohttp.ClientSession, question_data: Dict[str, Any]) -> Dict[str, Any]:
    """异步调用搜索API并返回结果"""
    payload = {
        "title": question_data["question"],
        "type": question_data["type"],
        "options": question_data.get("options", ""),
        "context": question_data.get("context", "")
    }
    headers = {"Content-Type": "application/json"}
    if ACCESS_TOKEN:
        headers["X-Access-Token"] = ACCESS_TOKEN

    try:
        async with session.post(SEARCH_ENDPOINT, json=payload, headers=headers, timeout=120) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientError as e:
        return {"code": 0, "msg": f"API请求失败: {e}"}
    except asyncio.TimeoutError:
        return {"code": 0, "msg": "API请求超时"}

def compare_answers(ai_answer: str, standard_answer: str, question_type: str) -> bool:
    """比较AI答案和标准答案"""
    if not isinstance(ai_answer, str) or not isinstance(standard_answer, str):
        return False
    ai_answer = ai_answer.strip()
    standard_answer = standard_answer.strip()

    if question_type == "multiple":
        ai_parts = set(part.strip() for part in ai_answer.split('#'))
        std_parts = set(part.strip() for part in standard_answer.split('#'))
        return ai_parts == std_parts
    
    return ai_answer == standard_answer

def generate_and_print_report(results: Dict[str, Any], duration: float):
    """使用Rich生成并打印评估报告"""
    console.rule("[bold cyan]AI 答题服务并发评估报告[/bold cyan]", style="cyan")
    
    # 总体结果
    stats_table = Table(show_header=False, box=None, padding=(0, 1))
    stats_table.add_column(style="dim")
    stats_table.add_column()
    stats_table.add_row("评估时间:", f"{time.strftime('%Y-%m-%d %H:%M:%S')}")
    stats_table.add_row("评估集:", f"[cyan]{GOLDEN_SET_PATH}[/cyan]")
    stats_table.add_row("目标服务:", f"[link={API_BASE_URL}]{API_BASE_URL}[/link]")
    stats_table.add_row("并发数:", f"[bold yellow]{CONCURRENT_REQUESTS}[/bold yellow]")
    stats_table.add_row("总耗时:", f"[bold green]{duration:.2f} 秒[/bold green]")
    stats_table.add_row("QPS (每秒查询数):", f"[bold magenta]{results['total_questions'] / duration:.2f}[/bold magenta]")
    console.print(stats_table)

    console.rule("[bold]总体结果[/bold]")
    summary_table = Table(title="评估摘要")
    summary_table.add_column("指标", justify="right", style="cyan", no_wrap=True)
    summary_table.add_column("数值", justify="center", style="magenta")
    summary_table.add_row("总题数", str(results['total_questions']))
    summary_table.add_row("正确数", f"[green]{results['correct_count']}[/green]")
    summary_table.add_row("错误数", f"[red]{results['incorrect_count']}[/red]")
    summary_table.add_row("API失败数", f"[yellow]{results['api_failures']}[/yellow]")
    summary_table.add_row("[bold]总准确率[/bold]", f"[bold cyan]{results['overall_accuracy']:.2f}%[/bold cyan]")
    console.print(summary_table)

    console.rule("[bold]各题型准确率[/bold]")
    type_table = Table(title="各题型准确率")
    type_table.add_column("题型", style="cyan")
    type_table.add_column("总题数", justify="center")
    type_table.add_column("正确数", justify="center")
    type_table.add_column("准确率", justify="right", style="bold")
    
    sorted_types = sorted(results['by_type'].keys())
    for q_type in sorted_types:
        data = results['by_type'][q_type]
        accuracy = data['accuracy']
        color = "green" if accuracy == 100 else "yellow" if accuracy > 80 else "red"
        type_table.add_row(q_type, str(data['total']), str(data['correct']), f"[{color}]{accuracy:.2f}%[/{color}]")
    console.print(type_table)

    if results['failures']:
        console.rule("[bold red]失败案例分析[/bold red]")
        for failure in sorted(results['failures'], key=lambda x: x['id']):
            panel_content = f"[bold]问题:[/bold]\n{failure['question']}\n\n"
            if failure.get('options'):
                panel_content += f"[bold]选项:[/bold]\n{failure['options']}\n\n"
            panel_content += f"[bold]标准答案:[/bold] [green]{failure['standard_answer']}[/green]\n"
            panel_content += f"[bold]AI  答案:[/bold] [red]{failure['ai_answer']}[/red]\n"
            
            api_response_json = json.dumps(failure['api_response'], indent=2, ensure_ascii=False)
            panel_content += f"\n[bold]API 响应:[/bold]\n"
            
            console.print(Panel(panel_content, title=f"[bold yellow]题目 ID: {failure['id']} (类型: {failure['type']})[/bold yellow]", border_style="red"))
            console.print(Syntax(api_response_json, "json", theme="monokai", line_numbers=True))

async def run_test(item: Dict[str, Any], session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, progress: Progress, task_id) -> Dict[str, Any]:
    """运行单个测试用例"""
    async with semaphore:
        api_response = await call_api(session, item)
        
        q_type = item['type']
        is_correct = False
        ai_answer = ""

        if api_response.get("code") == 1:
            ai_answer = api_response.get("answer", "")
            if compare_answers(ai_answer, item["standard_answer"], q_type):
                is_correct = True
        
        progress.update(task_id, advance=1)
        
        result = {
            "is_correct": is_correct,
            "q_type": q_type,
            "ai_answer": ai_answer,
            "api_response": api_response,
            "item": item
        }
        return result

async def main():
    """主执行函数"""
    console.print(Panel(f"[bold green]开始并发评估 AI 答题服务 (并发数: {CONCURRENT_REQUESTS})[/bold green]", border_style="green"))
    start_eval_time = time.time()
    
    golden_set = load_golden_set(GOLDEN_SET_PATH)
    total_questions = len(golden_set)
    
    stats_by_type = defaultdict(lambda: {'total': 0, 'correct': 0})
    failures = []
    
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    
    progress = Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("[bold blue]{task.completed} of {task.total} items"),
        expand=True
    )

    async with aiohttp.ClientSession() as session:
        with progress:
            task_id = progress.add_task("[cyan]评估进度[/cyan]", total=total_questions)
            tasks = [run_test(item, session, semaphore, progress, task_id) for item in golden_set]
            test_results = await asyncio.gather(*tasks)

    correct_count = 0
    api_failures = 0

    for res in test_results:
        stats_by_type[res['q_type']]['total'] += 1
        if res['is_correct']:
            correct_count += 1
            stats_by_type[res['q_type']]['correct'] += 1
        else:
            if res['ai_answer'] == "" and res['api_response'].get("code") != 1:
                 api_failures += 1
                 res['ai_answer'] = "API_ERROR"

            failures.append({
                "id": res['item']["id"],
                "type": res['q_type'],
                "question": res['item']["question"],
                "options": res['item'].get("options", ""),
                "standard_answer": res['item']["standard_answer"],
                "ai_answer": res['ai_answer'],
                "api_response": res['api_response']
            })

    duration = time.time() - start_eval_time
    overall_accuracy = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    for q_type in stats_by_type:
        type_total = stats_by_type[q_type]['total']
        type_correct = stats_by_type[q_type]['correct']
        stats_by_type[q_type]['accuracy'] = (type_correct / type_total) * 100 if type_total > 0 else 0

    results = {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "incorrect_count": total_questions - correct_count - api_failures,
        "api_failures": api_failures,
        "overall_accuracy": overall_accuracy,
        "by_type": stats_by_type,
        "failures": failures
    }

    generate_and_print_report(results, duration)
    
    # 保存HTML格式的报告以便回顾
    console.save_html("evaluation/evaluation_report_cli.html")
    console.print(f"\n[bold green]CLI输出报告已保存至: evaluation/evaluation_report_cli.html[/bold green]")


if __name__ == "__main__":
    asyncio.run(main())