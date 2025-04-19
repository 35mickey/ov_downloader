import sys
from url_parser import parse_video_page
from downloader import download_episodes
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <url>")
        return

    url = sys.argv[1]
    result = parse_video_page(url)

    if not result:
        print("Failed to parse the URL")
        return

    print("\n=== 电视剧信息 ===")
    print(f"名称: {result['title']}")
    print(f"总集数: {len(result['episode_urls'])}")
    print("\n前5集URL示例:")
    for i, url in enumerate(result['episode_urls'][:5], 1):
        print(f"{i}. {url}")

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
        print("无效的集数范围")
        return

    print(f"\n准备下载以下集数: {episodes_to_download}")

    # 下载剧集
    download_episodes(
        urls=[result['episode_urls'][ep-1] for ep in episodes_to_download],
        output_dir=download_dir,
        title=result['title'],
        episode_numbers=episodes_to_download
    )

if __name__ == "__main__":
    main()