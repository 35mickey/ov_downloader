import cloudscraper
import re
import json
from urllib.parse import urljoin

def extract_m3u8_url(page_url):
    try:
        # 配置cloudscraper绕过高级防护
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10
        )

        headers = {
            'Referer': 'https://www.wec-wec.org/',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }

        # 获取播放页HTML
        response = scraper.get(page_url, headers=headers)

        # 方法1：提取JavaScript变量中的m3u8
        player_data = re.search(r'player_(?:\w+)\s*=\s*({.*?});', response.text, re.DOTALL)
        if player_data:
            try:
                data = json.loads(player_data.group(1))
                if 'url' in data and data['url'].endswith('.m3u8'):
                    return data['url']
            except json.JSONDecodeError:
                pass

        # 方法2：提取加密的m3u8链接
        encrypted_url = re.search(r'var\s+url\s*=\s*["\'](.*?)["\']', response.text)
        if encrypted_url:
            # 这里添加解密逻辑（根据网站具体加密方式）
            decrypted_url = decrypt_url(encrypted_url.group(1))
            if decrypted_url.endswith('.m3u8'):
                return decrypted_url

        # 方法3：从iframe中提取
        iframe_match = re.search(r'<iframe[^>]+src=["\'](.*?)["\']', response.text)
        if iframe_match:
            iframe_url = urljoin(page_url, iframe_match.group(1))
            return extract_m3u8_url(iframe_url)  # 递归提取

        # 方法4：直接搜索m3u8链接
        m3u8_matches = re.findall(r'(https?:\\?/\\?/[^\s"\']+\.m3u8)', response.text)
        if m3u8_matches:
            normal_url = re.sub(r'\\/', '/', m3u8_matches[0])
            return normal_url

        return None

    except Exception as e:
        print(f"提取m3u8时出错: {str(e)}")
        return None

def decrypt_url(encrypted_url):
    """示例解密函数（需根据网站实际加密方式实现）"""
    # 这里应该是网站特定的解密逻辑
    # 例如：base64解码、字符替换等
    return encrypted_url  # 暂时直接返回，需要您补充具体实现