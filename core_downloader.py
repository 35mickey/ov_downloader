import subprocess
import os
import logging
import sys
import psutil
from typing import Dict, List, Optional
import time
import random
import json
import signal
from m3u8_extractor import extract_m3u8_url
import re
from urllib.parse import urlparse

# 缓存m3u8链接的文件名
M3U8_CACHE_FILE = "m3u8_cache.json"
PROCESS_MANAGER_FILE = "download_manager.pid"

# 修改下载状态文件路径
DOWNLOAD_STATUS_FILE = "download_status.json"
ACTIVE_DOWNLOADS_FILE = "active_downloads.json"  # 改为JSON格式

# 在文档1的顶部添加
STOP_FLAG_FILE = "stop_flag"

def check_stop_flag(output_dir: str) -> bool:
    """检查是否设置了停止标志"""
    return os.path.exists(os.path.join(output_dir, STOP_FLAG_FILE))

def set_stop_flag(output_dir: str):
    """设置停止标志"""
    with open(os.path.join(output_dir, STOP_FLAG_FILE), 'w') as f:
        f.write('1')

def clear_stop_flag(output_dir: str):
    """清除停止标志"""
    try:
        os.remove(os.path.join(output_dir, STOP_FLAG_FILE))
    except FileNotFoundError:
        pass

def get_download_status(output_dir: str) -> Dict:
    """获取下载状态"""
    status_file = os.path.join(output_dir, DOWNLOAD_STATUS_FILE)
    if os.path.exists(status_file):
        with open(status_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "failed": [], "progress": {}}

def save_download_status(output_dir: str, status: Dict, original_url: Optional[str] = None):
    """保存下载状态，并包含原始脚本入参URL"""
    status_file = os.path.join(output_dir, DOWNLOAD_STATUS_FILE)

    # 如果提供了原始URL，将其添加到状态中
    if original_url:
        status["original_url"] = original_url

    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

def update_active_downloads(output_dir: str, ep_num: int, pid: int, m3u8_url: str):
    """更新活动下载记录"""
    active_file = os.path.join(output_dir, ACTIVE_DOWNLOADS_FILE)
    active_data = {}

    if os.path.exists(active_file):
        with open(active_file, 'r', encoding='utf-8') as f:
            active_data = json.load(f)

    active_data[str(ep_num)] = {
        "pid": pid,
        "m3u8_url": m3u8_url,
        "start_time": time.strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(active_file, 'w', encoding='utf-8') as f:
        json.dump(active_data, f, ensure_ascii=False, indent=2)

def remove_active_download(output_dir: str, ep_num: int):
    """移除完成或失败的下载记录"""
    active_file = os.path.join(output_dir, ACTIVE_DOWNLOADS_FILE)
    if os.path.exists(active_file):
        with open(active_file, 'r', encoding='utf-8') as f:
            active_data = json.load(f)

        if str(ep_num) in active_data:
            del active_data[str(ep_num)]

            with open(active_file, 'w', encoding='utf-8') as f:
                json.dump(active_data, f, ensure_ascii=False, indent=2)

def load_m3u8_cache(output_dir):
    """加载缓存的m3u8链接"""
    cache_file = os.path.join(output_dir, M3U8_CACHE_FILE)
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_m3u8_cache(output_dir, cache_data):
    """保存m3u8链接缓存"""
    cache_file = os.path.join(output_dir, M3U8_CACHE_FILE)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

def daemonize():
    """使进程成为守护进程"""
    # 在开始前检查停止标志
    if os.path.exists(os.path.join(os.getcwd(), "stop_flag")):
        sys.exit(0)

    try:
        pid = os.fork()
        if pid > 0:
            # 退出父进程
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork failed: {e}\n")
        sys.exit(1)

    # 脱离终端
    os.setsid()
    os.umask(0)

    # 二次fork确保不会重新获取控制终端
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"second fork failed: {e}\n")
        sys.exit(1)

    # 重定向标准文件描述符
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def write_pid_file(output_dir):
    """写入PID文件"""
    pid_file = os.path.join(output_dir, PROCESS_MANAGER_FILE)
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

