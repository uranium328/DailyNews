import requests
from bs4 import BeautifulSoup

def fetch_cnn_paragraphs(url: str) -> list:
    # 1. 自訂 headers（可依需求增減）
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        # 其他 headers 如必要可補充：Cookie、Referer...
    }

    # 2. 發送 GET 請求
    response = requests.get(url, headers=headers, timeout=10)

    # 3. 檢查回應狀態
    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: 無法抓取頁面")

    # 4. 解析 HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 5. 尋找指定 class 的段落
    paragraphs = soup.find_all(class_="paragraph-elevate inline-placeholder vossi-paragraph")
    
    # 6. 提取文字內容
    paragraph_texts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if text:  # 只加入非空的段落
            paragraph_texts.append(text)
    
    return paragraph_texts

def fetch_cnn_paragraphs_as_string(url: str) -> str:
    """回傳合併後的段落字串"""
    paragraphs = fetch_cnn_paragraphs(url)
    return '\n\n'.join(paragraphs)

if __name__ == "__main__":
    url = "https://edition.cnn.com/2025/07/28/middleeast/us-thaad-missile-interceptor-shortage-intl-invs"
    try:
        # 方法 1: 回傳段落列表
        paragraphs = fetch_cnn_paragraphs(url)
        print(f"找到 {len(paragraphs)} 個段落：")
        print("-" * 50)
        for i, paragraph in enumerate(paragraphs, 1):
            print(f"段落 {i}:")
            print(paragraph)
            print("-" * 50)
        
        # 方法 2: 回傳合併的字串
        article_text = fetch_cnn_paragraphs_as_string(url)
        print("\n合併後的文章內容：")
        print("=" * 50)
        print(article_text)
        
    except Exception as e:
        print("錯誤：", e)