import requests
from bs4 import BeautifulSoup
import json
import time
import csv
from datetime import datetime, timedelta
import logging
from urllib.parse import urljoin, urlparse
import re
import os

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CNNWorldScraper:
    def __init__(self, today_only=True, output_dir='cnn_news'):
        self.base_url = "https://edition.cnn.com"
        self.world_url = "https://edition.cnn.com/world"
        self.today_only = today_only
        self.today_date = datetime.now().date()
        self.output_dir = output_dir
        
        # 創建輸出目錄
        self.create_output_directory()
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def create_output_directory(self):
        """創建輸出目錄"""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                logger.info(f"已創建輸出目錄: {self.output_dir}")
            else:
                logger.info(f"使用現有輸出目錄: {self.output_dir}")
        except Exception as e:
            logger.error(f"無法創建輸出目錄: {e}")
            # 如果無法創建目錄，使用當前目錄
            self.output_dir = '.'
        
    def get_page(self, url, retries=3):
        """獲取網頁內容"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"嘗試 {attempt + 1} 失敗: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                else:
                    logger.error(f"無法獲取頁面: {url}")
                    return None
    
    def extract_article_urls(self, soup):
        """從頁面中提取文章URL"""
        article_urls = set()
        
        # 尋找文章連結的各種可能選擇器
        selectors = [
            'a[href*="/world/"]',
            'a[href*="/2024/"]',
            'a[href*="/2025/"]',
            '.card a',
            '.container__link',
            '.cd__headline-text',
            'a.cd__headline-text',
            '[data-module-name="card"] a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    # 轉換為絕對URL
                    full_url = urljoin(self.base_url, href)
                    
                    # 過濾有效的文章URL
                    if self.is_valid_article_url(full_url):
                        article_urls.add(full_url)
        
        return list(article_urls)
    
    def is_today_article(self, url):
        """檢查文章是否為今天發布"""
        if not self.today_only:
            return True
            
        # 從URL中提取日期
        today_str = self.today_date.strftime('%Y/%m/%d')
        today_patterns = [
            self.today_date.strftime('%Y/%m/%d'),
            self.today_date.strftime('%Y/%m/%d').replace('/', '-'),
            self.today_date.strftime('%Y%m%d')
        ]
        
        for pattern in today_patterns:
            if pattern in url:
                return True
        
        return False
    
    def parse_article_date(self, date_text):
        """解析文章日期文本"""
        if not date_text:
            return None
            
        # 清理日期文本
        date_text = date_text.strip().lower()
        
        # 檢查是否包含"today"或今天相關詞彙
        today_keywords = ['today', 'just now', 'minutes ago', 'hours ago', 'hour ago', 'minute ago']
        for keyword in today_keywords:
            if keyword in date_text:
                return self.today_date
        
        # 嘗試解析各種日期格式
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
            r'(\w+)\s+(\d{1,2}),\s+(\d{4})', # Month DD, YYYY
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # 根據不同格式解析
                        if pattern == date_patterns[0]:  # MM/DD/YYYY
                            month, day, year = groups
                            return datetime(int(year), int(month), int(day)).date()
                        elif pattern == date_patterns[1]:  # YYYY-MM-DD
                            year, month, day = groups
                            return datetime(int(year), int(month), int(day)).date()
                        elif pattern == date_patterns[2]:  # DD-MM-YYYY
                            day, month, year = groups
                            return datetime(int(year), int(month), int(day)).date()
                        elif pattern == date_patterns[3]:  # Month DD, YYYY
                            month_name, day, year = groups
                            month_dict = {
                                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                                'september': 9, 'october': 10, 'november': 11, 'december': 12
                            }
                            month = month_dict.get(month_name.lower())
                            if month:
                                return datetime(int(year), month, int(day)).date()
                        elif pattern == date_patterns[4]:  # DD Month YYYY
                            day, month_name, year = groups
                            month_dict = {
                                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                                'september': 9, 'october': 10, 'november': 11, 'december': 12
                            }
                            month = month_dict.get(month_name.lower())
                            if month:
                                return datetime(int(year), month, int(day)).date()
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def is_valid_article_url(self, url):
        """檢查是否為有效的文章URL"""
        parsed = urlparse(url)
        
        # 基本檢查
        if not parsed.scheme or not parsed.netloc:
            return False
            
        # 檢查是否為CNN域名
        if 'cnn.com' not in parsed.netloc:
            return False
            
        # 過濾不需要的路徑
        excluded_paths = [
            '/videos/', '/video/', '/gallery/', '/galleries/',
            '/live-news/', '/profiles/', '/about/', '/contact/',
            '/search/', '/newsletters/', '/audio/', '/podcasts/'
        ]
        
        for excluded in excluded_paths:
            if excluded in parsed.path:
                return False
        
        # 檢查是否包含年份（通常文章URL包含年份）
        if any(year in parsed.path for year in ['2024', '2025']):
            # 如果只要今天的新聞，進一步檢查日期
            if self.today_only:
                return self.is_today_article(url)
            return True
            
        # 檢查是否為world相關文章
        if '/world/' in parsed.path:
            if self.today_only:
                return self.is_today_article(url)
            return True
            
        return False
    
    def is_today_by_content(self, article_data):
        """通過文章內容判斷是否為今天的新聞"""
        if not self.today_only:
            return True
            
        # 檢查發布日期
        if article_data.get('publish_date'):
            parsed_date = self.parse_article_date(article_data['publish_date'])
            if parsed_date:
                return parsed_date == self.today_date
        
        # 檢查URL中的日期
        return self.is_today_article(article_data.get('url', ''))
    
        """檢查是否為有效的文章URL"""
        parsed = urlparse(url)
        
        # 基本檢查
        if not parsed.scheme or not parsed.netloc:
            return False
            
        # 檢查是否為CNN域名
        if 'cnn.com' not in parsed.netloc:
            return False
            
        # 過濾不需要的路徑
        excluded_paths = [
            '/videos/', '/video/', '/gallery/', '/galleries/',
            '/live-news/', '/profiles/', '/about/', '/contact/',
            '/search/', '/newsletters/', '/audio/', '/podcasts/'
        ]
        
        for excluded in excluded_paths:
            if excluded in parsed.path:
                return False
        
        # 檢查是否包含年份（通常文章URL包含年份）
        if any(year in parsed.path for year in ['2024', '2025']):
            return True
            
        # 檢查是否為world相關文章
        if '/world/' in parsed.path:
            return True
            
        return False
    
    def extract_article_content(self, url):
        """提取文章內容"""
        response = self.get_page(url)
        if not response:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 嘗試提取文章信息
        article_data = {
            'url': url,
            'title': '',
            'content': '',
            'author': '',
            'publish_date': '',
            'tags': [],
            'scraped_at': datetime.now().isoformat()
        }
        
        # 提取標題
        title_selectors = [
            'h1.headline__text',
            'h1[data-editable="headline"]',
            'h1.pg-headline',
            'h1',
            '.headline__text'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                article_data['title'] = title_elem.get_text(strip=True)
                break
        
        # 提取內容
        content_selectors = [
            '.zn-body__paragraph',
            '.paragraph',
            '.zn-body__paragraph p',
            '[data-component-name="paragraph"] p',
            '.BasicArticle__paragraph'
        ]
        
        content_parts = []
        for selector in content_selectors:
            paragraphs = soup.select(selector)
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # 過濾太短的段落
                    content_parts.append(text)
        
        article_data['content'] = '\n\n'.join(content_parts)
        
        # 提取作者
        author_selectors = [
            '.byline__name',
            '.metadata__byline',
            '[data-module="ArticleByline"] .byline__name',
            '.byline'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                article_data['author'] = author_elem.get_text(strip=True)
                break
        
        # 提取發布日期
        date_selectors = [
            '.timestamp',
            '.metadata__date',
            '[data-module="ArticleByline"] .timestamp',
            'time',
            '.byline__timestamp',
            '.article-meta time'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                # 嘗試從多個屬性獲取日期
                date_text = (date_elem.get('datetime') or 
                           date_elem.get('data-timestamp') or 
                           date_elem.get_text(strip=True))
                article_data['publish_date'] = date_text
                break
        
        # 提取標籤
        tag_selectors = [
            '.metadata__section',
            '.breadcrumb__link',
            '.zn-tag'
        ]
        
        tags = []
        for selector in tag_selectors:
            tag_elems = soup.select(selector)
            for tag_elem in tag_elems:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text and tag_text not in tags:
                    tags.append(tag_text)
        
        article_data['tags'] = tags
        
        return article_data
    
    def scrape_world_news(self, max_articles=20):
        """爬取CNN世界新聞"""
        logger.info("開始爬取CNN世界新聞...")
        
        # 獲取世界新聞頁面
        response = self.get_page(self.world_url)
        if not response:
            logger.error("無法獲取世界新聞頁面")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取文章URL
        article_urls = self.extract_article_urls(soup)
        logger.info(f"找到 {len(article_urls)} 個文章URL")
        
        # 限制文章數量
        if max_articles:
            article_urls = article_urls[:max_articles]
        
        # 爬取文章內容
        articles = []
        today_articles = []
        
        for i, url in enumerate(article_urls, 1):
            logger.info(f"正在爬取文章 {i}/{len(article_urls)}: {url}")
            
            article_data = self.extract_article_content(url)
            if article_data and article_data['title']:
                # 如果啟用了今天限制，檢查是否為今天的新聞
                if self.today_only:
                    if self.is_today_by_content(article_data):
                        today_articles.append(article_data)
                        logger.info(f"✓ 今天的新聞: {article_data['title'][:50]}...")
                    else:
                        logger.info(f"✗ 非今天的新聞，跳過: {article_data['title'][:50]}...")
                else:
                    articles.append(article_data)
                    logger.info(f"成功爬取: {article_data['title'][:50]}...")
            else:
                logger.warning(f"無法爬取文章內容: {url}")
            
            # 添加延遲以避免被封鎖
            time.sleep(1)
        
        # 返回相應的結果
        final_articles = today_articles if self.today_only else articles
        
        if self.today_only:
            logger.info(f"爬取完成，共獲得 {len(final_articles)} 篇今天的文章")
        else:
            logger.info(f"爬取完成，共獲得 {len(final_articles)} 篇文章")
            
        return final_articles
    
    def save_to_json(self, articles, filename='cnn_world_news.json'):
        """保存為JSON文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存到 {filename}")
    
    def save_to_csv(self, articles, filename='cnn_world_news.csv'):
        """保存為CSV文件"""
        if not articles:
            logger.warning("沒有數據可保存")
            return
        
        fieldnames = ['title', 'author', 'publish_date', 'url', 'content', 'tags', 'scraped_at']
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for article in articles:
                # 處理標籤列表
                article_copy = article.copy()
                article_copy['tags'] = ', '.join(article['tags']) if article['tags'] else ''
                writer.writerow(article_copy)
        
        logger.info(f"已保存到 {filename}")
    
    def print_summary(self, articles):
        """打印爬取結果摘要"""
        if not articles:
            print("沒有爬取到文章")
            return
        
        print(f"\n=== 爬取結果摘要 ===")
        if self.today_only:
            print(f"總共爬取了 {len(articles)} 篇今天的文章")
            print(f"篩選日期: {self.today_date.strftime('%Y-%m-%d')}")
        else:
            print(f"總共爬取了 {len(articles)} 篇文章")
        print(f"爬取時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n=== 前5篇文章標題 ===")
        for i, article in enumerate(articles[:5], 1):
            print(f"{i}. {article['title']}")
            print(f"   作者: {article['author'] or '未知'}")
            print(f"   發布時間: {article['publish_date'] or '未知'}")
            print(f"   URL: {article['url']}")
            print()

def main():
    today_only = True
    max_articles = 20

    # 建立爬蟲實例
    scraper = CNNWorldScraper(today_only=today_only)

    if today_only:
        print(f"開始爬取今天({scraper.today_date.strftime('%Y-%m-%d')})的CNN世界新聞，最多 {max_articles} 篇...")
    else:
        print(f"開始爬取CNN世界新聞，最多 {max_articles} 篇...")

    # 爬取文章
    articles = scraper.scrape_world_news(max_articles=max_articles)

    # 存檔並列印摘要
    if articles:
        # 依日期加上檔名後綴
        date_str = scraper.today_date.strftime('%Y%m%d') if today_only else ''
        json_filename = f'cnn_world_news_{date_str}.json' if date_str else 'cnn_world_news.json'
        csv_filename  = f'cnn_world_news_{date_str}.csv'  if date_str else 'cnn_world_news.csv'

        scraper.save_to_json(articles, json_filename)
        scraper.save_to_csv(articles, csv_filename)
        scraper.print_summary(articles)
    else:
        msg = "今天沒有找到符合條件的世界新聞文章" if today_only else "未能爬取到任何文章"
        print(msg)

if __name__ == "__main__":
    main()