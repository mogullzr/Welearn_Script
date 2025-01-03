import random
import time
import re

import html2text
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import messagebox


def WebDriverStart():
    # 启动 WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

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
    # 去除超过两个空格的连续空格
    solution = re.sub(r'\s{2,}', ' ', solution)
    solution = re.sub(r'<[^>]*>', '', solution)
    # 去除换行符
    solution = solution.replace("\n", " ").replace("\r", " ")
    return solution.strip()  # 去除两端空白


#
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
        options = webdriver.ChromeOptions()
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

        driver.get("https://sso.sflep.com/idsvr/login.html")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))

        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")
        username_field.send_keys(username)
        password_field.send_keys(password)
        driver.find_element(By.ID, "login").click()

        try:
            # 初始化浏览器并登录
            driver.get("https://sso.sflep.com/idsvr/login.html")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))

            # 登录操作
            username_field = driver.find_element(By.ID, "username")
            password_field = driver.find_element(By.ID, "password")
            username_field.send_keys(username)  # 替换为你的用户名
            password_field.send_keys(password)  # 替换为你的密码
            driver.find_element(By.ID, "login").click()
            # 等待页面
            ccid = 3313

            WebDriverWait(driver, 15).until(EC.url_changes("https://sso.sflep.com/idsvr/login.html"))
            # 首先进入根页面
            root_url = f"https://welearn.sflep.com/student/course_info.aspx?cid={ccid}"
            driver.get(root_url)
            panel = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".panel.panel-default"))
            )
            # 获取总的章节数
            chapters = len(panel) - 1
            # 各个章节的结构数量
            panel_sum = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".progress_fix"))
            )

            # 存储各个章节的数量结构
            chapter_title_sum = {}
            index = 0
            for panel_little in panel_sum:
                text = panel_little.text
                num = int(text.split('/')[1])
                chapter_title_sum[index] = num
                index += 1
            # 开始遍历所有的章节小节内容
            for i in range(chapter, chapters + 1):
                for j in range(26, chapter_title_sum[i] + 1):
                    url = f"https://welearn.sflep.com/student/StudyCourse.aspx?cid=3313&classid=602663&sco=m-2-{i}-{j}"
                    # 跳转到学习页面并切换到 iframe
                    driver.get(url)
                    iframe = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                    )
                    driver.switch_to.frame(iframe)
                    # 看看是否存在提交按钮，如果不存在，那么就直接跳过进入下一章节
                    if driver.find_elements(By.CSS_SELECTOR, "[data-submitted]") != []:
                        driver.switch_to.default_content()
                        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
                        button.click()
                        continue

                    # 目前可以处理的题目类型有5种
                    choice_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-controltype='choice']")
                    fillinglong_elements = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='fillinglong']")
                    filling_elements = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='filling']")
                    click_elements = driver.find_elements(By.CSS_SELECTOR, ".ChooseBox.block_content.p")
                    writing_elements = driver.find_elements(By.CSS_SELECTOR, ".common_writing")

                    # 1.处理选择题逻辑
                    if choice_elements != []:
                        ul_elements = driver.find_elements(By.CSS_SELECTOR, "ul[data-itemtype='options']")  # 获取所有的ul
                        for ul in ul_elements:  # 遍历所有的ul
                            options_li = ul.find_elements(By.TAG_NAME, "li")  # 获取每个ul下的所有li元素
                            for option in options_li:
                                solution = option.get_attribute("data-solution")
                                if solution is not None:  # 如果有解决方案
                                    driver.execute_script("arguments[0].click();", option)
                                    time.sleep(0.3)
                                    print(f"已选择答案: {solution}")
                                    break  # 找到后退出循环

                    # 2.处理填空题1逻辑
                    if fillinglong_elements != []:  # 判断填空题是否存在
                        filling_questions = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='fillinglong']")
                        for question in filling_questions:
                            # 等待并获取填写框
                            input_field = WebDriverWait(question, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[data-itemtype='textarea']"))
                            )
                            # 等待并获取标准答案
                            result_div = WebDriverWait(question, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-itemtype='result']"))
                            )

                            solution = result_div.get_attribute('innerHTML').strip()  # 获取 HTML 内容，并去除多余空格
                            if not solution:  # 如果结果为空，则打印调试信息
                                print("警告: 标准答案为空")
                            else:
                                # 清理答案，去除连续空格和换行符
                                cleaned_solution = clean_solution(solution)
                                print(f"标准答案: {cleaned_solution}")
                                driver.execute_script("arguments[0].scrollIntoView(1true);", input_field)
                                driver.execute_script("arguments[0].value = '';", input_field)
                                if cleaned_solution != "(Answers may vary.)":
                                    # 使用 JavaScript 向输入框发送文本
                                    driver.execute_script("arguments[0].value = arguments[1];", input_field,
                                                          cleaned_solution)
                                else:
                                    driver.execute_script("arguments[0].value = arguments[1];", input_field, "None")

                    # 3.处理填空题2逻辑
                    if filling_elements != []:  # 判断填空题2是否存在data-itemtype="input"
                        filling_questions = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='filling']")
                        for question in filling_questions:
                            # 等待并获取填写框
                            input_field = WebDriverWait(question, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-itemtype='input']"))
                            )
                            # 等待并获取标准答案
                            result_div = WebDriverWait(question, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-itemtype='result']"))
                            )

                            solution = result_div.get_attribute('innerHTML').strip()  # 获取 HTML 内容，并去除多余空格
                            if solution.find(solution) != -1:
                                solution = solution.split('/')[0]
                            if not solution:  # 如果结果为空，则打印调试信息
                                print("警告: 标准答案为空")
                            else:
                                # 清理答案，去除连续空格和换行符
                                cleaned_solution = clean_solution(solution)
                                print(f"标准答案: {cleaned_solution}")
                                driver.execute_script("arguments[0].value = '';", input_field)
                                if cleaned_solution != "(Answers may vary.)":
                                    driver.execute_script("arguments[0].value = arguments[1];", input_field,
                                                          cleaned_solution)  # 填写答案
                                else:
                                    driver.execute_script("arguments[0].value = arguments[1];", input_field, "None")

                    # 4.选择点击类型题目逻辑
                    if click_elements != []:
                        # 先模拟点击一下：
                        filling_questions = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='filling']")
                        click_here_style = driver.find_element(By.CLASS_NAME, "click_here_style")
                        driver.execute_script("arguments[0].click()", click_here_style)
                        click_li = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".ChooseSheet_cell_flex li:first-child"))
                        )
                        # 点击找到的元素
                        driver.execute_script("arguments[0].click();", click_li)

                        # 是第一次就执行
                        flag = True
                        for question in filling_questions:
                            # 等待并获取填写框
                            input_field = WebDriverWait(question, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-itemtype='input']"))
                            )

                            # 等待并获取标准答案
                            result_div = WebDriverWait(question, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-itemtype='result']"))
                            )

                            solution = result_div.get_attribute('innerHTML').strip()  # 获取 HTML 内容，并去除多余空格
                            if not solution:  # 如果结果为空，则打印调试信息
                                print("警告: 标准答案为空")
                            else:
                                print(f"标准答案: {solution}")

                                # 第一次点击
                                if flag:
                                    div = driver.find_elements(By.CSS_SELECTOR, "div[data-itemtype='myresult']")[0]
                                    driver.execute_script("arguments[0].click();", div)
                                    flag = False

                                # 获取当前值并进行检查
                                all_li_elements = WebDriverWait(driver, 10).until(
                                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ChooseSheet_cell_flex li"))
                                )
                                for li in all_li_elements:
                                    span_content = li.find_element(By.TAG_NAME, "span").text.replace(' ', '')
                                    solution = solution.replace(' ', '')
                                    if span_content == solution:
                                        driver.execute_script("arguments[0].click();", li)
                                        break

                    # 5.作文类型题目逻辑
                    if writing_elements != []:
                        prompt = ""
                        # 初始化 html2text 转换器
                        html_to_md = html2text.HTML2Text()
                        html_to_md.ignore_links = False  # 保留链接
                        html_to_md.ignore_images = False  # 保留图片

                        # 1. 题目描述
                        prompt += "## 一、题目描述\n"
                        writing_descriptions = driver.find_elements(By.CLASS_NAME, "direction")
                        for description in writing_descriptions:
                            description_html = description.get_attribute("innerHTML")  # 获取 HTML 内容
                            description_md = html_to_md.handle(description_html)  # 转换为 Markdown
                            description_text = clean_solution(description_md.strip())  # 清理内容
                            prompt += f"- {description_text}\n"

                        # 2.题目要求和Tips技巧
                        prompt += "## 二、下面是题目给的一些题目要求和写作小技巧\n"
                        tip_descriptions = driver.find_elements(By.CLASS_NAME, "writing_evaluation_content")
                        for tip in tip_descriptions:
                            tip_html = tip.get_attribute("innerHTML")  # 获取 HTML 内容
                            tip_md = html_to_md.handle(tip_html)  # 转换为 Markdown
                            tip_text = clean_solution(tip_md.strip())  # 清理内容
                            prompt += f"- {tip_text}\n"

                        # 3.引入个性化提示
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
                        # 最终就是使用这个 prompt 调用deepseek的接口进行问答即可，
                        temperature = random.choice([0.8, 0.9, 1.0])
                        answer = DeepSeekAsk(prompt, temperature)

                        # 点击编辑按钮，然后将获取的答案填充进去即可

                        writing_create_icon_button = driver.find_element(By.CLASS_NAME, "writing_create_icon")
                        writing_create_icon_button.click()

                        modify_content = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".my_textarea_content"))
                        )
                        driver.execute_script("arguments[0].value = '';", modify_content)
                        driver.execute_script("arguments[0].value = arguments[1];", modify_content,
                                              answer)

                    # 这一种类型标识什么都没有
                    if choice_elements == [] and fillinglong_elements == [] and filling_elements == [] and click_elements == [] and writing_elements == []:
                        time.sleep(0.5)
                        driver.switch_to.default_content()
                        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
                        driver.execute_script("arguments[0].click();", button)
                        continue

                    time.sleep(0.3)
                    submit_button = driver.find_element(By.CSS_SELECTOR, "[data-controltype='submit']")
                    if submit_button == []:
                        driver.switch_to.default_content()
                        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
                        driver.execute_script("arguments[0].click();", button)
                        continue
                    # 可能出现点不到button的情况
                    driver.execute_script("arguments[0].click();", submit_button)
                    submit_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "layui-layer-btn0"))
                    )
                    # 点击 layui-layer-btn0 按钮
                    driver.execute_script("arguments[0].click();", submit_button)
                    # 可选：提交或保存答案
                    driver.switch_to.default_content()
                    button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
                    driver.execute_script("arguments[0].click();", button)

        except Exception as e:
            print(f"报错了: {e}")
    except Exception as e:
        messagebox.showerror("错误", f"脚本启动失败：{e}")
    finally:
        driver.quit()


