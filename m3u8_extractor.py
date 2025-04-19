import cloudscraper
import re,time,random
import json
from urllib.parse import urljoin,unquote
from url_parser import create_scraper,USER_AGENTS

def extract_m3u8_url(page_url):
    """优化后的m3u8链接提取函数"""
    def normalize_m3u8_url(url):
        """统一处理URL标准化"""
        if not url:
            return None

        # 去除所有反斜杠（包括转义和未转义的）
        url = url.replace('\\/', '/').replace('\\\\', '/')

        # URL解码
        url = unquote(url)

        # 补全协议头
        if url.startswith('//'):
            url = 'https:' + url
        elif not url.startswith(('http://', 'https://')):
            url = 'https://' + url.lstrip('/')

        # 验证是否为有效的m3u8链接
        if not url.lower().endswith('.m3u8'):
            return None

        return url

    try:
        # 使用cloudscraper绕过Cloudflare
        scraper = create_scraper()
        headers = {
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.google.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }

        # 带重试机制的请求
        for attempt in range(3):
            try:
                response = scraper.get(page_url, headers=headers, timeout=30)
                if response.status_code == 403:
                    headers['User-Agent'] = random.choice(USER_AGENTS)
                    response = scraper.get(page_url + '?bypass=1', headers=headers)
                response.raise_for_status()
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))

        # 检查Cloudflare防护
        if "Cloudflare" in response.text or "Just a moment" in response.text:
            raise Exception("触发Cloudflare防护，请手动解决验证码")

        response.encoding = 'utf-8'
        html = response.text

        # 所有可能的提取方法（按优先级排序）
        extraction_patterns = [
            # 1. 提取JSON格式的player对象
            (r'player_\w+\s*=\s*({.*?});', lambda m: json.loads(m.group(1)).get('url')),

            # 2. 提取直接赋值的play_url
            (r'play_url\s*=\s*["\'](.*?\.m3u8)["\']', lambda m: m.group(1)),

            # 3. 提取加密的url变量
            (r'var\s+url\s*=\s*["\'](.*?)["\']', lambda m: decrypt_url(m.group(1))),

            # 4. 提取iframe嵌套
            (r'<iframe[^>]+src=["\'](.*?)["\']', lambda m: urljoin(page_url, m.group(1))),

            # 5. 通用m3u8链接匹配
            (r'(https?:[\\/]+[^\s"\']+\.m3u8)', lambda m: m.group(1))
        ]

        # 尝试每种提取方法
        for pattern, processor in extraction_patterns:
            try:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    url = processor(match)
                    normalized_url = normalize_m3u8_url(url)
                    if normalized_url:
                        return normalized_url
            except (json.JSONDecodeError, AttributeError, KeyError):
                continue

        return None

    except Exception as e:
        logging.error(f"提取m3u8时出错: {str(e)}", exc_info=True)
        return None

def decrypt_url(encrypted_url):
    """示例解密函数（需根据网站实际加密方式实现）"""
    # 这里应该是网站特定的解密逻辑
    # 例如：base64解码、字符替换等
    return encrypted_url  # 暂时直接返回，需要您补充具体实现

