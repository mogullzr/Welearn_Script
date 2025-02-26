import datetime
import math
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
from webdriver_manager.chrome import ChromeDriverManager

# 初始时间
t1 = time.time()

# 最后时间
t2 = 0

# 全局变量用于存储日志框
log_window = None
log_text = None

# 全局变量用于存储刷课模式
multi_thread_mode = False  # 默认使用普通模式


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
    # 使用 ChromeDriverManager 安装 ChromeDriver，并返回驱动程序的路径
    driver_path = ChromeDriverManager().install()
    # 打印驱动程序路径
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 启用无头模式
    options.add_argument("--disable-css")  # 禁用css
    options.add_argument("--disable-images")  # 图片不加载
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(driver_path), options=options)
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
    """
    使用DeepSeek的API进行AI问答

    :param prompt:GPT专门问答语句
    :param temperature: 某种类型的参数
    :return: AI回答的答案
    """
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
    """
    进行登录逻辑
    :param driver:浏览器驱动
    :param username:用户名/手机号
    :param password:密码
    """

    # 进入Welearn的登录主页
    driver.get("https://sso.sflep.com/idsvr/login.html")

    # 等待该元素暴露再进行下面操作，其他地方的用法也是一个道理
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))

    # 用户名/手机号
    username_field = driver.find_element(By.ID, "username")
    # 手机号
    password_field = driver.find_element(By.ID, "password")

    # 输入用户名/手机号，密码
    username_field.send_keys(username)
    password_field.send_keys(password)

    # 点击登录按钮
    driver.find_element(By.ID, "login").click()
    WebDriverWait(driver, 15).until(EC.url_changes("https://sso.sflep.com/idsvr/login.html"))


def handle_choice_questions(driver, timee, correct_rate):
    """
    刷题: 选择题

    :param driver:浏览器驱动
    :param time: 选项之间等待时间
    :param correct_rate: 正确率
    :return:
    """
    # 获取选择题的标志元素
    choice_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-controltype='choice']")

    if choice_elements:
        total_elements_num = len(choice_elements)
        wrong_choice_num = math.floor(total_elements_num * (1 - correct_rate))

        # 需要设定的错误的题目编号
        wrong_choice_list = random.sample([i for i in range(1, total_elements_num + 1)], wrong_choice_num)
        index = 1

        # 获取题目的选项大列表
        ul_elements = driver.find_elements(By.CSS_SELECTOR, "ul[data-itemtype='options']")
        for ul in ul_elements:
            options_li = ul.find_elements(By.TAG_NAME, "li")
            # 获取每一个题目的小li
            for option in options_li:
                solution = option.get_attribute("data-solution")
                # 题目是否需要选择错误答案
                if index in wrong_choice_list:
                    # 代表当前选项是错误答案
                    if solution is None:
                        driver.execute_script("arguments[0].click();", option)
                        time.sleep(0.3)
                        print_color(f"已选择错误答案: {solution}", color="red", style="bold", isDash=True)
                        break
                # 代表当前选项是正确答案同时这道题目需要选择正确答案
                elif solution is not None:
                    driver.execute_script("arguments[0].click();", option)
                    time.sleep(0.3)
                    print_color(f"已选择正确答案: {solution}", color="red", style="bold", isDash=True)
                    break
            index += 1
            time.sleep(timee)


