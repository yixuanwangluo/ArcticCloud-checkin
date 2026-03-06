# -*- coding: utf-8 -*-
print(">>> ArcticCloud 自动续期脚本启动 <<<", flush=True)

import os
import sys
import time
import logging
import requests
import re
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================== 环境变量 ==================
USERNAME = os.environ.get("ARCTIC_USERNAME")
PASSWORD = os.environ.get("ARCTIC_PASSWORD")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
HEADLESS = os.environ.get("HEADLESS", "true").lower() == "true"

WAIT_TIMEOUT = int(os.environ.get("WAIT_TIMEOUT", "60"))

# ================== 日志 ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ================== Telegram ==================
def escape_md(text: str) -> str:
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text or "")

def send_telegram(msg: str):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={"chat_id": TG_CHAT_ID, "text": escape_md(msg), "parse_mode": "MarkdownV2"},
            timeout=15
        )
    except Exception:
        logging.warning("Telegram 发送失败（已忽略）", exc_info=True)

# ================== 调试：落盘页面和截图 ==================
def dump_debug(driver, tag: str):
    try:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        png = f"/tmp/arcticcloud_{tag}_{ts}.png"
        html = f"/tmp/arcticcloud_{tag}_{ts}.html"
        driver.save_screenshot(png)
        with open(html, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logging.info(f"已保存调试文件：{png} / {html}")
    except Exception:
        logging.warning("保存调试文件失败（已忽略）", exc_info=True)

# ================== 浏览器 ==================
def setup_driver():
    logging.info("启动 Chrome Driver")
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    if HEADLESS:
        options.add_argument("--headless=new")  # 新 headless 模式更稳定

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(120)  # 延长页面加载超时
    return driver

# ================== 登录 ==================
def login(driver):
    if not USERNAME or not PASSWORD:
        raise RuntimeError("缺少环境变量：ARCTIC_USERNAME / ARCTIC_PASSWORD")

    logging.info("开始登录")
    driver.get("https://vps.polarbear.nyc.mn/index/login/?referer=")

    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.NAME, "swapname"))
    ).send_keys(USERNAME)

    driver.find_element(By.NAME, "swappass").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//button[contains(., '登录') or contains(., 'Login')]").click()
    WebDriverWait(driver, WAIT_TIMEOUT).until(EC.url_contains("index"))
    logging.info("登录成功")

# ================== 打开第一个产品详情 ==================
def open_first_product_detail(driver):
    logging.info("进入产品管理页面")
    driver.get("https://vps.polarbear.nyc.mn/control/index/detail/")
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//table"))
    )
    row = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//table//tbody/tr[1]"))
    )

    try:
        cols = row.find_elements(By.XPATH, "./td")
        instance_name = cols[1].text.strip() if len(cols) >= 2 else ""
    except Exception:
        instance_name = ""
    instance_name = instance_name or "默认实例"

    manage_candidates = [
        ".//a[normalize-space()='管理' or contains(., '管理')]",
        ".//button[normalize-space()='管理' or contains(., '管理')]",
    ]
    for xp in manage_candidates:
        try:
            el = row.find_element(By.XPATH, xp)
            driver.execute_script("arguments[0].click();", el)
            logging.info(f"已点击「管理」进入实例：{instance_name}")
            WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return instance_name
        except Exception:
            pass

    try:
        manage_link = row.find_element(By.XPATH, ".//a[contains(@href,'/control/detail/')]")
        driver.get(manage_link.get_attribute("href"))
        logging.info(f"已打开旧版详情链接：{instance_name}")
        return instance_name
    except Exception as e:
        dump_debug(driver, "open_detail_failed")
        raise RuntimeError("无法从产品列表进入详情页（站点可能改版）") from e