if __name__ == '__main__':
    # 创建主窗口
    root = tk.Tk()
    root.title("WeLearn辅助'学习'工具——ByteOJ出版")

    # 窗口尺寸
    window_width = 500
    window_height = 350

    # 获取屏幕尺寸
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # 计算居中位置
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    # 设置窗口大小和位置
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)

    # 设置主窗口背景颜色
    root.configure(bg="#f0f8ff")

    # 标题标签
    title_label = tk.Label(
        root, text="WeLearn辅助'学习'工具——ByteOJ出版", font=("Arial", 20, "bold"), bg="#f0f8ff", fg="#333333"
    )
    title_label.pack(pady=20)

    # 用户名输入框
    username_frame = tk.Frame(root, bg="#f0f8ff")
    username_frame.pack(pady=15)
    tk.Label(
        username_frame, text="用户名:", font=("Arial", 14), bg="#f0f8ff", fg="#333333"
    ).grid(row=0, column=0, padx=15)
    username_entry = tk.Entry(username_frame, font=("Arial", 14), width=30)
    username_entry.grid(row=0, column=1, padx=10)

    # 密码输入框
    password_frame = tk.Frame(root, bg="#f0f8ff")
    password_frame.pack(pady=15)
    tk.Label(
        password_frame, text="密码:", font=("Arial", 14), bg="#f0f8ff", fg="#333333"
    ).grid(row=0, column=0, padx=15)
    password_entry = tk.Entry(password_frame, font=("Arial", 14), show="*", width=30)
    password_entry.grid(row=0, column=1, padx=10)

    # 第几单元开始
    chapter_frame = tk.Frame(root, bg="#f0f8ff")
    chapter_frame.pack(pady=15)
    tk.Label(
        chapter_frame, text="章节:", font=("Arial", 14), bg="#f0f8ff", fg="#333333"
    ).grid(row=0, column=0, padx=15)
    chapter_entry = tk.Entry(chapter_frame, font=("Arial", 14), width=30)
    chapter_entry.grid(row=0, column=1, padx=10)

    # 登录按钮
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

    # 运行主循环
    root.mainloop()
