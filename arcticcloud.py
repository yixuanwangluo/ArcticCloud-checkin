# -*- coding: utf-8 -*-
print(">>> ArcticCloud 自动签到脚本启动 <<<", flush=True)

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
from webdriver_manager.chrome import ChromeDriverManager

USERNAME = os.environ.get("ARCTIC_USERNAME")
PASSWORD = os.environ.get("ARCTIC_PASSWORD")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
HEADLESS = os.environ.get("HEADLESS", "true").lower() == "true"

WAIT_TIMEOUT = 40

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

def escape_md(text):
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def send_telegram(msg):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": TG_CHAT_ID,
        "text": escape_md(msg),
        "parse_mode": "MarkdownV2"
    }, timeout=15)

def setup_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    if HEADLESS:
        options.add_argument("--headless=new")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

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

def sign_only(driver):
    logging.info("访问控制台首页（签到）")
    driver.get("https://vps.polarbear.nyc.mn/control/index/")

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    time.sleep(2)

    send_telegram(
        "✅ ArcticCloud 自动签到成功\n"
        "———————————————\n"
        "📌 已完成登录并刷新活跃状态"
    )
    logging.info("签到完成")

def main():
    driver = None
    try:
        driver = setup_driver()
        login(driver)
        sign_only(driver)
    except Exception as e:
        logging.error("脚本执行异常", exc_info=True)
        send_telegram(f"❌ ArcticCloud 自动签到失败\n错误：{e}")
    finally:
        if driver:
            driver.quit()
        logging.info("脚本结束")

if __name__ == "__main__":
    main()
