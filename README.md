# ov_downloader
Online video downloader, only support m3u8 yet

一个在线视频下载器，目前只支持m3u8的在线视频流

# Dependency
```
# 安装yt-dlp, aria2c下载工具
sudo apt install yt-dlp aria2c

# 安装 cloudscraper, bs4, psutil
pip install cloudscraper beautifulsoup4 psutil
```

# How to Use
```
# 下载操作
python3 ov_downloader.py [在线视频链接]

# 监控下载状态
python3 monitor.py [视频下载目录]
```
