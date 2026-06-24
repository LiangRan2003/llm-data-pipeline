import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from executor import execute_cleaning_script

API_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com").rstrip("/") + "/chat/completions"
MODEL = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

CASES = [
    {
        "name": "价格清洗",
        "data": {"price_string": ["$19.99", "USD 20", "FREE", "1,000.50"]},
        "requirements": "生成 price 浮点列；FREE 为 0；千位分隔符正确处理；删除原列。",
        "expected_columns": ["price"],
        "expected": {"price": [19.99, 20.0, 0.0, 1000.5]},
    },
    {
        "name": "日期标准化",
        "data": {"date": ["2023-10-01", "Oct 2nd 2023", "invalid_date", "2023/10/03"]},
        "requirements": "将 date 转为 pandas datetime；无法解析的值设为 NaT。",
        "expected_columns": ["date"],
        "expected_dates": ["2023-10-01", "2023-10-02", None, "2023-10-03"],
    },
    {
        "name": "嵌套 JSON 展开",
        "data": {
            "metadata": [
                "{\"category\":\"electronics\",\"warranty_years\":2}",
                "{invalid_json",
                "{\"category\":\"accessories\",\"warranty_years\":null}",
            ]
        },
        "requirements": (
            "安全解析 metadata JSON，生成 metadata_category 和 "
            "metadata_warranty_years；无效 JSON 填充缺失值；删除原列。"
        ),
        "expected_columns": ["metadata_category", "metadata_warranty_years"],
        "expected": {"metadata_category": ["electronics", None, "accessories"]},
    },
    {
        "name": "用户编号规范化",
        "data": {"user_id": ["U1001", "user-1002", "1003", "U-1004", None]},
        "requirements": "统一为 U-数字 格式；无法提取数字时设为缺失值。",
        "expected_columns": ["user_id"],
        "expected": {"user_id": ["U-1001", "U-1002", "U-1003", "U-1004", None]},
    },
]


def call_llm(api_key, dataframe, requirements, feedback=None, previous_code=None):
    prompt = (
        "编写 pandas 清洗函数 clean_data(df)，输入和输出都是 DataFrame。"
        "只输出 Python 源码，不要 Markdown。不得访问网络、文件或系统。"
        f"\n要求：{requirements}\n数据：\n{dataframe.to_csv(index=False)}"
    )
    if feedback and previous_code:
        prompt += (
            f"\n上次代码没有通过数据质量验证：{feedback}\n"
            f"上次代码：\n{previous_code}\n请修复并重新输出完整源码。"
        )
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "你是资深数据工程师。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc
    code = body["choices"][0]["message"]["content"].strip()
    fence = chr(96) * 3
    if code.startswith(fence):
        code = code.split("\n", 1)[1]
    if code.endswith(fence):
        code = code[:-3]
    return code.strip()


def equal_value(actual, expected):
    if expected is None:
        return pd.isna(actual)
    if isinstance(expected, float):
        return abs(float(actual) - expected) < 1e-6
    return actual == expected


def evaluate_case(case, api_key):
    source = pd.DataFrame(case["data"])
    result = {
        "name": case["name"],
        "executed": False,
        "row_count_preserved": False,
        "schema_passed": False,
        "values_passed": False,
        "first_passed": False,
        "attempts": 0,
        "actual_values": None,
        "error": "",
    }
    code = None
    feedback = None
    for attempt in range(1, 4):
        result["attempts"] = attempt
        try:
            code = call_llm(
                api_key, source, case["requirements"], feedback=feedback, previous_code=code
            )
            cleaned = execute_cleaning_script(code, source)
            result["executed"] = True
            result["row_count_preserved"] = len(cleaned) == len(source)
            result["schema_passed"] = all(
                column in cleaned.columns for column in case["expected_columns"]
            )
            if "expected" in case and result["schema_passed"]:
                checks = []
                for column, expected_values in case["expected"].items():
                    checks.extend(
                        equal_value(actual, expected)
                        for actual, expected in zip(cleaned[column], expected_values)
                    )
                result["values_passed"] = all(checks)
            elif "expected_dates" in case and result["schema_passed"]:
                actual_dates = [
                    None if pd.isna(value) else pd.Timestamp(value).strftime("%Y-%m-%d")
                    for value in cleaned["date"]
                ]
                result["actual_values"] = actual_dates
                result["values_passed"] = actual_dates == case["expected_dates"]
            result["passed"] = all(
                result[key]
                for key in [
                    "executed",
                    "row_count_preserved",
                    "schema_passed",
                    "values_passed",
                ]
            )
            if attempt == 1:
                result["first_passed"] = result["passed"]
            if result["passed"]:
                break
            feedback = (
                f"期望字段 {case['expected_columns']}；字段通过={result['schema_passed']}；"
                f"行数通过={result['row_count_preserved']}；数值通过={result['values_passed']}。"
                f"期望值={case.get('expected', case.get('expected_dates'))}；"
                f"实际值={result.get('actual_values')}。"
                "请针对每个混合格式值分别可靠解析，不要使用已弃用参数。"
            )
        except Exception as exc:
            result["error"] = str(exc)
            feedback = result["error"]
    result["generated_code"] = code
    return result


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY for this process")
    results = [evaluate_case(case, api_key) for case in CASES]
    output_dir = ROOT / "evaluation"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = len(results)
    passed = sum(item["passed"] for item in results)
    first_passed = sum(item["first_passed"] for item in results)
    executed = sum(item["executed"] for item in results)
    values = sum(item["values_passed"] for item in results)
    lines = [
        "# LLM 数据清洗在线质量评测",
        "",
        "## 核心指标",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 首轮场景通过率 | {100 * first_passed / total:.1f}%（{first_passed}/{total}） |",
        f"| 代码可执行率 | {100 * executed / total:.1f}%（{executed}/{total}） |",
        f"| 数据值正确率 | {100 * values / total:.1f}%（{values}/{total}） |",
        f"| 自修复后通过率 | {100 * passed / total:.1f}%（{passed}/{total}） |",
        "",
        "## 逐场景结果",
        "",
        "| 场景 | 首轮通过 | 尝试次数 | 数值正确 | 最终通过 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in results:
        flag = lambda value: "是" if value else "否"
        lines.append(
            f"| {item['name']} | {flag(item['first_passed'])} | "
            f"{item['attempts']} | {flag(item['values_passed'])} | "
            f"{flag(item['passed'])} |"
        )
    lines.extend(
        [
            "",
            "本报告调用真实模型生成 pandas 代码，再执行并核对输出值。",
            "API 密钥不写入结果文件或仓库。",
            "",
        ]
    )
    report = "\n".join(lines)
    (output_dir / "LIVE_EVALUATION_REPORT.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
