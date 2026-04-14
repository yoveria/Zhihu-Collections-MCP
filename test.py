import requests
import json
import time
from urllib.parse import quote

# ---------- 1. 加载 cookies ----------
with open("cookies.json", "r", encoding="utf-8") as f:
    cookies_list = json.load(f)
cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies_list}

# ---------- 2. 构造完整的请求头 ----------
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Referer": "https://www.zhihu.com/",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "x-requested-with": "fetch",  # 可能为 fetch 或 XMLHttpRequest
    "x-zse-93": "101_3_3.0",  # 固定值，但请确认
    "x-zse-96": "2.0_vS9Wad/v1AdP/KX+pnuKkpjlb=AIeSD+Aa9d0geenkD=TTQMvxDWCq=fqAv9zXzc",  # 必须从浏览器复制最新值！
    # 如果你从浏览器看到其他自定义头，也可以加进来，比如 "x-api-version": "3.0.96"
}


# 定义 include 参数（与浏览器完全一致）
include_param = "data[*].updated_time,answer_count,follower_count,creator,description,is_following,comment_count,created_time;data[*].creator.kvip_info;data[*].creator.vip_info"

# ---------- 3. 获取当前用户的 url_token ----------
me_url = "https://www.zhihu.com/api/v4/me"
me_resp = requests.get(me_url, headers=headers, cookies=cookies_dict)

print("状态码:", me_resp.status_code)
print("响应内容前200字符:", me_resp.text[:200])

if me_resp.status_code != 200:
    print("获取用户信息失败，状态码:", me_resp.status_code)
    print("响应内容:", me_resp.text[:300])
    exit()

user_data = me_resp.json()
url_token = user_data.get("url_token")
print(f"当前用户 url_token: {url_token}")

# ---------- 4. 分页获取所有收藏夹 ----------
all_collections = []
offset = 0
limit = 20

while True:
    encoded_include = quote(include_param, safe="")
    collections_url = f"https://www.zhihu.com/api/v4/people/{url_token}/collections?include={encoded_include}&offset={offset}&limit={limit}"
    resp = requests.get(collections_url, headers=headers, cookies=cookies_dict)

    if resp.status_code != 200:
        print(f"获取收藏夹失败，状态码: {resp.status_code}")
        print("响应内容:", resp.text[:300])
        break

    data = resp.json()
    items = data.get("data", [])
    if not items:
        break

    all_collections.extend(items)
    print(f"已获取 {len(all_collections)} 个收藏夹...")

    if data.get("paging", {}).get("is_end", False):
        break

    offset += limit
    time.sleep(1)  # 避免请求过快

# ---------- 5. 打印结果 ----------
print(f"\n总共获取到 {len(all_collections)} 个收藏夹：")
for col in all_collections:
    print(
        f"  - {col['title']} (公开: {col['is_public']}) -> https://www.zhihu.com/collection/{col['id']}"
    )
