import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from base_scraper import CentralBankScraper

class BoCScraper(CentralBankScraper):
    def __init__(self):
        super().__init__(bank_name="BoC")

    def get_article_text(self, soup):
        # Remove junk
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # Find content
        content = soup.find('div', class_='post-content')
        if not content:
            return ""
        
        # Get paragraphs
        paras = []
        for p in content.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 30:
                paras.append(text)

        return ' '.join(paras)

    def run(self): 
        url = "https://www.bankofcanada.ca/press/press-releases/"
        
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except Exception as err:
            print(f"Error: {err}")
            return
        
        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('h3', class_='media-heading')
        
        keywords = ["interest rate", "monetary policy", "statement", "policy rate"]
        
        for article in articles:
            link = article.find('a')
            if not link:
                continue
            
            title = link.get_text().strip()
            if not any(k in title.lower() for k in keywords):
                continue
            
            article_url = urljoin(url, link['href'])
            # Skip if already in DB
            try:
                if self.url_exists(article_url):
                    continue
            except Exception:
                pass

            print(f"Scraping: {title}")

            try:
                r = requests.get(article_url, timeout=15)
                r.raise_for_status()
            except Exception as err:
                print(f"Failed to fetch {article_url}: {err}")
                continue
            
            article_soup = BeautifulSoup(r.text, 'html.parser')
            
            # Get date
            date_meta = article_soup.find('meta', attrs={'name': 'publication_date'})
            date = date_meta['content'][:10] if date_meta and date_meta.get('content') else '1970-01-01'
            
            # Get text
            text = self.get_article_text(article_soup)
            
            if len(text) < 200:
                continue
            
            self.save_to_db(date, article_url, text)
        
        print("Done.")

if __name__ == "__main__":
    scraper = BoCScraper()
    try:
        scraper.run()
    finally:
        scraper.close()