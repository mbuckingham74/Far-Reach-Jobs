# Scraper source implementations
# Each scraper should be registered using @register_scraper decorator
# Example:
#
# from scraper import BaseScraper, ScrapedJob, register_scraper
#
# @register_scraper
# class MyOrgScraper(BaseScraper):
#     @property
#     def source_name(self) -> str:
#         return "My Organization"
#
#     @property
#     def base_url(self) -> str:
#         return "https://example.com"
#
#     def get_job_listing_urls(self) -> list[str]:
#         return ["https://example.com/jobs"]
#
#     def parse_job_listing_page(self, soup, url) -> list[ScrapedJob]:
#         jobs = []
#         # Parse job listings from soup
#         return jobs

# Import all scrapers here so they get registered
# from scraper.sources.example_scraper import ExampleScraper
