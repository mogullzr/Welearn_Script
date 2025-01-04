import os
import random
import time
import re
from concurrent.futures import ThreadPoolExecutor

import html2text
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import messagebox, scrolledtext

# 初始时间
t1 = 0
# 最后时间
t2 = 0


def initialize_webdriver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 启用无头模式
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
    print(response.choices[0].message.content)
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


def handle_choice_questions(driver):
    choice_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-controltype='choice']")
    if choice_elements:
        ul_elements = driver.find_elements(By.CSS_SELECTOR, "ul[data-itemtype='options']")
        for ul in ul_elements:
            options_li = ul.find_elements(By.TAG_NAME, "li")
            for option in options_li:
                solution = option.get_attribute("data-solution")
                if solution is not None:
                    driver.execute_script("arguments[0].click();", option)
                    time.sleep(0.3)
                    print(f"已选择答案: {solution}")
                    break


def handle_filling_questions(driver, question_type):
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
            print("警告: 标准答案为空")
        else:
            cleaned_solution = clean_solution(solution)
            print(f"标准答案: {cleaned_solution}")
            driver.execute_script("arguments[0].value = '';", input_field)
            if cleaned_solution != "(Answers may vary.)":
                driver.execute_script("arguments[0].value = arguments[1];", input_field, cleaned_solution)
            else:
                driver.execute_script("arguments[0].value = arguments[1];", input_field, "None")


def handle_click_questions(driver):
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
                print("警告: 标准答案为空")
            else:
                print(f"标准答案: {solution}")
                if flag:
                    div = driver.find_elements(By.CSS_SELECTOR, "div[data-itemtype='myresult']")[0]
                    driver.execute_script("arguments[0].click();", div)
                    flag = False

                all_li_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ChooseSheet_cell_flex li"))
                )
                for li in all_li_elements:
                    span_content = li.find_element(By.TAG_NAME, "span").text.replace(' ', '')
                    solution = solution.replace(' ', '')
                    if span_content == solution:
                        driver.execute_script("arguments[0].click();", li)
                        break


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


def process_page(driver, url):
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

    handle_choice_questions(driver)
    handle_filling_questions(driver, "fillinglong")
    handle_filling_questions(driver, "filling")
    handle_click_questions(driver)
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


def worker(username, password, i, chapter_title_sum):
    driver = initialize_webdriver()
    login(driver, username, password)
    for j in range(1, chapter_title_sum[i] + 1):
        url = f"https://welearn.sflep.com/student/StudyCourse.aspx?cid=3314&classid=602663&sco=m-1-{i}-{j}"
        process_page(driver, url)
        print(f"{i}-{j}小节结束！！！！")
    print(f"{i}章节结束！！！！")
    t2 = time.time()
    driver.quit()


# 任务处理函数
def task_worker(driver, task_queue):
    while not task_queue.empty():
        url = task_queue.get()  # 从队列中获取任务
        process_page(driver, url)
        task_queue.task_done()  # 标记任务完成


def show_log_window():
    global log_window, log_text

    log_window = tk.Toplevel()
    log_window.title("日志信息")
    log_window.geometry("600x400")

    log_text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD, width=70, height=20)
    log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # 重定向print输出到日志框
    import sys
    sys.stdout = TextRedirector(log_text, "stdout")


class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert("end", str, (self.tag,))
        self.widget.configure(state="disabled")
        self.widget.see("end")

    def flush(self):
        pass


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
        driver = initialize_webdriver()
        t1 = time.time()
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

        # 使用线程池
        # max_workers=os.cpu_count() // 2
        with ThreadPoolExecutor(chapters) as executor:  # 根据 CPU 核心数调整线程数
            futures = []
            for i in range(chapter, chapters + 1):
                # 提交任务到线程池
                future = executor.submit(worker, username, password, i, chapter_title_sum)
                futures.append(future)

            # 等待所有任务完成
            for future in futures:
                future.result()
    except Exception as e:
        messagebox.showerror("错误", f"脚本启动失败：{e}")


if __name__ == '__main__':
    root = tk.Tk()
    root.title("WeLearn辅助'学习'工具——ByteOJ出版")


    window_width = 500
    window_height = 500
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)
    root.configure(bg="#f0f8ff")

    title_label = tk.Label(
        root, text="WeLearn辅助'学习'工具——ByteOJ出版", font=("Arial", 20, "bold"), bg="#f0f8ff", fg="#333333"
    )
    title_label.pack(pady=20)

    username_frame = tk.Frame(root, bg="#f0f8ff")
    username_frame.pack(pady=15)
    tk.Label(username_frame, text="用户名:", font=("Arial", 14), bg="#f0f8ff", fg="#333333").grid(row=0, column=0,
                                                                                                  padx=15)
    username_entry = tk.Entry(username_frame, font=("Arial", 14), width=30)
    username_entry.grid(row=0, column=1, padx=10)

    password_frame = tk.Frame(root, bg="#f0f8ff")
    password_frame.pack(pady=15)
    tk.Label(password_frame, text="密码:", font=("Arial", 14), bg="#f0f8ff", fg="#333333").grid(row=0, column=0,
                                                                                                padx=15)
    password_entry = tk.Entry(password_frame, font=("Arial", 14), show="*", width=30)
    password_entry.grid(row=0, column=1, padx=10)

    chapter_frame = tk.Frame(root, bg="#f0f8ff")
    chapter_frame.pack(pady=15)
    tk.Label(chapter_frame, text="章节:", font=("Arial", 14), bg="#f0f8ff", fg="#333333").grid(row=0, column=0, padx=15)
    chapter_entry = tk.Entry(chapter_frame, font=("Arial", 14), width=30)
    chapter_entry.grid(row=0, column=1, padx=10)

    login_button = tk.Button(
        root,
        text="启动脚本",
        font=("Arial", 14, "bold"),
        bg="#4682b4",
        fg="white",
        activebackground="#5a9bd3",
        activeforeground="white",
        width=25,
        height=2,
        command=start_login,
        relief="raised",
        bd=3,
    )
    login_button.pack(pady=20)
    # 添加一个按钮，点击后显示日志窗口
    # def on_button_click():
    #     show_log_window()
    #     print("日志窗口已显示！")
    #     print("这是一条测试日志信息。")
    #
    # button = tk.Button(root, text="显示日志窗口", command=on_button_click)
    # button.pack(pady=20)

    root.mainloop()
