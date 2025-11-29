class TananaChiefsScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "Tanana Chiefs Conference (TCC) – Interior villages"

    @property
    def base_url(self) -> str:
        return "https://careers.tananachiefs.org/OA_HTML/OA.jsp?OAFunc=TCC_IRC_ALL_JOBS"

    def get_job_listing_urls(self) -> list[str]:
        return [self.base_url]

    def parse_job_listing_page(self, soup, url):
        jobs = []

        # The main job table is identified by ID "JobSearchTable:Content"
        job_table = soup.find('table', id='JobSearchTable:Content')
        if not job_table:
            return jobs

        # Look for job rows
        job_rows = job_table.find_all('tr')

        for row in job_rows:
            cells = row.find_all('td')
            # Need at least 8 cells for a valid job row
            if len(cells) < 8:
                continue

            try:
                # Table structure (0-indexed):
                # 0: Checkbox (select)
                # 1: Name/ID with link to job details
                # 2: Job Title (text only)
                # 3: Organization Name
                # 4: Professional Area (Job Category)
                # 5: Location
                # 6: Date Posted
                # 7: Employment Type
                # 8: Apply button (optional)

                # Get job link from cell 1 (Name column)
                name_cell = cells[1]
                job_link = name_cell.find('a', href=True)
                if not job_link or job_link.get('href') == '#':
                    # Try finding the other link
                    links = name_cell.find_all('a', href=True)
                    job_link = None
                    for link in links:
                        href = link.get('href', '')
                        if href and href != '#' and 'IRC_VIS_VAC_DISPLAY' in href:
                            job_link = link
                            break

                if not job_link:
                    continue

                # Get job title from cell 2
                title_cell = cells[2]
                title = title_cell.get_text(strip=True)
                if not title:
                    continue

                # Build the job URL
                job_href = job_link.get('href', '')
                if job_href.startswith('/'):
                    job_url = 'https://careers.tananachiefs.org' + job_href
                elif job_href.startswith('OA.jsp'):
                    job_url = 'https://careers.tananachiefs.org/OA_HTML/' + job_href
                else:
                    job_url = urljoin(self.base_url, job_href)

                # Organization name is in cell 3
                organization = cells[3].get_text(strip=True) or "Tanana Chiefs Conference"

                # Job category is in cell 4
                job_category = cells[4].get_text(strip=True) or None

                # Location is in cell 5
                location = cells[5].get_text(strip=True) or None

                # Date posted is in cell 6
                date_posted = cells[6].get_text(strip=True) or None

                # Employment type is in cell 7
                employment_type = cells[7].get_text(strip=True) if len(cells) > 7 else None

                job = ScrapedJob(
                    external_id=self.generate_external_id(job_url),
                    title=title,
                    url=job_url,
                    organization=organization,
                    location=location,
                    state="AK",
                    description=f"Posted: {date_posted}" if date_posted else None,
                    job_type=f"{job_category} - {employment_type}" if job_category and employment_type else job_category or employment_type,
                    salary_info=None
                )

                jobs.append(job)

            except Exception:
                continue

        return jobs

    def run(self):
        """Override run to select date filter and click Search button before scraping."""
        jobs = []
        errors = []

        # Fetch page with:
        # 1. Select "All Open Reqs" from DatePosted2 dropdown
        # 2. Click Search button
        soup = self.fetch_page(
            self.base_url,
            wait_for='table',
            select_actions=[
                {"selector": "select#DatePosted2", "value": {"label": "All Open Reqs"}}
            ],
            click_selector='button#Go',
            click_wait_for='table tr td a'
        )

        if soup is None:
            errors.append(f"Failed to fetch {self.base_url}")
            return jobs, errors

        try:
            page_jobs = self.parse_job_listing_page(soup, self.base_url)
            jobs.extend(page_jobs)
        except Exception as e:
            errors.append(f"Error parsing {self.base_url}: {e}")

        return jobs, errors
