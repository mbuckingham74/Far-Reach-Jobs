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

        # Look for job rows - skip header and navigation rows
        job_rows = job_table.find_all('tr')

        for row in job_rows:
            # Skip header row (has th), qbe row, and navigation row
            if (row.find('th') or
                row.get('id') == 'JobSearchTable:qbeRow' or
                'navigationRow' in row.get('class', [])):
                continue

            cells = row.find_all('td')
            if len(cells) < 8:
                continue

            try:
                # Extract job information from table cells
                # Columns: Select, Name, Job Title, Organization, Job Category, Location, Date Posted, Employment Type, Apply

                # Job title is in the 3rd column (index 2)
                title_cell = cells[2]
                title_link = title_cell.find('a')
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                if not title:
                    continue

                # Extract the job URL from the link
                job_href = title_link.get('href', '')
                if job_href.startswith('javascript:') or not job_href:
                    job_url = url
                else:
                    job_url = urljoin(self.base_url, job_href)

                # Organization name is in the 4th column (index 3)
                organization_cell = cells[3]
                organization = organization_cell.get_text(strip=True) or "Tanana Chiefs Conference"

                # Job category is in the 5th column (index 4)
                job_type_cell = cells[4]
                job_type = job_type_cell.get_text(strip=True) or None

                # Location is in the 6th column (index 5)
                location_cell = cells[5]
                location = location_cell.get_text(strip=True) or None

                # Date posted is in the 7th column (index 6)
                date_cell = cells[6]
                date_posted = date_cell.get_text(strip=True) or None

                # Employment type is in the 8th column (index 7)
                employment_type_cell = cells[7] if len(cells) > 7 else None
                employment_type = employment_type_cell.get_text(strip=True) if employment_type_cell else None

                job = ScrapedJob(
                    external_id=self.generate_external_id(job_url + title),
                    title=title,
                    url=job_url,
                    organization=organization,
                    location=location,
                    state="AK",
                    description=f"Posted: {date_posted}" if date_posted else None,
                    job_type=f"{job_type} - {employment_type}" if job_type and employment_type else job_type or employment_type,
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
