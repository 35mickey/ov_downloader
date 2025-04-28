import sys
from url_parser import parse_video_page
from core_downloader import download_episodes, save_download_status, get_download_status  # 添加导入
import os
import logging
from datetime import datetime
import re

def setup_logging(title):
    """设置简洁的日志记录（仅输出到控制台）"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)  # 仅输出到控制台
        ]
    )

    # 禁止yt-dlp的详细输出
    logging.getLogger('yt-dlp').setLevel(logging.WARNING)
    return logging.getLogger()

def extract_episode_number(text):
    """
    从描述文本中提取集数，例如从 '第10集' 提取 10
    """
    match = re.search(r'第(\d+)集', text)
    return int(match.group(1)) if match else None

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <url>")
        return

    original_url = sys.argv[1]  # 用户提供的原始URL
    result = parse_video_page(original_url)

    if not result:
        print("Failed to parse the URL")
        return

    logger = setup_logging(result['title'])

    logger.info(f"目标URL: {original_url}\n")
    logger.info(f"=== 电视剧信息 ===")
    logger.info(f"名称: {result['title']}")
    logger.info(f"总集数: {len(result['episode_urls'])}\n")
    logger.info(f"=== 所有剧集URL ===")

    # 按字符串顺序排序
    sorted_episodes = sorted(
        result['episode_urls'],
        key=lambda item: format_number(item[0])  # 使用URL进行排序
    )

    # 按字符串顺序排序
    for idx, (url, text) in enumerate(sorted_episodes, start=1):
        logger.info(f"{idx}. {text} ({url})")

    # 创建下载目录
    download_dir = os.path.join(os.path.dirname(__file__), result['title'])
    os.makedirs(download_dir, exist_ok=True)

    # 保存初始状态并记录原始URL
    status = get_download_status(download_dir)
    save_download_status(download_dir, status, original_url=original_url)

    # 获取用户输入后添加确认提示
    user_input = input("\n请输入要下载的编号(如: 1 或 1-5): ").strip()

    # 处理用户输入
    if not user_input:
        logger.error("未输入编号范围")
        return

    # 处理编号范围
    if '-' in user_input:
        start, end = map(int, user_input.split('-'))
        idxs_to_download = list(range(start, end + 1))
    else:
        idxs_to_download = [int(user_input)]

    # 验证输入范围
    max_episode = len(sorted_episodes)
    idxs_to_download = [idx for idx in idxs_to_download if 1 <= idx <= max_episode]

    if not idxs_to_download:
        logger.error("无效的编号范围")
        return

    # 提取对应的集数编号（第X集的X）
    episode_numbers = [
        extract_episode_number(sorted_episodes[ep - 1][1]) for ep in idxs_to_download
    ]

    # 处理输入后添加详细反馈
    logger.info("=== 下载设置 ===")
    logger.info(f"电视剧名称: {result['title']}")
    logger.info(f"下载编号: {idxs_to_download}")
    logger.info(f"存储目录: {download_dir}")

    # 添加确认步骤
    confirm = input("\n确认开始下载？(Y/n): ").strip().lower()
    if confirm and confirm != 'y':
        logger.info("下载已取消")
        return

    logger.info(f"准备下载以下编号集: {idxs_to_download}")

    # 确保下载时也使用排序后的URL列表
    download_episodes(
        urls=[sorted_episodes[ep - 1][0] for ep in idxs_to_download],
        output_dir=download_dir,
        title=result['title'],
        episode_numbers=episode_numbers,  # 传递实际的集数编号
        logger=logger
    )

def format_number(url):
    """
    将url中所有小于100的数字扩展成3位数（高位补0）
    例如：'386769-0-0.html' -> '386769-000-000.html'
         '386769-1-10.html' -> '386769-001-010.html'
    """
    def pad_match(match):
        num = int(match.group())
        if num < 100:
            return f"{num:03d}"  # 补零到3位
        return match.group()  # 大于等于100的数字保持不变

    # 使用正则表达式查找所有数字
    return re.sub(r'\d+', pad_match, url)

if __name__ == "__main__":
    main()