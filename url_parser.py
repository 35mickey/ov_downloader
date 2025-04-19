import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re,time,random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5) AppleWebKit/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15"
]

def create_scraper():
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True,
            'mobile': False
        },
        delay=10,
        interpreter='nodejs',  # 使用NodeJS引擎提高破解成功率
        captcha={
            'provider': '2captcha',
            'api_key': 'YOUR_API_KEY'  # 可选：付费验证码服务
        }
    )

def parse_video_page(url):
    try:
        # 使用cloudscraper绕过Cloudflare
        scraper = create_scraper()

        # 首次请求带完整headers
        headers = {
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.google.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }

        for attempt in range(3):
            try:
                response = scraper.get(url, headers=headers, timeout=30)
                if response.status_code == 403:
                    # 动态切换User-Agent
                    headers['User-Agent'] = random.choice(USER_AGENTS)
                    # 添加Cloudflare绕过参数
                    response = scraper.get(url + '?bypass=1', headers=headers)

                response.raise_for_status()
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))

        # 检查验证码页面
        if "Cloudflare" in response.text:
            raise Exception("触发Cloudflare防护，请手动解决验证码")

        # 检查是否是Cloudflare验证页面
        if "Just a moment" in response.text:
            print("Cloudflare protection detected. Trying to bypass...")
            # 可以添加重试逻辑或其他处理

        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取电视剧名称
        title = extract_title(soup, url)

        # 提取每一集的播放URL
        episode_urls = extract_episode_urls(soup, url)

        return {
            'title': title,
            'episode_urls': episode_urls,
            'source_url': url
        }
    except Exception as e:
        print(f"Error parsing {url}: {str(e)}")
        return None

def extract_title(soup, url):
    # 尝试多种方式提取标题
    title = None

    # 方式1：从meta标签中提取
    meta_title = soup.find('meta', property='og:title')
    if meta_title and meta_title.get('content'):
        title = meta_title['content']

    # 方式2：从title标签中提取
    if not title:
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            # 清理标题中的不必要部分
            title = title.split('-')[0].split('|')[0].split('_')[0].strip()

    # 方式3：从h1标签中提取
    if not title:
        h1_tag = soup.find('h1')
        if h1_tag:
            title = h1_tag.get_text().strip()

    # 如果有《》，则只提取其中的内容
    if title and '《' in title and '》' in title:
        # 使用正则表达式提取《》中的内容
        import re
        match = re.search(r'《(.*?)》', title)
        if match:
            title = match.group(1)

    return title

def extract_episode_urls(soup, base_url):
    episode_urls = []

    # 针对第一个网站的特殊处理
    if "jslpsp.com" in base_url:
        # 查找所有包含"播放我的后半生"的链接
        episode_links = soup.find_all('a', class_='module-play-list-link',
                                   string=lambda text: text and '播放我的后半生' in text)
        if not episode_links:
            # 或者查找所有包含"第XX集"的链接
            episode_links = soup.find_all('a', class_='module-play-list-link',
                                        string=lambda text: text and '第' in text and '集' in text)

    # 其他网站的通用处理
    else:
        # 原来的提取逻辑
        episode_links = soup.find_all('a', string=lambda text: text and '第' in text and '集' in text)
        if not episode_links:
            episode_links = soup.find_all('a', string=lambda text: text and any(char.isdigit() for char in text))
        if not episode_links:
            episode_links = soup.find_all('a', class_=lambda cls: cls and ('play' in cls or 'episode' in cls))
        if not episode_links:
            episode_links = soup.find_all('a', href=lambda href: href and ('vodplay' in href or 'bo' in href or 'play' in href))

    for link in episode_links:
        href = link.get('href')
        if href:
            full_url = urljoin(base_url, href)
            episode_urls.append(full_url)

    # 去重
    episode_urls = list(set(episode_urls))

    # 按集数排序
    try:
        episode_urls.sort(key=lambda x: extract_episode_number(x))
    except:
        pass

    return episode_urls

def extract_episode_number(url):
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