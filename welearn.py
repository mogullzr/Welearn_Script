import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import messagebox
from selenium.webdriver.common.action_chains import ActionChains

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


def start_login():
    username = username_entry.get()
    password = password_entry.get()

    if not username or not password:
        messagebox.showerror("错误", "用户名或密码不能为空！")
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

            root_url = f"https://welearn.sflep.com/student/course_info.aspx?cid={ccid}"
            driver.get(root_url)
            time.sleep(3)
            panel = driver.find_elements(By.CSS_SELECTOR, ".panel.panel-default")
            chapter = len(panel) - 1
            panel_sum = driver.find_elements(By.CSS_SELECTOR, ".progress_fix")
            chapter_title_sum = {}
            index = 0
            for panel_little in panel_sum:
                text = panel_little.text
                num = int(text.split('/')[1])
                chapter_title_sum[index] = num
                index += 1
            for i in range(1, chapter + 1):
                for j in range(1, chapter_title_sum[i] + 1):
                    url = f"https://welearn.sflep.com/student/StudyCourse.aspx?cid=3313&classid=602663&sco=m-2-{i}-{j}"
                    # 跳转到学习页面并切换到 iframe
                    driver.get(url)
                    iframe = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                    )

                    time.sleep(0.3)
                    driver.switch_to.frame(iframe)
                    # print(driver.page_source)
                    print(driver.find_elements(By.CSS_SELECTOR, "[data-submitted]"))
                    if driver.find_elements(By.CSS_SELECTOR, "[data-submitted]") != []:
                        driver.switch_to.default_content()
                        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
                        button.click()
                        continue
                    # 1.处理选择题逻辑
                    choice_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-controltype='choice']")
                    fillinglong_elements = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='fillinglong']")
                    filling_elements = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='filling']")
                    click_elements = driver.find_elements(By.CSS_SELECTOR, ".ChooseBox.block_content.p")

                    if choice_elements != []:  # 如果选择题存在
                        ul_elements = driver.find_elements(By.CSS_SELECTOR, "ul[data-itemtype='options']")  # 获取所有的ul
                        for ul in ul_elements:  # 遍历所有的ul
                            options_li = ul.find_elements(By.TAG_NAME, "li")  # 获取每个ul下的所有li元素
                            for option in options_li:
                                solution = option.get_attribute("data-solution")
                                if solution != None:  # 如果有解决方案
                                    driver.execute_script("arguments[0].click();", option)
                                    time.sleep(0.3)
                                    print(f"已选择答案: {solution}")
                                    break  # 找到后退出循环

                    # 2.处理填空题1逻辑
                    if fillinglong_elements != []:  # 判断填空题是否存在
                        filling_questions = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='fillinglong']")
                        for question in filling_questions:
                            time.sleep(0.3)
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
                                driver.execute_script("arguments[0].scrollIntoView(true);", input_field)
                                driver.execute_script("arguments[0].value = '';", input_field)
                                if input_field != "(Answers may vary.)":
                                    # 使用 JavaScript 向输入框发送文本
                                    driver.execute_script("arguments[0].value = arguments[1];", input_field, cleaned_solution)
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
                            time.sleep(0.3)

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
                                if input_field != "(Answers may vary.)":
                                    driver.execute_script("arguments[0].value = arguments[1];", input_field,
                                                          cleaned_solution)  # 填写答案
                                else:
                                    driver.execute_script("arguments[0].value = arguments[1];", input_field, "None")

                    if click_elements != []:
                        # 先模拟点击一下：
                        filling_questions = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='filling']")
                        click_here_style = driver.find_element(By.CLASS_NAME, "click_here_style")
                        driver.execute_script("arguments[0].click()", click_here_style)
                        time.sleep(0.1)
                        click_li = driver.find_element(By.CSS_SELECTOR, ".ChooseSheet_cell_flex li:first-child")
                        time.sleep(0.1)
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

                                time.sleep(0.1)
                                # 获取当前值并进行检查
                                all_li_elements = driver.find_elements(By.CSS_SELECTOR, ".ChooseSheet_cell_flex li")
                                for li in all_li_elements:
                                    span_content = li.find_element(By.TAG_NAME, "span").text.replace(' ', '')
                                    solution = solution.replace(' ', '')
                                    if span_content == solution:
                                        driver.execute_script("arguments[0].click();", li)
                                        break
                    # 4.处理点击题
                    # if click_elements != []:
                    #     filling_questions = driver.find_elements(By.CSS_SELECTOR, "[data-controltype='filling']")
                    #     for question in filling_questions:
                    #         # 等待并获取填写框
                    #         input_field = WebDriverWait(question, 10).until(
                    #             EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-itemtype='input']"))
                    #         )
                    #         # 等待并获取标准答案
                    #         result_div = WebDriverWait(question, 10).until(
                    #             EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-itemtype='result']"))
                    #         )
                    #
                    #         solution = result_div.get_attribute('innerHTML').strip()  # 获取 HTML 内容，并去除多余空格
                    #         if not solution:  # 如果结果为空，则打印调试信息
                    #             print("警告: 标准答案为空")
                    #         else:
                    #             # 清理答案，去除连续空格和换行符
                    #             cleaned_solution = clean_solution(solution)
                    #             print(f"标准答案: {cleaned_solution}")
                    #             driver.execute_script("arguments[0].value = '';", input_field)
                    #             if input_field != "(Answers may vary.)":
                    #                 driver.execute_script("arguments[0].value = arguments[1];", input_field, cleaned_solution)  # 填写答案
                    #             else:
                    #                 driver.execute_script("arguments[0].value = arguments[1];", input_field, "None")

                    if choice_elements == [] and fillinglong_elements == [] and filling_elements == [] and click_elements == []:
                        time.sleep(0.5)
                        driver.switch_to.default_content()
                        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
                        driver.execute_script("arguments[0].click();", button)
                        continue

                    submit_button = driver.find_element(By.CSS_SELECTOR, "[data-controltype='submit']")
                    if submit_button == []:
                        driver.switch_to.default_content()
                        button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
                        driver.execute_script("arguments[0].click();", button)
                        continue
                    time.sleep(0.3)
                    # 可能出现点不到button的情况
                    driver.execute_script("arguments[0].click();", submit_button)
                    time.sleep(0.3)
                    submit_button = driver.find_element(By.CLASS_NAME, "layui-layer-btn0")
                    driver.execute_script("arguments[0].click();", submit_button)
                    # 可选：提交或保存答案
                    time.sleep(0.3)
                    # 打印完成信息
                    driver.switch_to.default_content()
                    button = driver.find_element(By.CSS_SELECTOR, "a[href='javascript:ReturnMain();']")
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.3)
        except Exception as e:
            print(f"报错了: {e}")
    except Exception as e:
        messagebox.showerror("错误", f"脚本启动失败：{e}")
    finally:
        driver.quit()

if __name__ == '__main__':
    # 创建主窗口
    root = tk.Tk()
    root.title("登录自动化工具")

    # 窗口尺寸
    window_width = 500
    window_height = 300

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