import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import zipfile

# 配置
FLARESOLVERR_URL = "http://localhost:8191/v1"   # FlareSolverr 服务地址
DOWNLOAD_DIR = "downloads"
ZIP_NAME = "site.zip"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_cookies_and_ua(url):
    """调用 FlareSolverr 获取 cookies 和 userAgent"""
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": 60000
    }
    resp = requests.post(FLARESOLVERR_URL, json=payload, timeout=90)
    resp.raise_for_status()
    data = resp.json()

    cookies = data["solution"]["cookies"]
    cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    user_agent = data["solution"]["userAgent"]

    return cookie_header, user_agent, data["solution"]["response"]

def save_html(content, url, out_dir=DOWNLOAD_DIR):
    """保存页面 HTML 本身"""
    path = urlparse(url).path
    if path.endswith("/") or path == "":
        rel_path = path.lstrip("/") + "index.html"
    else:
        rel_path = path.lstrip("/")
        if not rel_path.endswith(".html"):
            rel_path += ".html"

    filepath = os.path.join(out_dir, rel_path)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"📄 页面已保存: {rel_path}")

def fetch_resources(url, cookies="", user_agent=""):
    """抓取页面并解析静态资源"""
    headers = {
        "Cookie": cookies,
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": url
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    resources = []

    for tag in soup.find_all(["link", "script", "img"]):
        attr = tag.get("href") or tag.get("src")
        if attr:
            full_url = urljoin(url, attr)
            resources.append(full_url)

    return resources, resp.text

def download_file(url, cookies="", user_agent="", out_dir=DOWNLOAD_DIR):
    """下载单个文件并按网站目录归档"""
    headers = {
        "Cookie": cookies,
        "User-Agent": user_agent,
        "Accept": "*/*",
        "Referer": url
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()

        path = urlparse(url).path
        if path.endswith("/") or path == "":
            filename = "index.html"
            rel_path = path.lstrip("/") + filename
        else:
            filename = os.path.basename(path)
            rel_path = path.lstrip("/")

        filepath = os.path.join(out_dir, rel_path)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "wb") as f:
            f.write(resp.content)

        print(f"✅ 下载成功: {rel_path}")
    except Exception as e:
        print(f"❌ 下载失败: {url} -> {e}")

def zip_dir(source_dir, zip_name):
    """打包目录为 ZIP"""
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, source_dir)
                zipf.write(filepath, arcname)
    print(f"🎉 打包完成 -> {zip_name}")

def main(urls):
    for target_url in urls:
        print(f"\n🔍 获取 {target_url} 的 cookies 和 UA...")
        cookies, user_agent, html_content = get_cookies_and_ua(target_url)
        print("🍪 Cookie:", cookies)
        print("🖥️ User-Agent:", user_agent)

        print(f"📥 抓取页面资源: {target_url}")
        resources, html_text = fetch_resources(target_url, cookies, user_agent)

        # 保存页面本身
        save_html(html_text, target_url)

        print(f"📦 共发现 {len(resources)} 个资源，开始下载...")
        for url in resources:
            download_file(url, cookies, user_agent)

    print("\n📂 开始打包 ZIP...")
    zip_dir(DOWNLOAD_DIR, ZIP_NAME)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 bazhan.py <URL1> [URL2] [URL3] ...")
        sys.exit(1)

    urls = sys.argv[1:]
    main(urls)
