import subprocess
import os
from m3u8_extractor import extract_m3u8_url
from urllib.parse import urljoin
import logging
import sys
import atexit

def download_episodes(urls, output_dir, title, episode_numbers, logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)

    # 确保程序退出时不会终止子进程
    def cleanup():
        pass

    atexit.register(cleanup)

    for url, ep_num in zip(urls, episode_numbers):
        logger.info(f"\n正在处理第 {ep_num} 集...")

        m3u8_url = extract_m3u8_url(url)
        if not m3u8_url:
            logger.error(f"⚠️ 无法提取第 {ep_num} 集的m3u8链接")
            continue

        output_file = os.path.join(output_dir, f"{title}_第{ep_num}集.%(ext)s")

        try:
            cmd = [
                'yt-dlp',
                '--newline',  # 确保进度输出为逐行模式
                '--progress',  # 显示进度条
                '--no-warnings',
                '-o', output_file,
                '--merge-output-format', 'mp4',
                m3u8_url
            ]

            # 创建进度日志文件
            progress_log = os.path.join(output_dir, f"{title}_第{ep_num}集_progress.log")

            with open(progress_log, 'w') as log_file:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )

            logger.info(f"✅ 后台下载已启动 | 进度查看: tail -f '{progress_log}'")
            logger.info(f"🔗 m3u8地址: {m3u8_url}")
            logger.info(f"📁 保存路径: {output_file.replace('%(ext)s', 'mp4')}")
            logger.info("⏳ 开始下载...")

            # 使用nohup在后台运行
            if sys.platform == "win32":
                # Windows系统
                process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    close_fds=True
                )
            else:
                # Unix-like系统
                process = subprocess.Popen(
                    ['nohup'] + cmd,
                    stdout=open(os.devnull, 'w'),
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setpgrp
                )

            # 不等待进程结束
            logger.info(f"✅ 第 {ep_num} 集已开始后台下载 (PID: {process.pid})")

        except Exception as e:
            logger.error(f"❌ 下载第 {ep_num} 集时发生错误: {str(e)}")