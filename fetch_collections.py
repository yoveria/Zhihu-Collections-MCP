# -*- coding:utf-8 -*-
"""
独立的收藏夹获取脚本
从知乎页面获取用户的所有收藏夹，并更新到config.json文件中
使用知乎 API 方式，支持分页和签名验证
"""
import os
import json
import requests
import time
import random
import logging
from datetime import datetime
import pathlib
import platform
from urllib.parse import quote


def get_current_os():
    """获取当前操作系统类型"""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        return "unknown"


def parse_output_path(path_str, os_type):
    """解析路径，根据操作系统类型处理"""
    if not path_str:
        return None

    if not os_type:
        os_type = get_current_os()

    try:
        if os_type.lower() == "windows":
            path_str = path_str.replace("/", "\\")
            return pathlib.Path(path_str).resolve()
        elif os_type.lower() in [
            "linux",
            "freebsd",
            "openbsd",
            "netbsd",
            "solaris",
            "aix",
        ]:
            if path_str.startswith("~"):
                path_str = os.path.expanduser(path_str)
            return pathlib.Path(path_str).resolve()
        elif os_type.lower() in ["macos", "darwin"]:
            if path_str.startswith("~"):
                path_str = os.path.expanduser(path_str)
            return pathlib.Path(path_str).resolve()
        elif os_type.lower() in ["cygwin", "msys"]:
            if path_str.startswith("/cygdrive/"):
                drive_path = path_str[10:]
                if len(drive_path) >= 2 and drive_path[1] == "/":
                    path_str = (
                        drive_path[0].upper() + ":" + drive_path[1:].replace("/", "\\")
                    )
            elif path_str.startswith("/") and len(path_str) >= 3 and path_str[2] == "/":
                path_str = path_str[1].upper() + ":" + path_str[2:].replace("/", "\\")
            return pathlib.Path(path_str).resolve()
        else:
            logging.warning(f"未知操作系统类型: {os_type}，尝试通用路径处理")
            if path_str.startswith("~"):
                path_str = os.path.expanduser(path_str)
            return pathlib.Path(path_str).resolve()
    except Exception as e:
        logging.error(f"路径解析失败: {path_str}, 错误: {str(e)}")
        return None