def handle_filling_questions(driver, question_type, option_time, correct_rate):
    """
    刷题：短填空题 or 长填空题

    :param driver:浏览器驱动
    :param question_type: 问题类型
    :param option_time: 选项之间停留时间
    :param correct_rate: 题目的正确率
    :return:
    """
    # 判断属于什么类型的填空，存在短填空和长填空两种
    if question_type == "fillinglong":
        selector = "[data-controltype='fillinglong']"
        input_selector = "textarea[data-itemtype='textarea']"
    else:
        selector = "[data-controltype='filling']"
        input_selector = "input[data-itemtype='input']"

    filling_questions = driver.find_elements(By.CSS_SELECTOR, selector)

    # 随意挑选错的题目
    total_elements_num = len(filling_questions)
    wrong_filling_num = math.ceil(total_elements_num * (1 - correct_rate) - 0.5)

    # 需要设定的错误的题目编号
    wrong_filling_list = random.sample([i for i in range(1, total_elements_num + 1)], wrong_filling_num)
    index = 1

    for question in filling_questions:
        # 聚焦填空input位置
        input_field = WebDriverWait(question, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, input_selector))
        )

        # 获取题目答案
        result_div = WebDriverWait(question, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-itemtype='result']"))
        )

        solution = result_div.get_attribute('innerHTML').strip()
        if not solution:
            print_color("警告: 标准答案为空", color="red", style="bold", isDash=True)
        else:
            # 清洗标准答案
            cleaned_solution = clean_solution(solution)
            # 当前题目是否在抽取到的错误题目编号当中
            if index in wrong_filling_list:
                # 输入错误答案
                print_color(f"错误答案: {cleaned_solution}", color="red", style="bold", isDash=True)
                driver.execute_script("arguments[0].value = '';", input_field)
                if cleaned_solution != "(Answers may vary.)":
                    prompt = ""
                    if question_type == "fillinglong":
                        # 输入一个和目标单词词性接近的单词
                        prompt = '''
                        请你帮我写一下这个英语单词的其他其他词性的单词，比如形容词、副词、名词都可以，注意输出答案格式需要满足以下条件：
                        1.只输出一个单词
                        这个单词是：
                        ''' + cleaned_solution
                    else:
                        # 输入和对应语句意思接近的语句
                        prompt = '''
                        请你帮我写一下和下面语句意思接近的话语，注意输出答案格式需要满足以下条件：
                        1.我只需要输出的语句结果
                        2.输出的语句只能有一段
                        ''' + cleaned_solution

                    cleaned_solution = DeepSeekAsk(prompt, temperature=0.8)
                    driver.execute_script("arguments[0].value = arguments[1];", input_field, cleaned_solution)
                else:
                    driver.execute_script("arguments[0].value = arguments[1];", input_field, "None")

            else:
                print_color(f"标准答案: {cleaned_solution}", color="red", style="bold", isDash=True)
                driver.execute_script("arguments[0].value = '';", input_field)
                if cleaned_solution != "(Answers may vary.)":
                    driver.execute_script("arguments[0].value = arguments[1];", input_field, cleaned_solution)
                else:
                    driver.execute_script("arguments[0].value = arguments[1];", input_field, "None")
            time.sleep(option_time)
        index += 1


def handle_click_questions(driver, option_time):
    """
    刷题：点击式填空题目

    :param driver:浏览器驱动
    :param option_time: 选项等待时间
    :return:
    """

    # 寻找点击式填空题目
    click_elements = driver.find_elements(By.CSS_SELECTOR, ".ChooseBox.block_content.p")

    if click_elements:
        # 首先点击第一个按钮位置，先打开下框栏
        click_here_style = driver.find_element(By.CLASS_NAME, "click_here_style")
        driver.execute_script("arguments[0].click()", click_here_style)
        click_li = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ChooseSheet_cell_flex li:first-child"))
        )
        driver.execute_script("arguments[0].click();", click_li)

        flag = True
        filling_questions = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='filling']")
        # 开始填充题目答案
        for question in filling_questions:
            # 找题目答案
            result_div = WebDriverWait(question, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-itemtype='result']"))
            )
            solution = result_div.get_attribute('innerHTML').strip()

            # 查看是否存在答案
            if not solution:
                print_color("警告: 标准答案为空", color="red", style="bold", isDash=True)
            else:
                print_color(f"标准答案: {solution}", color="red", style="bold", isDash=True)
                # 第一次点击则需要点击第一个位置聚焦一下
                if flag:
                    div = driver.find_elements(By.CSS_SELECTOR, "div[data-itemtype='myresult']")[0]
                    driver.execute_script("arguments[0].click();", div)
                    flag = False

                # 开始选择正确答案
                all_li_elements = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ChooseSheet_cell_flex li"))
                )
                for li in all_li_elements:
                    span_content = li.find_element(By.TAG_NAME, "span").text.replace(' ', '')
                    solution = solution.replace(' ', '')
                    if span_content == solution:
                        driver.execute_script("arguments[0].click();", li)
                        time.sleep(option_time)
                        break


