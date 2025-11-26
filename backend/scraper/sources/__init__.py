"""
Scraper source implementations.

IMPORTANT: Each scraper must be:
1. Decorated with @register_scraper
2. Imported in this file for registration to occur

Example scraper:

    # In scraper/sources/example_org.py
    from scraper import BaseScraper, ScrapedJob, register_scraper

    @register_scraper
    class ExampleOrgScraper(BaseScraper):
        @property
        def source_name(self) -> str:
            return "Example Organization"

        @property
        def base_url(self) -> str:
            return "https://example.org"

        def get_job_listing_urls(self) -> list[str]:
            return ["https://example.org/jobs"]

        def parse_job_listing_page(self, soup, url) -> list[ScrapedJob]:
            jobs = []
            for item in soup.select(".job-posting"):
                jobs.append(ScrapedJob(
                    external_id=self.generate_external_id(item.select_one("a")["href"]),
                    title=item.select_one(".title").get_text(strip=True),
                    url=item.select_one("a")["href"],
                    organization=item.select_one(".org").get_text(strip=True),
                    location=item.select_one(".location").get_text(strip=True),
                ))
            return jobs

Then import it here:

    from scraper.sources.example_org import ExampleOrgScraper

And add a ScrapeSource record to the database:

    INSERT INTO scrape_sources (name, base_url, scraper_class, is_active)
    VALUES ('Example Organization', 'https://example.org', 'ExampleOrgScraper', 1);
"""

# Import all scrapers here so they get registered on module load
from scraper.sources.generic import GenericScraper

# Custom scrapers can be added below:
# from scraper.sources.example_org import ExampleOrgScraper
