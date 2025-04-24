import subprocess
import os
from m3u8_extractor import extract_m3u8_url
from urllib.parse import urljoin
import logging
import sys
import atexit
import time
import random
import json
import signal

# 缓存m3u8链接的文件名
M3U8_CACHE_FILE = "m3u8_cache.json"
PROCESS_MANAGER_FILE = "download_manager.pid"

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
        # 这里放置原来的下载逻辑
        status_file = os.path.join(output_dir, "download_status.json")
        status = {"completed": [], "failed": []}

        for ep_num in episode_numbers:
            str_ep_num = str(ep_num)
            if str_ep_num not in m3u8_cache:
                continue

            m3u8_url = m3u8_cache[str_ep_num]

            # 创建日志文件
            progress_log = os.path.join(output_dir, f"episode_{ep_num}_progress.log")
            with open(progress_log, 'a') as log:
                log.write(f"\n=== 开始下载第 {ep_num} 集 ===\n")
                log.write(f"m3u8 URL: {m3u8_url}\n")
                log.write(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            output_file = os.path.join(output_dir, f"{title}_第{ep_num}集.%(ext)s")

            cmd = [
                'yt-dlp',
                '--newline',
                '--progress',
                '-o', output_file,
                '--merge-output-format', 'mp4',
                '--verbose',
                m3u8_url
            ]

            # 启动下载进程
            process = subprocess.Popen(
                cmd,
                stdout=open(progress_log, 'a'),
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if sys.platform != "win32" else None
            )

            # 记录进程信息
            with open(os.path.join(output_dir, "active_downloads.txt"), 'a') as f:
                f.write(f"{ep_num},{process.pid}\n")

            # 等待下载完成
            while process.poll() is None:
                time.sleep(10)

            # 更新状态
            if process.returncode == 0:
                status["completed"].append(ep_num)
            else:
                status["failed"].append(ep_num)

            with open(status_file, 'w') as f:
                json.dump(status, f)

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
        progress_log = os.path.join(output_dir, f"episode_{ep_num}_progress.log")
        logger.info(f"  tail -f '{progress_log}'  # 查看第 {ep_num} 集进度")

    logger.info("🛑 停止所有下载: pkill yt-dlp")
    logger.info("🔍 检查活动下载: cat active_downloads.txt")