def handle_writing_questions(driver):
    """
    通过AI写作文

    :param driver:浏览器驱动
    :return:
    """
    # 先获取作文类型题目的标志类名
    writing_elements = driver.find_elements(By.CSS_SELECTOR, ".common_writing")
    if writing_elements:
        # 开始组装prompt
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
            "- 无论是标题、开头、正文还是结尾都只需使用最简单的文本格式，请特别注意标题要和正文格式一致，不要再使用**符号了，同时也不要像类似于Title:Friendship  的格式展示标题了，给出类似于Friendship内容即可，"
            "还有就是需要注意请把作文的格式写得更加像人写的作文格式，\n"
            "感谢你的配合！"
        )

        # DeepSeek的参数设定
        temperature = random.choice([0.8, 0.9, 1.0])
        answer = DeepSeekAsk(prompt, temperature)

        # 点击打开作文编辑页面的按钮
        writing_create_icon_button = driver.find_element(By.CLASS_NAME, "writing_create_icon")
        writing_create_icon_button.click()

        # 聚焦编辑页面
        modify_content = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".my_textarea_content"))
        )
        driver.execute_script("arguments[0].value = '';", modify_content)
        driver.execute_script("arguments[0].value = arguments[1];", modify_content, answer)

        return True
    return False


def process_page(driver, url, wait_time):
    """
    进行页面的刷课刷题模式
    :param driver:浏览器驱动
    :param url: 需要进入的页面url
    :param wait_time: 各个页面至少需要等的间隔时间
    :return:
    """
    # 选项之间填入时间间隔设定
    option_time = 0
    if option_entry.get() != "":
        option_time = int(option_entry.get())

    # 进入对应的 url
    driver.get(url)

    # 网页比较狗，有多个地方使用了iframe嵌套方式来反爬
    iframe = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )
    driver.switch_to.frame(iframe)

    # 查看当前页面的题目是否已经提交过了
    if driver.find_elements(By.CSS_SELECTOR, "[data-submitted]"):
        driver.switch_to.default_content()
        time.sleep(wait_time)
        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
        button.click()
        return

    # 获取正确率，默认为 100
    correct_rate = correct_rate_entry.get()
    if correct_rate == "":
        correct_rate = 100
    else:
        correct_rate = int(correct_rate)
    correct_rate /= 100

    # 开始刷题，一共5种类型的题目
    handle_choice_questions(driver, option_time, correct_rate)
    handle_filling_questions(driver, "fillinglong", option_time, correct_rate)
    handle_filling_questions(driver, "filling", option_time, correct_rate)
    handle_click_questions(driver, option_time)
    isWriting = handle_writing_questions(driver)
    if isWriting:
        # 寻找题目 Submit 按钮
        submit_button = driver.find_element(By.CSS_SELECTOR, "[data-controltype='submit']")
        if not submit_button:
            driver.switch_to.default_content()
            button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
            driver.execute_script("arguments[0].click();", button)
            return

        # 点击 Submit 按钮
        driver.execute_script("arguments[0].click();", submit_button)
        submit_button = WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.CLASS_NAME, "cmd_submit"))
        )
        driver.execute_script("arguments[0].click();", submit_button)
        driver.switch_to.default_content()

        # 返回课程首页
        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")

        # 等待设定的间隔时间
        time.sleep(wait_time)

        # 回到主页面
        driver.execute_script("arguments[0].click();", button)
        return

    # 如果这5中类型的题目没有任何一个匹配得到，就代表页面没有题目
    if not any([driver.find_elements(By.CSS_SELECTOR, selector) for selector in [
        "div[data-controltype='choice']",
        "[data-controltype='fillinglong']",
        "[data-controltype='filling']",
        ".ChooseBox.block_content.p",
        ".common_writing"
    ]]):
        driver.switch_to.default_content()
        time.sleep(wait_time)
        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
        driver.execute_script("arguments[0].click();", button)
        return

    # 寻找题目 Submit 按钮
    submit_button = driver.find_element(By.CSS_SELECTOR, "[data-controltype='submit']")
    if not submit_button:
        driver.switch_to.default_content()
        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
        driver.execute_script("arguments[0].click();", button)
        return

    # 点击 Submit 按钮
    driver.execute_script("arguments[0].click();", submit_button)
    submit_button = WebDriverWait(driver, 100).until(
        EC.presence_of_element_located((By.CLASS_NAME, "layui-layer-btn0"))
    )
    driver.execute_script("arguments[0].click();", submit_button)
    driver.switch_to.default_content()

    # 返回课程首页
    button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")

    # 等待设定的间隔时间
    time.sleep(wait_time)

    # 回到主页面
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


