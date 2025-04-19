import sys
from url_parser import parse_video_page
from core_downloader import download_episodes
import os
import logging
from datetime import datetime

def setup_logging(title):
    """设置简洁的日志记录"""
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 禁止yt-dlp的详细输出
    logging.getLogger('yt-dlp').setLevel(logging.WARNING)
    return logging.getLogger()

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <url>")
        return

    url = sys.argv[1]
    result = parse_video_page(url)

    if not result:
        print("Failed to parse the URL")
        return

    logger = setup_logging(result['title'])

    logger.info("\n=== 电视剧信息 ===")
    logger.info(f"名称: {result['title']}")
    logger.info(f"总集数: {len(result['episode_urls'])}")
    logger.info("\n所有剧集URL:")

    # 按URL名称排序
    sorted_episodes = sorted(
        enumerate(result['episode_urls'], 1),
        key=lambda x: extract_episode_number(x[1])
    )

    for i, url in sorted_episodes:
        logger.info(f"{i}. {url}")

    # 创建下载目录
    download_dir = os.path.join(os.path.dirname(__file__), result['title'])
    os.makedirs(download_dir, exist_ok=True)

    # 获取用户输入
    user_input = input("\n请输入要下载的集数(如: 1 或 1-5), 直接回车下载全部: ").strip()

    # 处理用户输入
    if not user_input:
        # 下载全部
        episodes_to_download = list(range(1, len(result['episode_urls']) + 1))
    elif '-' in user_input:
        # 处理范围
        start, end = map(int, user_input.split('-'))
        episodes_to_download = list(range(start, end + 1))
    else:
        # 单集
        episodes_to_download = [int(user_input)]

    # 验证输入范围
    max_episode = len(result['episode_urls'])
    episodes_to_download = [ep for ep in episodes_to_download if 1 <= ep <= max_episode]

    if not episodes_to_download:
        logger.error("无效的集数范围")
        return

    logger.info(f"\n准备下载以下集数: {episodes_to_download}")

    # 下载剧集
    download_episodes(
        urls=[result['episode_urls'][ep-1] for ep in episodes_to_download],
        output_dir=download_dir,
        title=result['title'],
        episode_numbers=episodes_to_download,
        logger=logger
    )

    logger.info(f"\n* 如果需要强行停止下载请执行: * \n\npkill yt-dlp")

def extract_episode_number(url):
    """从URL中提取集数用于排序"""
    # 尝试从URL中提取集数
    match = re.search(r'第(\d+)集', url)
    if match:
        return int(match.group(1))

    match = re.search(r'(\d+)\.html', url)
    if match:
        return int(match.group(1))

    match = re.search(r'-(\d+)-', url)
    if match:
        return int(match.group(1))

    return 0

if __name__ == "__main__":
    import re  # 添加re模块导入
    main()