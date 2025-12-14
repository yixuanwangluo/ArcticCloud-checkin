# ====== 强制可观测（第一行）======
print(">>> arcticcloud.py 已开始执行（TOP LEVEL） <<<", flush=True)

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

print(">>> 所有 import 已完成 <<<", flush=True)

# ================== 环境变量 ==================
USERNAME = os.environ.get("ARCTIC_USERNAME")
PASSWORD = os.environ.get("ARCTIC_PASSWORD")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
HEADLESS = os.environ.get("HEADLESS", "true").lower() == "true"

print(f">>> ENV 检测：USERNAME={'OK' if USERNAME else 'MISSING'} | "
      f"PASSWORD={'OK' if PASSWORD else 'MISSING'} | "
      f"HEADLESS={HEADLESS} <<<", flush=True)

WAIT_TIMEOUT = 60

# ================== 日志 ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.info("logging 系统初始化完成")

# ================== 工具函数 ==================
def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def send_telegram(msg):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logging.warning("Telegram 未配置，跳过推送")
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={
            "chat_id": TG_CHAT_ID,
            "text": msg,
            "parse_mode": "MarkdownV2"
        }, timeout=15)
        logging.info(f"Telegram 返回状态码：{r.status_code}")
    except Exception as e:
        logging.error(f"Telegram 推送异常: {e}")

# ================== 浏览器 ==================
def setup_driver():
    logging.info("开始 setup_driver()")
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    if HEADLE