# ================== 续期 ==================
def renew_on_detail_page(driver):
    logging.info("开始在详情页执行续期")
    renew_btn = None
    renew_xpaths = [
        "//button[contains(.,'续费产品') or contains(.,'Renew Product')]",
        "//a[contains(.,'续费产品') or contains(.,'Renew Product')]",
        "//button[contains(@data-target,'modal') and (contains(.,'续期') or contains(.,'Renew'))]",
    ]
    for xp in renew_xpaths:
        try:
            renew_btn = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xp)))
            break
        except TimeoutException:
            continue

    if not renew_btn:
        dump_debug(driver, "renew_btn_not_found")
        raise TimeoutException("找不到『续费产品』按钮（选择器全部失效）")

    driver.execute_script("arguments[0].click();", renew_btn)
    logging.info("已点击续费产品入口")
    time.sleep(1)

    confirm_selectors = [
        (By.CSS_SELECTOR, "input.install-complete"),
        (By.XPATH, "//button[contains(.,'确认') or contains(.,'确定') or contains(.,'提交') or contains(.,'续期') or contains(.,'续费')]"),
        (By.XPATH, "//input[@type='submit' and (contains(@value,'确认') or contains(@value,'确定') or contains(@value,'提交'))]"),
    ]
    confirm_btn = None
    for by, sel in confirm_selectors:
        try:
            confirm_btn = WebDriverWait(driver, 8).until(EC.presence_of_element_located((by, sel)))
            break
        except TimeoutException:
            continue

    if confirm_btn:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", confirm_btn)
        driver.execute_script("arguments[0].click();", confirm_btn)
        logging.info("已点击确认续期")
        return

    checkout_xpaths = [
        "//button[contains(.,'提交') or contains(.,'确认') or contains(.,'下单') or contains(.,'支付')]",
        "//a[contains(.,'提交') or contains(.,'确认') or contains(.,'下单') or contains(.,'支付')]",
        "//input[@type='submit']",
    ]
    for xp in checkout_xpaths:
        try:
            btn = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, xp)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            driver.execute_script("arguments[0].click();", btn)
            logging.info("已在订单/结算页点击提交/确认")
            return
        except TimeoutException:
            continue

    dump_debug(driver, "confirm_not_found")
    raise TimeoutException("已点击续期入口，但找不到确认/提交按钮（可能改成了新流程）")

def renew_single_instance(driver):
    instance_name = open_first_product_detail(driver)
    WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    renew_on_detail_page(driver)
    time.sleep(3)
    send_telegram(
        f"📢 ArcticCloud 续期成功\n"
        f"———————————————\n"
        f"🖥 实例：{instance_name}\n"
        f"✅ 自动续期完成"
    )

# ================== 主程序 ==================
def main():
    driver = None
    max_attempts = 3  # 重试次数
    for attempt in range(1, max_attempts + 1):
        try:
            logging.info(f">>> 第 {attempt} 次尝试 ArcticCloud 自动续期 <<<")
            driver = setup_driver()
            login(driver)
            renew_single_instance(driver)
            logging.info("✅ 续期成功，退出循环")
            break
        except TimeoutException as e:
            logging.warning(f"⚠️ 超时异常: {e}，第 {attempt} 次尝试失败")
            if driver:
                dump_debug(driver, f"timeout_attempt_{attempt}")
        except WebDriverException as e:
            logging.warning(f"⚠️ WebDriver 异常: {e}，第 {attempt} 次尝试失败")
            if driver:
                dump_debug(driver, f"webdriver_attempt_{attempt}")
        except Exception as e:
            err_text = f"{type(e).__name__}: {repr(e)}"
            logging.error("❌ 续期异常: %s", err_text, exc_info=True)
            if driver:
                dump_debug(driver, f"exception_attempt_{attempt}")
            send_telegram(f"❌ ArcticCloud 自动续期失败\n错误：{err_text}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None

        if attempt < max_attempts:
            wait_sec = 5
            logging.info(f"⏳ 等待 {wait_sec} 秒后重试...")
            time.sleep(wait_sec)
        else:
            logging.error("❌ 已达到最大重试次数，自动续期失败")

if __name__ == "__main__":
    main()
