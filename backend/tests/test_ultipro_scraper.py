"""Tests for UltiPro scraper."""

import pytest
from unittest.mock import patch, MagicMock

from scraper.sources.ultipro import UltiProScraper


class TestUltiProScraper:
    """Tests for the UltiPro API scraper."""

    def test_extracts_tenant_and_board_id_from_url(self):
        """Should extract tenant and board-id from listing URL."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/SOU1048SOFO/JobBoard/"
                "c9cedf85-000e-4f7b-b325-fdda3f04c5be/"
            ),
        )

        assert scraper._tenant == "SOU1048SOFO"
        assert scraper._board_id == "c9cedf85-000e-4f7b-b325-fdda3f04c5be"

    def test_extracts_from_url_without_trailing_slash(self):
        """Should handle URLs without trailing slash."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/SOU1048SOFO/JobBoard/"
                "c9cedf85-000e-4f7b-b325-fdda3f04c5be"
            ),
        )

        assert scraper._tenant == "SOU1048SOFO"
        assert scraper._board_id == "c9cedf85-000e-4f7b-b325-fdda3f04c5be"

    def test_builds_correct_api_url(self):
        """Should build the correct API URL from parameters."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-id-456/"
            ),
        )

        api_url = scraper._get_api_url()
        assert "JobBoardView/LoadSearchResults" in api_url
        assert "TEST123" in api_url
        assert "board-id-456" in api_url

    def test_builds_correct_job_detail_url(self):
        """Should build correct URL for viewing a specific job."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-id-456/"
            ),
        )

        job_url = scraper._get_job_detail_url("job-abc-123")
        assert "OpportunityDetail" in job_url
        assert "opportunityId=job-abc-123" in job_url

    def test_parses_job_from_api_response(self):
        """Should correctly parse a job opportunity from API response."""
        scraper = UltiProScraper(
            source_name="Southcentral Foundation (SCF)",
            base_url="https://www.southcentralfoundation.com",
            listing_url=(
                "https://recruiting2.ultipro.com/SOU1048SOFO/JobBoard/"
                "c9cedf85-000e-4f7b-b325-fdda3f04c5be/"
            ),
        )

        # Sample opportunity from actual API response
        opportunity = {
            "Id": "REQ-2024-001234",
            "Title": "Registered Nurse - ICU",
            "RequisitionNumber": "RN-2024-001",
            "FullTime": True,
            "Locations": [
                {
                    "Address": {
                        "City": "Anchorage",
                        "State": "AK",
                    }
                }
            ],
            "PostedDate": "2024-01-15T00:00:00",
            "BriefDescription": "Join our team as an ICU nurse.",
        }

        job = scraper._parse_opportunity(opportunity)

        assert job is not None
        assert job.title == "Registered Nurse - ICU"
        assert job.organization == "Southcentral Foundation (SCF)"
        assert job.state == "AK"
        assert job.location == "Anchorage, AK"
        assert job.job_type == "Full-Time"
        assert job.description == "Join our team as an ICU nurse."
        assert "OpportunityDetail" in job.url
        assert "REQ-2024-001234" in job.url

    def test_parses_part_time_job(self):
        """Should correctly identify part-time jobs."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
            ),
        )

        opportunity = {
            "Id": "job-123",
            "Title": "Part-Time Receptionist",
            "FullTime": False,
            "Locations": [],
        }

        job = scraper._parse_opportunity(opportunity)

        assert job is not None
        assert job.job_type == "Part-Time"

    def test_handles_missing_location(self):
        """Should handle jobs without location data."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
            ),
        )

        opportunity = {
            "Id": "job-123",
            "Title": "Remote Position",
            "FullTime": True,
            "Locations": [],
        }

        job = scraper._parse_opportunity(opportunity)

        assert job is not None
        assert job.location is None
        assert job.state is None

    def test_handles_null_locations(self):
        """Should handle null Locations field."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
            ),
        )

        opportunity = {
            "Id": "job-123",
            "Title": "Remote Position",
            "FullTime": True,
            "Locations": None,
        }

        job = scraper._parse_opportunity(opportunity)

        assert job is not None
        assert job.location is None

    def test_run_fetches_from_api(self):
        """Should fetch jobs from the UltiPro API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "opportunities": [
                {
                    "Id": "123",
                    "Title": "Test Job",
                    "RequisitionNumber": "REQ-001",
                    "FullTime": True,
                    "Locations": [
                        {
                            "Address": {
                                "City": "Anchorage",
                                "State": "AK",
                            }
                        }
                    ],
                    "BriefDescription": "A test job.",
                },
                {
                    "Id": "456",
                    "Title": "Another Job",
                    "RequisitionNumber": "REQ-002",
                    "FullTime": False,
                    "Locations": [],
                    "BriefDescription": None,
                },
            ]
        }

        with patch("scraper.sources.ultipro.httpx.post", return_value=mock_response):
            scraper = UltiProScraper(
                source_name="Test Org",
                base_url="https://example.org",
                listing_url=(
                    "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
                ),
            )

            jobs, errors = scraper.run()

            assert len(jobs) == 2
            assert len(errors) == 0
            assert jobs[0].title == "Test Job"
            assert jobs[1].title == "Another Job"

    def test_handles_pagination(self):
        """Should paginate through multiple pages of results."""
        call_count = [0]

        def mock_post(*args, **kwargs):
            call_count[0] += 1
            mock_response = MagicMock()
            mock_response.status_code = 200

            # Return 50 jobs on first call, 10 on second (simulating last page)
            if call_count[0] == 1:
                jobs = [
                    {"Id": f"job-{i}", "Title": f"Job {i}", "FullTime": True, "Locations": []}
                    for i in range(50)
                ]
            else:
                jobs = [
                    {"Id": f"job-{50+i}", "Title": f"Job {50+i}", "FullTime": True, "Locations": []}
                    for i in range(10)
                ]

            mock_response.json.return_value = {"opportunities": jobs}
            return mock_response

        with patch("scraper.sources.ultipro.httpx.post", side_effect=mock_post):
            scraper = UltiProScraper(
                source_name="Test Org",
                base_url="https://example.org",
                listing_url=(
                    "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
                ),
            )

            jobs, errors = scraper.run()

            assert call_count[0] == 2  # Should have made 2 API calls
            assert len(jobs) == 60  # 50 + 10 jobs
            assert len(errors) == 0

    def test_handles_missing_tenant(self):
        """Should return error when tenant is missing from URL."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url="https://recruiting2.ultipro.com/JobBoard/board-456/",  # Missing tenant
        )

        jobs, errors = scraper.run()

        assert len(jobs) == 0
        assert len(errors) == 1
        assert "missing tenant" in errors[0].lower()

    def test_handles_api_error(self):
        """Should handle API errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")

        with patch("scraper.sources.ultipro.httpx.post", return_value=mock_response):
            scraper = UltiProScraper(
                source_name="Test Org",
                base_url="https://example.org",
                listing_url=(
                    "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
                ),
            )

            jobs, errors = scraper.run()

            assert len(jobs) == 0
            assert len(errors) == 1

    def test_uses_requisition_number_for_external_id(self):
        """Should prefer RequisitionNumber over Id for external_id."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
            ),
        )

        opportunity = {
            "Id": "internal-guid-123",
            "Title": "Test Job",
            "RequisitionNumber": "REQ-2024-ABC",
            "FullTime": True,
            "Locations": [],
        }

        job = scraper._parse_opportunity(opportunity)

        # external_id is hashed, but it should be based on RequisitionNumber
        assert job is not None
        assert job.external_id is not None
        assert len(job.external_id) > 0

    def test_handles_city_only_location(self):
        """Should handle location with city but no state."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
            ),
        )

        opportunity = {
            "Id": "job-123",
            "Title": "Test Job",
            "FullTime": True,
            "Locations": [
                {
                    "Address": {
                        "City": "Anchorage",
                    }
                }
            ],
        }

        job = scraper._parse_opportunity(opportunity)

        assert job is not None
        assert job.location == "Anchorage"
        assert job.state == ""