def worker(username, password, i, chapter_title_sum, isSpeed, driver, wait_time):
    """
    刷课、刷题的主线程逻辑

    :param username:用户名/手机号
    :param password:密码
    :param i: 第i章节
    :param chapter_title_sum:第i章节的小节数量
    :param isSpeed:是否为急速模式
    :param driver:浏览器驱动
    :param wait_time:等待时间
    :return:
    """
    if isSpeed:
        driver = initialize_webdriver()
        login(driver, username, password)

    times = datetime.datetime
    for j in range(1, chapter_title_sum + 1):
        # 对应小节开刷时间
        start_date = times.now().strftime("%Y-%m-%d %H:%M:%S")

        # 获取课程ID
        ccid = int(book_entry.get())
        url = f"https://welearn.sflep.com/student/StudyCourse.aspx?cid={ccid}&classid=602663&sco=m-{3315 - ccid}-{i}-{j}"

        # 判断是否需要刷课
        # 1.获取 "用时 00:27" 中的时间部分 + javascript获取隐藏的时间
        target_li = driver.find_element(By.XPATH, f"//li[contains(@onclick, '{3315 - ccid}-{i}-{j}')]")
        time_span = target_li.find_element(By.XPATH, ".//span[contains(text(), '用时')]")
        time_text = driver.execute_script("return arguments[0].textContent;", time_span).strip()  # 获取文本并去除空白字符
        time_value = time_text.replace("用时", "").strip()  # 提取时间部分
        aim_value = "02:00"

        # 2.检查 <i> 标签的 class
        i_tag = target_li.find_element(By.TAG_NAME, "i")
        i_class = i_tag.get_attribute("class")

        # 1.时间是否超过2min 同时 2.是否已经打勾了
        if i_class == "fa fa-check-circle-o" and time_value >= aim_value:
            # print("<i> 标签的 class 是 'fa fa-check-circle-o'")
            continue

        print_color(f"{start_date}:开始刷小节内容：第{i}章-第{j}小节内容(#^.^#)", color="blue", style="bold",
                    isDash=True)

        # 刷课/刷题逻辑
        process_page(driver, url, wait_time)

        # 当前小节刷完时间
        end_date = times.now().strftime("%Y-%m-%d %H:%M:%S")
        print_color(f"{end_date}:已经刷完了第{i}章-第{j}小节内容(#^.^#)", style="bold", color="green", isDash=True)

    # 对应章节结束时间
    print_color(f"{i}章节结束！！！！", color="green", style="bold")

    # 章节花费的总时间计算
    t2 = time.time()
    hours, minutes, seconds = time_diff_to_hms(t1, t2)
    print_color(f"第{i}章节一共花费了{hours}小时{minutes}分钟{seconds}秒O(∩_∩)O", style="bold", color="red",
                isDash=True)

    # 关闭浏览器
    driver.quit()


def show_log_window():
    global log_window, log_text

    log_window = ttk.Toplevel()
    log_window.title("日志信息")
    log_window.geometry("1000x400")

    log_text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD, width=100, height=30)
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
    chapter = chapter_entry.get()
    ccid = book_entry.get()

    if not username or not password:
        messagebox.showerror("错误", "用户名或密码不能为空！")
        return
    if not chapter:
        messagebox.showerror("错误", "开始章节不允许为空！")
        return
    if not ccid:
        messagebox.showerror("错误", "书籍编号不允许为空！")
        return
    messagebox.showinfo("提示", f'''
    用户名:{username}
    密码: {password}
    ''')
    try:
        # 在新线程中运行 Selenium 操作
        selenium_thread = threading.Thread(target=run_selenium_operations, args=(username, password, int(chapter)))
        selenium_thread.start()
    except Exception as e:
        messagebox.showerror("错误", f"脚本启动失败：{e}")


