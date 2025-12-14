# -*- coding: utf-8 -*-
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

# ================== URL ==================
LOGIN_URL = "https://vps.polarbear.nyc.mn/index/login/?referer="
CONTROL_INDEX_URL = "https://vps.polarbear.nyc.mn/control/index/detail/"

# ================== 日志 ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ================== 工具函数 ==================
def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def send_telegram(msg):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logging.warning("Telegram 未配置，跳过推送")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TG_CHAT_ID,
        "text": msg,
        "parse_mode": "MarkdownV2"
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        if r.status_code == 200:
            logging.info("Telegram 推送成功")
        else:
            logging.error(f"Telegram 推送失败: {r.text}")
    except Exception as e:
        logging.error(f"Telegram 推送异常: {e}")

# ================== 浏览器 ==================
def setup_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    )

    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    if HEADLESS:
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    return driver

# ================== 登录 ==================
def login(driver):
    logging.info("开始登录")
    driver.get(LOGIN_URL)

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.NAME, "swapname"))
    ).send_keys(USERNAME)

    driver.find_element(By.NAME, "swappass").send_keys(PASSWORD)

    driver.find_element(By.XPATH, "//button[contains(., '登录')]").click()

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.url_contains("index/index")
    )
    logging.info("登录成功")

# ================== 续期逻辑 ==================
def renew_instances(driver):
    driver.get(CONTROL_INDEX_URL)
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.url_contains("/control/index")
    )

    buttons = WebDriverWa