def extract_anthology_and_episode(url):
    """从URL中提取anthology和集数"""
    path = urlparse(url).path  # 获取URL的路径部分

    # 使用正则表达式提取最后一个'-'后面的数字
    episode_match = re.search(r'-([0-9]+)(?:\.[a-zA-Z0-9]+)?$', path)
    if episode_match:
        episode_number = episode_match.group(1)  # 提取数字部分
    else:
        episode_number = None

    # 提取最后一个'-'前面到最近的'/'之间的字符串作为anthology
    anthology_match = re.search(r'/([^/]+)-[0-9]+(?:-[0-9]+)?(?:\.[a-zA-Z0-9]+)?$', path)
    if anthology_match:
        anthology = anthology_match.group(1)  # 提取anthology部分
    else:
        anthology = None

    return anthology, episode_number

def download_episodes(urls, output_dir, title, episode_numbers, logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)

    # 加载已有的缓存
    m3u8_cache = load_m3u8_cache(output_dir)

    # 先提取所有m3u8链接并缓存（这部分保持在前台）
    logger.info("⏳ 正在提取m3u8链接...")
    for url, ep_num in zip(urls, episode_numbers):
        if str(ep_num) not in m3u8_cache:
            logger.info(f"正在提取第 {ep_num} 集的m3u8链接...")
            m3u8_url = extract_m3u8_url(url)
            if not m3u8_url:
                logger.error(f"⚠️ 无法提取第 {ep_num} 集的m3u8链接")
                continue
            m3u8_cache[str(ep_num)] = m3u8_url
            save_m3u8_cache(output_dir, m3u8_cache)
            time.sleep(random.uniform(1, 3))

    save_m3u8_cache(output_dir, m3u8_cache)
    logger.info("✅ m3u8链接提取完成并已缓存")

    # 关键修改点：将实际下载部分放入后台
    def run_downloader():
        clear_stop_flag(output_dir)  # 开始前清除停止标志
        status = get_download_status(output_dir)

        for ep_num, url in zip(episode_numbers, urls):
            if check_stop_flag(output_dir):  # 检查停止标志
                logger.info("检测到停止请求，终止下载")
                break

            str_ep_num = str(ep_num)
            if str_ep_num not in m3u8_cache:
                continue

            m3u8_url = m3u8_cache[str_ep_num]
            progress_log = os.path.join(output_dir, f"ep_{ep_num}_progress.log")

            # 清空进度日志
            open(progress_log, 'w').close()

            # 生成输出文件名
            output_file = os.path.join(output_dir, f"{title}_第{ep_num}集.%(ext)s")

            cmd = [
                'yt-dlp',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--newline',
                '--progress',
                '-o', output_file,
                '--merge-output-format', 'mp4',
                '--socket-timeout', '60',
                '--verbose',
                m3u8_url
            ]

            process = subprocess.Popen(
                cmd,
                stdout=open(progress_log, 'a'),
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if sys.platform != "win32" else None
            )

            # 更新活动下载记录
            update_active_downloads(output_dir, ep_num, process.pid, m3u8_url)

            while process.poll() is None:
                if check_stop_flag(output_dir):  # 检查停止标志
                    process.terminate()
                    logger.info(f"已终止第 {ep_num} 集的下载")
                    break
                time.sleep(10)

            # 更新状态
            if process.returncode == 0:
                status["completed"].append(ep_num)
            else:
                status["failed"].append(ep_num)

            # 移除活动记录
            remove_active_download(output_dir, ep_num)
            save_download_status(output_dir, status)

    # 启动后台下载
    if sys.platform == "win32":
        # Windows使用start命令
        subprocess.Popen(
            [sys.executable, __file__, '--daemon'],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            close_fds=True
        )
    else:
        # Unix使用nohup
        pid = os.fork()
        if pid == 0:  # 子进程
            os.setsid()
            run_downloader()
            os._exit(0)

    # 给用户显示关键信息
    logger.info("✅ 后台下载已启动")
    logger.info(f"📁 下载目录: {output_dir}")
    logger.info("📋 可以通过以下方式查看详细进度:")
    for ep_num in episode_numbers:
        progress_log = os.path.join(output_dir, f"ep_{ep_num}_progress.log")
        logger.info(f"  tail -f '{progress_log}'  # 查看第 {ep_num} 集进度")

    logger.info(f"🛑 停止所有下载: python monitor.py {title} --stop")
    logger.info(f"🔍 检查活动下载: python monitor.py {title}")