def setup_logging():
    """设置日志"""
    logs_dir = os.path.join(os.path.dirname(__file__), "downloads", "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"openCollection_{timestamp}.log"
    log_path = os.path.join(logs_dir, log_filename)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

    return log_path


def load_cookies():
    """加载cookies文件"""
    try:
        with open("cookies.json", "r", encoding="utf-8") as f:
            cookies_list = json.load(f)
        cookies_dict = {}
        for cookie in cookies_list:
            cookies_dict[cookie["name"]] = cookie["value"]
        return cookies_dict
    except FileNotFoundError:
        print("未找到cookies.json文件，将使用无登录模式访问（部分内容可能无法获取）")
        logging.warning("未找到cookies.json文件")
        return {}


def load_config():
    """加载配置文件"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        logging.error("未找到config.json文件")
        print("未找到config.json文件，请确保文件存在")
        return None


def get_all_collections(cookies=None):
    """
    通过知乎 API 获取当前用户的所有收藏夹（支持分页）
    :param cookies: cookies字典
    :return: 收藏夹列表，每个元素为 {"name": "收藏夹名", "url": "https://www.zhihu.com/collection/xxx"}
    """
    # 构造必要的请求头（需要包含签名，否则会返回403）
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
        "x-requested-with": "fetch",
        "x-zse-93": "101_3_3.0",
        # 重要：x-zse-96 签名需要从浏览器复制最新的值，否则会返回403
        # 如果遇到403错误，请重新登录知乎，在浏览器开发者工具中复制对应API请求的 x-zse-96 值
        "x-zse-96": "2.0_vS9Wad/v1AdP/KX+pnuKkpjlb=AIeSD+Aa9d0geenkD=TTQMvxDWCq=fqAv9zXzc",
    }

    # 1. 获取当前用户的 url_token
    me_url = "https://www.zhihu.com/api/v4/me"
    try:
        me_resp = requests.get(me_url, headers=headers, cookies=cookies)
        if me_resp.status_code != 200:
            logging.error(f"获取用户信息失败，状态码: {me_resp.status_code}")
            print(f"获取用户信息失败，状态码: {me_resp.status_code}")
            return []
        user_data = me_resp.json()
        url_token = user_data.get("url_token")
        if not url_token:
            logging.error("未能获取到 url_token")
            print("未能获取到 url_token")
            return []
        logging.info(f"当前用户 url_token: {url_token}")
        print(f"当前用户 url_token: {url_token}")
    except Exception as e:
        logging.error(f"获取用户信息异常: {str(e)}")
        print(f"获取用户信息异常: {str(e)}")
        return []

    # 2. 构造 include 参数（与浏览器保持一致）
    include_param = "data[*].updated_time,answer_count,follower_count,creator,description,is_following,comment_count,created_time;data[*].creator.kvip_info;data[*].creator.vip_info"
    encoded_include = quote(include_param, safe="")

    all_collections = []
    offset = 0
    limit = 20

    while True:
        collections_url = f"https://www.zhihu.com/api/v4/people/{url_token}/collections?include={encoded_include}&offset={offset}&limit={limit}"
        try:
            resp = requests.get(collections_url, headers=headers, cookies=cookies)
            if resp.status_code != 200:
                logging.error(f"获取收藏夹失败，状态码: {resp.status_code}")
                print(f"获取收藏夹失败，状态码: {resp.status_code}")
                if resp.status_code == 403:
                    print(
                        "提示：可能是 x-zse-96 签名已过期，请从浏览器复制最新的签名值并更新脚本中的 headers"
                    )
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                collection_id = item.get("id")
                title = item.get("title")
                if title and collection_id:
                    all_collections.append(
                        {
                            "name": title,
                            "url": f"https://www.zhihu.com/collection/{collection_id}",
                        }
                    )

            logging.info(f"已获取 {len(all_collections)} 个收藏夹...")
            print(f"已获取 {len(all_collections)} 个收藏夹...")

            if data.get("paging", {}).get("is_end", False):
                break

            offset += limit
            time.sleep(random.uniform(0.5, 1.5))  # 随机延时，避免请求过快

        except Exception as e:
            logging.error(f"获取收藏夹异常: {str(e)}")
            print(f"获取收藏夹异常: {str(e)}")
            break

    return all_collections


def update_config_with_collections(collections):
    """
    将获取到的收藏夹更新到config.json中
    :param collections: 收藏夹列表
    :return: 是否成功
    """
    try:
        config = load_config()
        if config is None:
            return False

        config["zhihuUrls"] = collections
        config["openCollection"] = False

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logging.info(f"配置文件已更新，包含{len(collections)}个收藏夹")
        print(f"配置文件已更新，包含{len(collections)}个收藏夹")
        return True
    except Exception as e:
        logging.error(f"更新配置文件失败: {str(e)}")
        print(f"更新配置文件失败: {str(e)}")
        return False


def save_collections_log(collections, log_path):
    """
    保存收藏夹获取日志
    :param collections: 收藏夹列表
    :param log_path: 日志文件路径
    """
    try:
        log_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_collections": len(collections),
            "collections": collections,
            "log_file": log_path,
        }

        logs_dir = os.path.dirname(log_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_log_path = os.path.join(logs_dir, f"openCollection_{timestamp}.json")

        with open(json_log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        logging.info(f"详细日志已保存到: {json_log_path}")
        print(f"详细日志已保存到: {json_log_path}")
    except Exception as e:
        logging.error(f"保存详细日志失败: {str(e)}")


def main():
    """主函数"""
    print("=" * 60)
    print("知乎收藏夹获取工具 (API版)")
    print("=" * 60)

    log_path = setup_logging()
    logging.info("开始执行收藏夹获取任务")
    print(f"日志文件: {log_path}")

    cookies = load_cookies()
    if not cookies:
        print("警告: 未找到有效的cookies，可能无法获取私密收藏夹")
        logging.warning("未找到有效的cookies")

    print("\n开始获取收藏夹列表...")
    logging.info("开始获取收藏夹列表")

    try:
        all_collections = get_all_collections(cookies)

        if not all_collections:
            print("未获取到任何收藏夹")
            logging.warning("未获取到任何收藏夹")
            return False

        print(f"\n总共获取到 {len(all_collections)} 个收藏夹:")
        logging.info(f"总共获取到 {len(all_collections)} 个收藏夹")

        for i, collection in enumerate(all_collections, 1):
            print(f"  {i}. {collection['name']}")
            logging.info(f"收藏夹 {i}: {collection['name']} - {collection['url']}")

        print(f"\n正在更新config.json...")
        success = update_config_with_collections(all_collections)

        if success:
            print("✓ 配置文件更新成功")
            print("✓ openCollection已自动设为false")
            logging.info("配置文件更新成功")

            save_collections_log(all_collections, log_path)

            print(f"\n下一步:")
            print("1. 运行 python main.py 开始下载收藏夹内容")
            print(
                "2. 如需重新获取收藏夹列表，将config.json中的openCollection设为true后重新运行此脚本"
            )
            return True
        else:
            print("✗ 配置文件更新失败")
            logging.error("配置文件更新失败")
            return False

    except Exception as e:
        error_msg = f"获取收藏夹过程中发生错误: {str(e)}"
        print(f"✗ {error_msg}")
        logging.error(error_msg)
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n{'=' * 60}")
        print("收藏夹获取完成！")
        print(f"{'=' * 60}")
    else:
        print(f"\n{'=' * 60}")
        print("收藏夹获取失败！")
        print(f"{'=' * 60}")
        exit(1)
