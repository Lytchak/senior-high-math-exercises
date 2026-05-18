import os
import re
import sys
from collections import OrderedDict

PROBLEMS_DIR = "problems"
TEMPLATE_FILE = "template.html"
OUTPUT_FILE = "index.html"

# 月份英文映射
MONTH_EN = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December"
}


def convert_includegraphics(text):
    """将 \includegraphics[...]{...} 转换为 HTML 的 <img> 标签"""
    def replacer(match):
        options = match.group(1) or ""
        filename = match.group(2)
        styles = ["max-width: 100%", "height: auto", "display: block", "margin: 1em auto"]
        width_match = re.search(r'width\s*=\s*([\d\.]+\w+)', options)
        if width_match:
            styles.append(f"width: {width_match.group(1)}")
        style_str = "; ".join(styles)
        return f'<img src="{filename}" style="{style_str}">'

    pattern = r'\\includegraphics\s*(?:\[(.*?)\])?\{(.*?)\}'
    return re.sub(pattern, replacer, text)


def convert_lists(text):
    """将 LaTeX 的 enumerate/itemize 环境转换为 HTML 列表"""
    def process_list(match):
        env_type = match.group(1)
        content = match.group(2)
        tag = 'ol' if env_type == 'enumerate' else 'ul'
        items = re.split(r'\\item\s*', content)
        items = [item.strip() for item in items if item.strip()]
        lis = [f'<li>{item}</li>' for item in items]
        return f'<{tag}>\n' + '\n'.join(lis) + f'\n</{tag}>'

    text = re.sub(
        r'\\begin\{(enumerate|itemize)\}(.*?)\\end\{\1\}',
        process_list, text, flags=re.DOTALL
    )
    return text


def parse_tex(filepath):
    """解析单月 .tex 文件，提取所有题目和解答"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    problems = []

    # 匹配 \begin{problem}{日期} ... \end{problem}
    prob_pattern = re.compile(r'\\begin\{problem\}\{([\d\.]+)\}(.*?)\\end\{problem\}', re.DOTALL)
    
    for match in prob_pattern.finditer(content):
        date_str = match.group(1)
        prob_content = match.group(2).strip()

        # 提取月份 (如 2026.05)
        month_str = date_str.rsplit('.', 1)[0]

        # 提取 solution (可能在 problem 内部)
        sol_match = re.search(r'\\begin\{solution\}(.*?)\\end\{solution\}', prob_content, re.DOTALL)
        solution = sol_match.group(1).strip() if sol_match else ""

        # 题目部分 = 去除 solution 后的内容
        question = re.sub(r'\\begin\{solution\}.*?\\end\{solution\}', '', prob_content, flags=re.DOTALL).strip()

        # 转换图片和列表
        question = convert_includegraphics(question)
        question = convert_lists(question)
        solution = convert_includegraphics(solution)
        solution = convert_lists(solution)

        problems.append({
            "date": date_str,
            "month": month_str,
            "question": question,
            "solution": solution,
        })

    return problems


def make_html(problem, is_first_in_month, show_solution):
    """将一道题转为 HTML 块"""
    date = problem["date"]
    month = problem["month"]
    question = problem["question"]
    solution = problem["solution"]

    # 如果是该月第一道题，插入锚点
    anchor = f'<div id="{month}" class="month-anchor"></div>\n' if is_first_in_month else ''

    # 根据参数决定是否生成解答区块
    solution_block = ""
    if show_solution and solution:
        solution_block = f"""
      <div class="proof">
        <details>
          <summary><em>Solution:</em></summary>
          <div class="anim-wrap"><div class="anim-inner">
            {solution}
          </div></div>
        </details>
      </div>"""

    block = f"""
{anchor}<div class="problem">
  <details open>
    <summary><strong>{date}.</strong></summary>
    <div class="anim-wrap"><div class="anim-inner">
      {question}
      {solution_block}
    </div></div>
  </details>
</div>"""
    return block


def make_nav(months_in_order):
    """生成月份导航 HTML"""
    html = ''
    current_year = ''

    for m in months_in_order:
        year = m[:4]
        month_num = m[5:]
        month_name = MONTH_EN.get(month_num, month_num)

        if year != current_year:
            html += f'<div class="nav-year">{year}</div>'
            current_year = year

        html += f'<a href="#{m}" class="nav-link"><span class="dot"></span>{month_name}</a>\n'

    return html


def main():
    # 解析命令行参数，默认为 1 (显示答案)
    show_solution = True
    if len(sys.argv) > 1:
        if sys.argv[1] == '0':
            show_solution = False
        elif sys.argv[1] == '1':
            show_solution = True
        else:
            print("⚠ Invalid argument. Use 0 (hide solution) or 1 (show solution).")
            return

    all_problems = []

    if not os.path.isdir(PROBLEMS_DIR):
        print(f"❌ Folder {PROBLEMS_DIR}/ not found")
        return

    # 遍历文件夹，读取所有 .tex 文件
    for filename in os.listdir(PROBLEMS_DIR):
        if not filename.endswith(".tex"):
            continue
        filepath = os.path.join(PROBLEMS_DIR, filename)
        parsed = parse_tex(filepath)
        all_problems.extend(parsed)

    # 按日期降序排序
    all_problems.sort(key=lambda p: p["date"], reverse=True)

    # 收集月份并保持降序
    months_seen = OrderedDict()
    for p in all_problems:
        months_seen[p["month"]] = True
    months_in_order = list(months_seen.keys())

    # 生成题目 HTML
    blocks = []
    first_month_done = set()
    for p in all_problems:
        is_first = p["month"] not in first_month_done
        if is_first:
            first_month_done.add(p["month"])
        blocks.append(make_html(p, is_first, show_solution))

    # 生成导航 HTML
    nav_html = make_nav(months_in_order)

    # 读取模板并替换
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    final_html = template.replace("<!-- PROBLEMS_HERE -->", "\n".join(blocks))
    final_html = final_html.replace("<!-- MONTH_NAV_HERE -->", nav_html)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_html)

    status = "WITH SOLUTIONS" if show_solution else "WITHOUT SOLUTIONS"
    print(f"✅ Generated {OUTPUT_FILE} ({status}), {len(all_problems)} problems across {len(months_in_order)} months")


if __name__ == "__main__":
    main()