def run_selenium_operations(username, password, chapter):
    # 打开一个Chrome浏览器
    driver = initialize_webdriver()

    # 登录
    login(driver, username, password)

    # 获取课程编号 ccid 并进入课程
    ccid = int(book_entry.get())
    root_url = f"https://welearn.sflep.com/student/course_info.aspx?cid={ccid}"
    driver.get(root_url)

    # 通过 html 结构解析出每个章节的题目的数量
    panel = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".panel.panel-default"))
    )
    chapters = len(panel) - 1
    panel_sum = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".progress_fix"))
    )

    chapter_title_sum = {}
    index = 0
    for panel_little in panel_sum:
        text = panel_little.text
        num = int(text.split('/')[1])
        chapter_title_sum[index] = num
        index += 1

    # 判断是普通模式还是急速模式，True为急速模式，False是普通模式
    if multi_thread_mode:
        # 将随机时间固定修改为0
        wait_time = 0
        # 使用线程池
        with ThreadPoolExecutor(chapters) as executor:
            futures = []
            for i in range(chapter, chapters + 1):
                future = executor.submit(worker, username, password, i, chapter_title_sum[i], multi_thread_mode, None,
                                         wait_time)
                futures.append(future)

            # 等待所有任务完成
            for future in futures:
                future.result()
    else:
        # 单线程模式
        for i in range(chapter, chapters + 1):
            longest_time = 0
            if time_entry.get() != "":
                longest_time = int(time_entry.get())
            wait_time = random.randint(longest_time // 2, longest_time)
            wait_time = max(10, wait_time)
            wait_time = min(20 * 60, wait_time)

            worker(username, password, i, chapter_title_sum[i], multi_thread_mode, driver, wait_time)

    # 刷题完毕，打印日志信息
    date = datetime.datetime
    nowDate = date.now().strftime("%Y-%m-%d %H:%M:%S")
    print_color(f"{nowDate}:刷课结束o(￣▽￣)ｄ!!!!!!!!!!!!!!!!!!!!!!!!!!", style="bold", color="green", isDash=True)


def toggle_thread_mode():
    """
    设定两种刷题模式：
    1.普通模式:就是一个一个刷
    2.急速模式:就是每个章节都开一个窗口多线程刷题
    """
    global multi_thread_mode
    multi_thread_mode = not multi_thread_mode
    mode_text = "急速模式" if multi_thread_mode else "普通模式"
    mode_button.config(text=f"切换模式: {mode_text}")
    print_color(f"已切换到{mode_text}", color="blue", style="bold", isDash=True)


if __name__ == '__main__':
    # 使用 ttkbootstrap 主题
    root = ttk.Window(themename="cosmo")  # 可选主题：cosmo, flatly, journal, etc.
    root.title("WeLearn辅助'学习'工具——ByteOJ出版")

    # 框框长度，宽度
    window_width = 1000
    window_height = 900

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

    # 书籍编号ccid输入
    book_frame = ttk.Frame(main_frame)
    book_frame.pack(pady=10)
    ttk.Label(book_frame, text="书籍编号:", font=("Arial", 14)).grid(row=0, column=0, padx=10)
    book_entry = ttk.Entry(book_frame, font=("Arial", 14), width=30)
    book_entry.grid(row=0, column=1, padx=10)

    # 正确率输入框
    correct_rate_frame = ttk.Frame(main_frame)
    correct_rate_frame.pack(pady=10)
    ttk.Label(correct_rate_frame, text="正确率 (%):", font=("Arial", 14)).grid(row=0, column=0, padx=10)
    correct_rate_entry = ttk.Entry(correct_rate_frame, font=("Arial", 14), width=10)
    correct_rate_entry.grid(row=0, column=1, padx=10)
    correct_rate_entry.insert(0, "100")  # 默认正确率为 100%

    # 各个小节之间刷课等待最长时间
    time_frame = ttk.Frame(main_frame)
    time_frame.pack(pady=10)
    ttk.Label(time_frame, text="最长等待时间(s,可选):", font=("Arial", 14)).grid(row=0, column=0, padx=10)
    time_entry = ttk.Entry(time_frame, font=("Arial", 14), width=18)
    time_entry.grid(row=0, column=1, padx=10)

    # 两个选项之间选择速度的调整
    option_frame = ttk.Frame(main_frame)
    option_frame.pack(pady=10)
    ttk.Label(option_frame, text="选项填入间隔(s,可选):", font=("Arial", 14)).grid(row=0, column=0, padx=10)
    option_entry = ttk.Entry(option_frame, font=("Arial", 14), width=18)
    option_entry.grid(row=0, column=1, padx=10)

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
        text="切换模式: 普通模式",
        style="TButton",
        width=25,
        command=toggle_thread_mode,
    )
    mode_button.pack(pady=10)
    root.mainloop()