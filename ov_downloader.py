import sys
from url_parser import parse_video_page
from core_downloader import download_episodes
import os
import logging
from datetime import datetime

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

    logger.info(f"目标URL: {url}\n")
    logger.info(f"=== 电视剧信息 ===")
    logger.info(f"名称: {result['title']}")
    logger.info(f"总集数: {len(result['episode_urls'])}\n")
    logger.info(f"=== 所有剧集URL ===")

    # 按字符串顺序排序
    sorted_episodes = sorted(
        result['episode_urls'],
        key=lambda url: format_number(url)   # 扩展数字方便排序
    )

    # 按字符串顺序排序
    for idx, url in enumerate(sorted_episodes, start=1):
        logger.info(f"{idx}. {url}")

    # 创建下载目录
    download_dir = os.path.join(os.path.dirname(__file__), result['title'])
    os.makedirs(download_dir, exist_ok=True)

    # 获取用户输入
    user_input = input("\n请输入要下载的集数(如: 1 或 1-5): ").strip()

    # 处理用户输入
    if not user_input:
        # 没有输入，优雅退出
        logger.error("未输入集数范围")
        return
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

    # 修改点2：确保下载时也使用排序后的URL列表
    sorted_urls = sorted(result['episode_urls'])
    download_episodes(
        urls=[sorted_urls[ep-1] for ep in episodes_to_download],
        output_dir=download_dir,
        title=result['title'],
        episode_numbers=episodes_to_download,
        logger=logger
    )

    logger.info(f"\n\n* 如果需要强行停止下载请执行: * \n\npkill yt-dlp\n")

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
    import re  # 添加re模块导入
    main()