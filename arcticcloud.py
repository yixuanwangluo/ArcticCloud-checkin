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

print(
    f">>> ENV 检测：USERNAME={'OK' if USERNAME else 'MISSING'} | "
    f"PASSWORD={'OK' if PASSWORD else 'MISSING'} | "
    f"HEADLESS={HEADLESS} <<<",
    flush=True
)

WAIT_TIMEOUT = 60

# ================== 日志 ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.info("logging 系统初始化完成")

# ================== 浏览器 ==================
def setup_driver():
    logging.info("开始 setup_driver()")
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
    logging.info("Chrome Driver 启动成功")
    return driver

# ================== 登录 ==================
def login(driver):
    logging.info("进入 login()")
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

# ================== 主流程 ==================
def main():
    print(">>> main() 已进入 <<<", flush=True)
    driver = None
    try:
        logging.info("启动 ArcticCloud 自动续期（MAIN）")
        driver = setup_driver()
        login(driver)
        logging.info("流程走到登录之后（验证用）")
    except Exception as e:
        logging.error("主流程异常", exc_info=True)
        print(f">>> 捕获到异常：{e} <<<", flush=True)
    finally:
        if driver:
            driver.quit()
        logging.info("程序结束")

# ================== 程序入口 ==================
if __name__ == "__main__":
    print(">>> __main__ 入口命中 <<<", flush=True)
    main()
