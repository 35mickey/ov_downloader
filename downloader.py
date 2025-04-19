import subprocess
import os
from m3u8_extractor import extract_m3u8_url
from urllib.parse import urljoin

def download_episodes(urls, output_dir, title, episode_numbers):
    for url, ep_num in zip(urls, episode_numbers):
        print(f"\n正在处理第 {ep_num} 集...")

        m3u8_url = extract_m3u8_url(url)
        if not m3u8_url:
            print(f"⚠️ 无法提取第 {ep_num} 集的m3u8链接")
            continue

        # 修改输出文件名格式
        output_file = os.path.join(output_dir, f"{title}_第{ep_num}集.%(ext)s")

        try:
            cmd = [
                'yt-dlp',
                '--no-warnings',
                '-o', output_file,
                '--merge-output-format', 'mp4',
                '--retries', '10',
                '--fragment-retries', '20',
                '--no-abort-on-unavailable-fragment',  # 修正参数名
                '--concurrent-fragments', '8',  # 增加线程数
                '--referer', url,
                '--force-overwrites',
                m3u8_url
            ]

            print(f"🔗 m3u8地址: {m3u8_url}")
            print(f"📁 保存路径: {output_file.replace('%(ext)s', 'mp4')}")
            print("⏳ 开始下载...")

            subprocess.run(cmd, check=True)
            print(f"✅ 第 {ep_num} 集下载完成!")

        except subprocess.CalledProcessError as e:
            print(f"❌ 下载第 {ep_num} 集失败: {str(e)}")
            # 添加详细错误日志
            print("建议尝试手动下载命令:")
            print(' '.join(cmd))
        except Exception as e:
            print(f"❌ 下载第 {ep_num} 集时发生错误: {str(e)}")