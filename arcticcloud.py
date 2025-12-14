# -*- coding: utf-8 -*-
print(">>> ArcticCloud 自动续期脚本启动 <<<", flush=True)

import os
import sys
import time
import logging
import requests
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ================== 环境变量 ==================
USERNAME = os.environ.get("ARCTIC_USERNAME")
PASSWORD = os.environ.get("ARCTIC_PASSWORD")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
HEADLESS = os.environ.get("HEADLESS", "true").lower() == "true"

WAIT_TIMEOUT = 60

# ================== 日志 ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ================== Telegram ==================
def escape_md(text):
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def send_telegram(msg):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logging.warning("Telegram 未配置，跳过推送")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={
            "chat_id": TG_CHAT_ID,
            "text": escape_md(msg),
            "parse_mode": "MarkdownV2"
        }, timeout=15)
        logging.info(f"Telegram 状态码：{r.status_code}")
    except Exception as e:
        logging.error(f"Telegram 推送异常: {e}")

# ================== 浏览器 ==================
def setup_driver():
    logging.info("启动 Chrome Driver")
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# ================== 登录 ==================
def login(driver):
    logging.info("开始登录")
    driver.get("https://vps.polarbear.nyc.mn/index/login/?referer=")

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.NAME, "swapname"))
    ).send_keys(USERNAME)

    driver.find_element(By.NAME, "swappass").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[contains(., '登录')]").click()

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.url_contains("index/index")
    )
    logging.info("登录成功")

# ================== 续期 ==================
def renew_single_instance(driver):
    logging.info("进入控制台首页")
    driver.get("https://vps.polarbear.nyc.mn/control/index/detail/")

    # ① 找到唯一的「管理 / 详情」按钮
    manage_btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@href,'/control/detail/')]")
        )
    )

    instance_name = manage_btn.text.strip() or "默认实例"
    detail_url = manage_btn.get_attribute("href")

    logging.info(f"进入实例：{instance_name}")
    driver.get(detail_url)

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.url_contains("/control/detail/")
    )

    # ② 点击「续期」
    renew_btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located(
            (By.XPATH, "//button[@data-target='#addcontactmodal']")
        )
    )
    driver.execute_script("arguments[0].click();", renew_btn)
    logging.info("已点击续期按钮")

    # ③ 等弹窗出现
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.ID, "addcontactmodal"))
    )
    time.sleep(1)

    # ④ 点击「确认续期」
    submit_btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input.install-complete")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", submit_btn)

    logging.info("已点击确认续期")

    # ⑤ 等结果
    time.sleep(3)

    msg = (
        f"📢 ArcticCloud 续期成功\n"
        f"———————————————\n"
        f"🖥 实例：{instance_name}\n"
        f"✅ 自动续期完成"
    )
    send_telegram(msg)

# ================== 主程序 ==================
def main():
    driver = None
    try:
        logging.info("启动 ArcticCloud 自动续期（单实例）")
        driver = setup_driver()
        login(driver)
        renew_single_instance(driver)
    except Exception as e:
        logging.error("续期流程异常", exc_info=True)
        send_telegram(f"❌ ArcticCloud 自动续期失败\n错误：{e}")
    finally:
        if driver:
            driver.quit()
        logging.info("脚本执行结束")

if __name__ == "__main__":
    main()
