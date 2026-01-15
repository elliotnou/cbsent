import os
import re
import io
import json
import requests
import PyPDF2
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from base_scraper import CentralBankScraper

class FedScraper(CentralBankScraper):
    def __init__(self):
        super().__init__(bank_name="Fed")
        self.feed_url = "https://www.federalreserve.gov/json/ne-press.json"
        self.session = requests.Session()

        raw_cutoff = os.getenv('SCRAPER_EARLIEST_DATE', '2021-07-29')
        try:
            self.cutoff = datetime.datetime.strptime(raw_cutoff, '%Y-%m-%d').date()
        except ValueError:
            self.cutoff = datetime.date(2024, 1, 1)

    def get_pdf_text(self, url):
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            with io.BytesIO(resp.content) as f:
                reader = PyPDF2.PdfReader(f)
                return " ".join([page.extract_text() or "" for page in reader.pages]).strip()
        except Exception:
            return None

    def run(self):
        try:
            r = self.session.get(self.feed_url, timeout=15)
            r.raise_for_status()
            releases = json.loads(r.content.decode('utf-8-sig'))
        except Exception as e:
            print(f"Feed error: {e}")
            return

        processed = 0
        for item in releases:
            title = (item.get('t') or item.get('title') or "").strip()
            path = item.get('l', '')
            if not title or not path: continue

            tags = title.lower()

            # Only scrape reports with relevant keywords in title for hawkish/dovish signals
            if not any(k in tags for k in ['statement', 'projections', 'projection']): continue
            if any(noise in tags for noise in ['schedule', 'implementation']): continue

            full_url = urljoin("https://www.federalreserve.gov", path)
            match = re.search(r'(\d{8})', path)
            if not match: continue
                
            raw_d = match.group(1)

            date_str = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:]}"
            if datetime.datetime.strptime(date_str, '%Y-%m-%d').date() < self.cutoff: break

            if self.url_exists(full_url): continue

            print(f"Found: {title} ({date_str})")
            content = None

            if full_url.endswith('.pdf'):
                content = self.get_pdf_text(full_url)
            else:
                try:
                    page = self.session.get(full_url, timeout=15)
                    soup = BeautifulSoup(page.text, 'html.parser')
                    pdf_btn = soup.find('a', href=re.compile(r'\.pdf$', re.I))
                    if pdf_btn:
                        pdf_url = urljoin(full_url, pdf_btn['href'])
                        # Avoid re-downloading if URL already exists
                        if not self.url_exists(pdf_url):
                            content = self.get_pdf_text(pdf_url)
                    else:
                        article = soup.find('div', id='article') or soup.find('div', class_='col-xs-12')
                        if article:
                            content = " ".join([p.get_text() for p in article.find_all('p') if len(p.get_text()) > 30])
                except Exception:
                    continue

            if content and len(content) > 300:
                self.save_to_db(date_str, full_url, f"Type: {title}\n\n{content}")
                processed += 1

        print(f"Done. Processed {processed} new items.")

if __name__ == "__main__":
    scraper = FedScraper()
    try:
        scraper.run()
    finally:
        scraper.close()