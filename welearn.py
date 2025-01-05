import datetime
import os
import random
import time
import re
from concurrent.futures import ThreadPoolExecutor
import threading
import html2text
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# 初始时间
t1 = time.time()
# 最后时间
t2 = 0

# 全局变量用于存储日志框
log_window = None
log_text = None

# 全局变量用于存储刷课模式
multi_thread_mode = True  # 默认使用多线程模式


def print_color(text, color="white", style=None, isDash=None):
    """
    在 Tkinter 的 Text 组件中打印带颜色的文本

    :param text: 要打印的文本
    :param color: 文本颜色（可选：red, green, blue, yellow, white）
    :param style: 文本样式（可选：bold）
    """
    if not log_text:
        return  # 如果日志框未初始化，直接返回

    # 构建标签
    tags = []
    if color:
        tags.append(color)
    if style:
        tags.append(style)
    if isDash:
        text += "\n-------------------------------------------------------------------------------------------------"

    # 插入带颜色的文本
    log_text.configure(state="normal")
    log_text.insert("end", text + "\n", tuple(tags))
    log_text.configure(state="disabled")
    log_text.see("end")  # 自动滚动到底部


def initialize_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 启用无头模式
    options.add_argument("--disable-css")  # 禁用css
    options.add_argument("--disable-images")  # 图片不加载
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service("./chromedriver_win32/chromedriver.exe"), options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        """
    })
    return driver


def clean_solution(solution):
    solution = re.sub(r'\s{2,}', ' ', solution)
    solution = re.sub(r'<[^>]*>', '', solution)
    solution = solution.replace("\n", " ").replace("\r", " ")
    return solution.strip()


def DeepSeekAsk(prompt, temperature):
    api_key = "sk-ecee03845a1b42938fb66bae42694268"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        stream=False
    )
    print_color(response.choices[0].message.content, color="blue", style="bold", isDash=True)
    return response.choices[0].message.content


def login(driver, username, password):
    driver.get("https://sso.sflep.com/idsvr/login.html")
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))

    username_field = driver.find_element(By.ID, "username")
    password_field = driver.find_element(By.ID, "password")
    username_field.send_keys(username)
    password_field.send_keys(password)
    driver.find_element(By.ID, "login").click()
    WebDriverWait(driver, 15).until(EC.url_changes("https://sso.sflep.com/idsvr/login.html"))


def should_answer_correctly(correct_rate, total_questions, correct_count, current_question):
    """
    混合随机与动态调整，确保最终正确率接近设定值
    :param correct_rate: 目标正确率（0 到 100）
    :param total_questions: 总题数
    :param correct_count: 当前已答对的题数
    :param current_question: 当前题号（从 1 开始）
    :return: True 表示回答正确，False 表示回答错误
    """
    target_correct = total_questions * (correct_rate / 100)
    remaining_questions = total_questions - current_question + 1
    required_correct = max(0, target_correct - correct_count)

    # 计算剩余题目中需要答对的比例
    if required_correct / remaining_questions >= 1:
        return True  # 必须答对
    elif required_correct / remaining_questions <= 0:
        return False  # 必须答错
    else:
        return random.random() < (required_correct / remaining_questions)


def handle_choice_questions(driver, correct_rate, total_questions, correct_count, current_question):
    choice_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-controltype='choice']")
    if choice_elements:
        ul_elements = driver.find_elements(By.CSS_SELECTOR, "ul[data-itemtype='options']")
        for ul in ul_elements:
            options_li = ul.find_elements(By.TAG_NAME, "li")
            if should_answer_correctly(correct_rate, total_questions, correct_count[0], current_question[0]):
                # 回答正确：选择第一个正确答案
                for option in options_li:
                    solution = option.get_attribute("data-solution")
                    if solution is not None:
                        driver.execute_script("arguments[0].click();", option)
                        time.sleep(0.3)
                        print_color(f"已选择答案: {solution}", color="red", style="bold", isDash=True)
                        correct_count[0] += 1
                        break
            else:
                # 回答错误：随机选择一个错误答案
                wrong_options = [option for option in options_li if option.get_attribute("data-solution") is None]
                if wrong_options:
                    random.choice(wrong_options).click()
                    print_color("回答错误: 随机选择了一个错误答案", color="yellow", style="bold", isDash=True)
            current_question[0] += 1


def handle_filling_questions(driver, question_type, correct_rate, total_questions, correct_count, current_question):
    if question_type == "fillinglong":
        selector = "[data-controltype='fillinglong']"
        input_selector = "textarea[data-itemtype='textarea']"
    else:
        selector = "[data-controltype='filling']"
        input_selector = "input[data-itemtype='input']"

    filling_questions = driver.find_elements(By.CSS_SELECTOR, selector)
    for question in filling_questions:
        input_field = WebDriverWait(question, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, input_selector))
        )
        result_div = WebDriverWait(question, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-itemtype='result']"))
        )
        solution = result_div.get_attribute('innerHTML').strip()
        if not solution:
            print_color("警告: 标准答案为空", color="red", style="bold", isDash=True)
        else:
            cleaned_solution = clean_solution(solution)
            if should_answer_correctly(correct_rate, total_questions, correct_count[0], current_question[0]):
                # 回答正确：填写标准答案
                print_color(f"标准答案: {cleaned_solution}", color="red", style="bold", isDash=True)
                driver.execute_script("arguments[0].value = '';", input_field)
                if cleaned_solution != "(Answers may vary.)":
                    driver.execute_script("arguments[0].value = arguments[1];", input_field, cleaned_solution)
                else:
                    driver.execute_script("arguments[0].value = arguments[1];", input_field, "None")
                correct_count[0] += 1
            else:
                # 回答错误：填写随机错误答案
                wrong_answer = "错误答案"
                driver.execute_script("arguments[0].value = arguments[1];", input_field, wrong_answer)
                print_color(f"回答错误: 填写了随机错误答案: {wrong_answer}", color="yellow", style="bold", isDash=True)
            current_question[0] += 1


def handle_click_questions(driver, correct_rate, total_questions, correct_count, current_question):
    click_elements = driver.find_elements(By.CSS_SELECTOR, ".ChooseBox.block_content.p")
    if click_elements:
        click_here_style = driver.find_element(By.CLASS_NAME, "click_here_style")
        driver.execute_script("arguments[0].click()", click_here_style)
        click_li = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ChooseSheet_cell_flex li:first-child"))
        )
        driver.execute_script("arguments[0].click();", click_li)

        flag = True
        filling_questions = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='filling']")
        for question in filling_questions:
            input_field = WebDriverWait(question, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-itemtype='input']"))
            )
            result_div = WebDriverWait(question, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-itemtype='result']"))
            )
            solution = result_div.get_attribute('innerHTML').strip()
            if not solution:
                print_color("警告: 标准答案为空", color="red", style="bold", isDash=True)
            else:
                print_color(f"标准答案: {solution}", color="red", style="bold", isDash=True)
                if flag:
                    div = driver.find_elements(By.CSS_SELECTOR, "div[data-itemtype='myresult']")[0]
                    driver.execute_script("arguments[0].click();", div)
                    flag = False

                all_li_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ChooseSheet_cell_flex li"))
                )
                if should_answer_correctly(correct_rate, total_questions, correct_count[0], current_question[0]):
                    # 回答正确：选择正确答案
                    for li in all_li_elements:
                        span_content = li.find_element(By.TAG_NAME, "span").text.replace(' ', '')
                        solution = solution.replace(' ', '')
                        if span_content == solution:
                            driver.execute_script("arguments[0].click();", li)
                            correct_count[0] += 1
                            break
                else:
                    # 回答错误：随机选择一个错误答案
                    wrong_li = random.choice(all_li_elements)
                    driver.execute_script("arguments[0].click();", wrong_li)
                    print_color("回答错误: 随机选择了一个错误答案", color="yellow", style="bold", isDash=True)
                current_question[0] += 1


def handle_writing_questions(driver):
    writing_elements = driver.find_elements(By.CSS_SELECTOR, ".common_writing")
    if writing_elements:
        prompt = ""
        html_to_md = html2text.HTML2Text()
        html_to_md.ignore_links = False
        html_to_md.ignore_images = False

        # 题目描述
        prompt += "## 一、题目描述\n"
        writing_descriptions = driver.find_elements(By.CLASS_NAME, "direction")
        for description in writing_descriptions:
            description_html = description.get_attribute("innerHTML")
            description_md = html_to_md.handle(description_html)
            description_text = clean_solution(description_md.strip())
            prompt += f"- {description_text}\n"

        # 题目要求和Tips技巧
        prompt += "## 二、下面是题目给的一些题目要求和写作小技巧\n"
        tip_descriptions = driver.find_elements(By.CLASS_NAME, "writing_evaluation_content")
        for tip in tip_descriptions:
            tip_html = tip.get_attribute("innerHTML")
            tip_md = html_to_md.handle(tip_html)
            tip_text = clean_solution(tip_md.strip())
            prompt += f"- {tip_text}\n"

        # 引入个性化提示
        prompt += (
            "## 三、请求生成答案\n"
            "请根据上述题目描述和要求，生成该题目的答案。\n"
            "请注意：\n"
            "- 答案必须是完整的，不能包含任何需要手动填写的占位符（如 `your name: []` 或 `[在此处填写]`）。\n"
            "- 答案需结合你的个人经历或观点，使其更具独特性。\n"
            "- 答案需使用英文作文常用的三段式结构，包括以下部分：\n"
            "  1. **标题**：简洁明了，概括文章主题。\n"
            "  2. **开头**：引入主题，明确观点或立场。\n"
            "  3. **正文**：展开论述，提供支持观点的理由或例子。\n"
            "  4. **结尾**：总结全文，重申观点或提出建议。\n"
            "- 无论是标题、开头、正文还是结尾都只需使用最简单的文本格式，请特别注意标题要和正文格式一致，不要再使用**符号了，同时也不要像类似于Title:Friendship  的格式展示标题了，给出类似于Friendship内容即可\n"
            "感谢你的配合！"
        )

        temperature = random.choice([0.8, 0.9, 1.0])
        answer = DeepSeekAsk(prompt, temperature)

        writing_create_icon_button = driver.find_element(By.CLASS_NAME, "writing_create_icon")
        writing_create_icon_button.click()

        modify_content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".my_textarea_content"))
        )
        driver.execute_script("arguments[0].value = '';", modify_content)
        driver.execute_script("arguments[0].value = arguments[1];", modify_content, answer)


def process_page(driver, url, correct_rate, total_questions, correct_count, current_question):
    driver.get(url)
    iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframe)

    if driver.find_elements(By.CSS_SELECTOR, "[data-submitted]") != []:
        driver.switch_to.default_content()
        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
        button.click()
        return

    handle_choice_questions(driver, correct_rate, total_questions, correct_count, current_question)
    handle_filling_questions(driver, "fillinglong", correct_rate, total_questions, correct_count, current_question)
    handle_filling_questions(driver, "filling", correct_rate, total_questions, correct_count, current_question)
    handle_click_questions(driver, correct_rate, total_questions, correct_count, current_question)
    handle_writing_questions(driver)

    if not any([driver.find_elements(By.CSS_SELECTOR, selector) for selector in [
        "div[data-controltype='choice']",
        "[data-controltype='fillinglong']",
        "[data-controltype='filling']",
        ".ChooseBox.block_content.p",
        ".common_writing"
    ]]):
        time.sleep(0.5)
        driver.switch_to.default_content()
        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
        driver.execute_script("arguments[0].click();", button)
        return

    time.sleep(0.3)
    submit_button = driver.find_element(By.CSS_SELECTOR, "[data-controltype='submit']")
    if not submit_button:
        driver.switch_to.default_content()
        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
        driver.execute_script("arguments[0].click();", button)
        return

    driver.execute_script("arguments[0].click();", submit_button)
    submit_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "layui-layer-btn0"))
    )
    driver.execute_script("arguments[0].click();", submit_button)
    driver.switch_to.default_content()
    button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
    driver.execute_script("arguments[0].click();", button)


def time_diff_to_hms(start_time, end_time):
    """
    计算两个时间戳之间的时间差，并返回小时、分钟、秒

    :param start_time: 开始时间戳
    :param end_time: 结束时间戳
    :return: (hours, minutes, seconds)
    """
    time_diff = end_time - start_time
    hours = int(time_diff // 3600)
    minutes = int((time_diff % 3600) // 60)
    seconds = int(time_diff % 60)
    return hours, minutes, seconds


def worker(username, password, i, chapter_title_sum):
    driver = initialize_webdriver()
    login(driver, username, password)
    times = datetime.datetime

    # 获取正确率
    correct_rate = float(correct_rate_entry.get())

    # 统计总题数和已答对的题数
    total_questions = 10  # 假设每章有 10 道题
    correct_count = [0]  # 使用列表以便在函数中修改
    current_question = [1]  # 当前题号

    for j in range(1, 4):
        start_date = times.now().strftime("%Y-%m-%d %H:%M:%S")
        url = f"https://welearn.sflep.com/student/StudyCourse.aspx?cid=3314&classid=602663&sco=m-1-{i}-{j}"
        print_color(f"{start_date}:开始刷小节内容：第{i}章-第{j}小节内容(#^.^#)", color="blue", style="bold", isDash=True)

        process_page(driver, url, correct_rate, total_questions, correct_count, current_question)

        end_date = times.now().strftime("%Y-%m-%d %H:%M:%S")
        print_color(f"{end_date}:已经刷完了第{i}章-第{j}小节内容(#^.^#)", style="bold", color="green", isDash=True)
    print_color(f"{i}章节结束！！！！", color="green", style="bold")
    t2 = time.time()
    hours, minutes, seconds = time_diff_to_hms(t1, t2)
    print_color(f"第{i}章节一共花费了{hours}小时{minutes}分钟{seconds}秒O(∩_∩)O", style="bold", color="red", isDash=True)
    driver.quit()


def show_log_window():
    global log_window, log_text

    log_window = ttk.Toplevel()
    log_window.title("日志信息")
    log_window.geometry("600x400")

    log_text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD, width=70, height=20)
    log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # 定义颜色标签
    log_text.tag_config("red", foreground="red")
    log_text.tag_config("green", foreground="green")
    log_text.tag_config("blue", foreground="blue")
    log_text.tag_config("yellow", foreground="yellow")
    log_text.tag_config("bold", font=("Arial", 10, "bold"))

    # 重定向 print 输出到日志框
    import sys
    sys.stdout = TextRedirector(log_text, "stdout")


class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        """
        重定向 print 输出到 Tkinter 的 Text 组件，并支持带颜色的文本

        :param widget: Tkinter 的 Text 组件
        :param tag: 默认的标签（用于设置颜色和样式）
        """
        self.widget = widget
        self.tag = tag

    def write(self, text):
        """
        将文本插入到 Text 组件中，并根据颜色标签设置样式
        """
        self.widget.configure(state="normal")  # 允许编辑
        self.widget.insert("end", text, (self.tag,))  # 插入文本并应用标签
        self.widget.configure(state="disabled")  # 禁止编辑
        self.widget.see("end")  # 自动滚动到底部

    def flush(self):
        pass  # 必须实现 flush 方法


def start_login():
    username = username_entry.get()
    password = password_entry.get()
    chapter = int(chapter_entry.get())

    if not username or not password:
        messagebox.showerror("错误", "用户名或密码不能为空！")
        return
    if not chapter:
        messagebox.showerror("错误", "开始章节不允许为空！")
        return

    try:
        # 在新线程中运行 Selenium 操作
        selenium_thread = threading.Thread(target=run_selenium_operations, args=(username, password, chapter))
        selenium_thread.start()
    except Exception as e:
        messagebox.showerror("错误", f"脚本启动失败：{e}")


def run_selenium_operations(username, password, chapter):
    driver = initialize_webdriver()
    login(driver, username, password)

    ccid = 3314
    root_url = f"https://welearn.sflep.com/student/course_info.aspx?cid={ccid}"
    driver.get(root_url)
    panel = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".panel.panel-default"))
    )
    chapters = len(panel) - 1
    panel_sum = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".progress_fix"))
    )

    chapter_title_sum = {}
    index = 0
    for panel_little in panel_sum:
        text = panel_little.text
        num = int(text.split('/')[1])
        chapter_title_sum[index] = num
        index += 1

    if multi_thread_mode:
        # 使用线程池
        with ThreadPoolExecutor(chapters) as executor:
            futures = []
            for i in range(chapter, chapters + 1):
                future = executor.submit(worker, username, password, i, chapter_title_sum)
                futures.append(future)

            # 等待所有任务完成
            for future in futures:
                future.result()
    else:
        # 单线程模式
        for i in range(chapter, chapters + 1):
            worker(username, password, i, chapter_title_sum)

    date = datetime.datetime
    nowDate = date.now().strftime("%Y-%m-%d %H:%M:%S")
    print_color(f"{nowDate}:刷课结束o(￣▽￣)ｄ!!!!!!!!!!!!!!!!!!!!!!!!!!", style="bold", color="green", isDash=True)


def toggle_thread_mode():
    global multi_thread_mode
    multi_thread_mode = not multi_thread_mode
    mode_text = "多线程模式" if multi_thread_mode else "单线程模式"
    mode_button.config(text=f"切换模式: {mode_text}")
    print_color(f"已切换到{mode_text}", color="blue", style="bold", isDash=True)


if __name__ == '__main__':
    # 使用 ttkbootstrap 主题
    root = ttk.Window(themename="cosmo")  # 可选主题：cosmo, flatly, journal, etc.
    root.title("WeLearn辅助'学习'工具——ByteOJ出版")

    window_width = 550
    window_height = 600
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)

    # 设置圆角样式
    style = ttk.Style()
    style.configure("TButton", borderwidth=0, relief="flat", padding=10, font=("Arial", 12), background="#4CAF50",
                    foreground="white", bordercolor="#4CAF50", focusthickness=0, focuscolor="none", borderradius=15)
    style.map("TButton", background=[("active", "#45a049")])  # 点击时的背景色

    # 主界面布局
    main_frame = ttk.Frame(root)
    main_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

    title_label = ttk.Label(
        main_frame, text="WeLearn辅助'学习'工具——ByteOJ出版", font=("Arial", 20, "bold")
    )
    title_label.pack(pady=20)

    # 用户名输入框
    username_frame = ttk.Frame(main_frame)
    username_frame.pack(pady=10)
    ttk.Label(username_frame, text="用户名:", font=("Arial", 14)).grid(row=0, column=0, padx=10)
    username_entry = ttk.Entry(username_frame, font=("Arial", 14), width=30)
    username_entry.grid(row=0, column=1, padx=10)

    # 密码输入框
    password_frame = ttk.Frame(main_frame)
    password_frame.pack(pady=10)
    ttk.Label(password_frame, text="密码:", font=("Arial", 14)).grid(row=0, column=0, padx=10)
    password_entry = ttk.Entry(password_frame, font=("Arial", 14), show="*", width=30)
    password_entry.grid(row=0, column=1, padx=10)

    # 章节输入框
    chapter_frame = ttk.Frame(main_frame)
    chapter_frame.pack(pady=10)
    ttk.Label(chapter_frame, text="章节:", font=("Arial", 14)).grid(row=0, column=0, padx=10)
    chapter_entry = ttk.Entry(chapter_frame, font=("Arial", 14), width=30)
    chapter_entry.grid(row=0, column=1, padx=10)

    # 正确率输入框
    correct_rate_frame = ttk.Frame(main_frame)
    correct_rate_frame.pack(pady=10)
    ttk.Label(correct_rate_frame, text="正确率 (%):", font=("Arial", 14)).grid(row=0, column=0, padx=10)
    correct_rate_entry = ttk.Entry(correct_rate_frame, font=("Arial", 14), width=10)
    correct_rate_entry.grid(row=0, column=1, padx=10)
    correct_rate_entry.insert(0, "100")  # 默认正确率为 100%

    # 启动脚本按钮
    login_button = ttk.Button(
        main_frame,
        text="启动脚本",
        style="TButton",
        width=25,
        command=start_login,
    )
    login_button.pack(pady=20)

    # 显示日志窗口按钮
    def on_button_click():
        show_log_window()
        print_color("欢迎━(*｀∀´*)ノ亻!来到ByteOJ创始人——Mogullzr研发的Welearn刷课脚本", style="bold", isDash=False)
        print_color("下面显示的内容是刷课的日志信息(#^.^#)(#^.^#)", style="bold", isDash=True)


    log_button = ttk.Button(
        main_frame,
        text="显示日志窗口",
        style="TButton",
        width=25,
        command=on_button_click,
    )
    log_button.pack(pady=10)

    # 切换刷课模式按钮
    mode_button = ttk.Button(
        main_frame,
        text="切换模式: 多线程模式",
        style="TButton",
        width=25,
        command=toggle_thread_mode,
    )
    mode_button.pack(pady=10)

    root.mainloop()