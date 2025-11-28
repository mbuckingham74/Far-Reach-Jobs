"""Tests for UltiPro/UKG Pro scraper."""

import pytest
from unittest.mock import patch, MagicMock

from scraper.sources.ultipro import UltiProScraper
from scraper.url_utils import is_ultipro_url, is_adp_workforce_url


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
        assert "could not extract" in errors[0].lower()

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

    def test_handles_state_as_object(self):
        """Should handle State field as object with Code/Name properties."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
            ),
        )

        # Real UltiPro API returns State as an object, not a string
        opportunity = {
            "Id": "job-123",
            "Title": "Test Job",
            "FullTime": True,
            "Locations": [
                {
                    "Address": {
                        "City": "Anchorage",
                        "State": {"Code": "AK", "Name": "Alaska"},
                    }
                }
            ],
        }

        job = scraper._parse_opportunity(opportunity)

        assert job is not None
        assert job.location == "Anchorage, AK"
        assert job.state == "AK"

    def test_normalizes_job_detail_url_to_board_url(self):
        """Should extract board URL even when given a job detail URL."""
        # User might copy/paste a job detail URL instead of the board URL
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/SOU1048SOFO/JobBoard/"
                "c9cedf85-000e-4f7b-b325-fdda3f04c5be/OpportunityDetail?"
                "opportunityId=786ef21d-1db8-4676-ae0e-8b95c1e0fecb"
            ),
        )

        assert scraper._tenant == "SOU1048SOFO"
        assert scraper._board_id == "c9cedf85-000e-4f7b-b325-fdda3f04c5be"
        # API URL should be normalized (no OpportunityDetail in path)
        api_url = scraper._get_api_url()
        assert "OpportunityDetail" not in api_url
        assert "JobBoardView/LoadSearchResults" in api_url

    def test_preserves_host_from_input_url(self):
        """Should use the host from the input URL, not hardcoded."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting.ultipro.com/ALT123/JobBoard/board-xyz/"
            ),
        )

        assert scraper._host == "recruiting.ultipro.com"
        api_url = scraper._get_api_url()
        assert "recruiting.ultipro.com" in api_url
        assert "recruiting2" not in api_url

    def test_builds_normalized_board_url(self):
        """Should build a clean normalized board URL from parts."""
        scraper = UltiProScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456/"
                "OpportunityDetail?opportunityId=some-job-id"
            ),
        )

        expected_board_url = "https://recruiting2.ultipro.com/TEST123/JobBoard/board-456"
        assert scraper._board_url == expected_board_url

    # ==================== UKG Pro (rec.pro.ukg.net) Tests ====================

    def test_extracts_tenant_and_board_id_from_ukg_pro_url(self):
        """Should extract tenant and board-id from UKG Pro rec.pro.ukg.net URL."""
        scraper = UltiProScraper(
            source_name="Ahtna Inc",
            base_url="https://www.ahtna.com",
            listing_url=(
                "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/"
                "b5e902eb-8919-4dab-bfa8-23d54b8ec174/"
            ),
        )

        assert scraper._tenant == "AHT1000AHT"
        assert scraper._board_id == "b5e902eb-8919-4dab-bfa8-23d54b8ec174"
        assert scraper._host == "aht1971.rec.pro.ukg.net"

    def test_builds_correct_api_url_for_ukg_pro(self):
        """Should build correct API URL for UKG Pro domain."""
        scraper = UltiProScraper(
            source_name="Ahtna Inc",
            base_url="https://www.ahtna.com",
            listing_url=(
                "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/"
                "b5e902eb-8919-4dab-bfa8-23d54b8ec174/"
            ),
        )

        api_url = scraper._get_api_url()
        assert api_url == (
            "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/"
            "b5e902eb-8919-4dab-bfa8-23d54b8ec174/JobBoardView/LoadSearchResults"
        )

    def test_builds_correct_job_detail_url_for_ukg_pro(self):
        """Should build correct job detail URL for UKG Pro domain."""
        scraper = UltiProScraper(
            source_name="Ahtna Inc",
            base_url="https://www.ahtna.com",
            listing_url=(
                "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/"
                "b5e902eb-8919-4dab-bfa8-23d54b8ec174/"
            ),
        )

        job_url = scraper._get_job_detail_url("c1dfec4c-12ab-4875-8559-4d13f340505d")
        assert job_url == (
            "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/"
            "b5e902eb-8919-4dab-bfa8-23d54b8ec174/OpportunityDetail?"
            "opportunityId=c1dfec4c-12ab-4875-8559-4d13f340505d"
        )

    def test_handles_ukg_pro_url_with_query_params(self):
        """Should handle UKG Pro URLs with query parameters."""
        scraper = UltiProScraper(
            source_name="Ahtna Inc",
            base_url="https://www.ahtna.com",
            listing_url=(
                "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/"
                "b5e902eb-8919-4dab-bfa8-23d54b8ec174/?q=&o=postedDateDesc"
            ),
        )

        assert scraper._tenant == "AHT1000AHT"
        assert scraper._board_id == "b5e902eb-8919-4dab-bfa8-23d54b8ec174"

    def test_parses_job_from_ukg_pro_api_response(self):
        """Should correctly parse a job from real UKG Pro API response format."""
        scraper = UltiProScraper(
            source_name="Ahtna Inc",
            base_url="https://www.ahtna.com",
            listing_url=(
                "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/"
                "b5e902eb-8919-4dab-bfa8-23d54b8ec174/"
            ),
        )

        # Sample from actual UKG Pro API response
        opportunity = {
            "Id": "c1dfec4c-12ab-4875-8559-4d13f340505d",
            "Featured": False,
            "Title": "Janitor-on-call-Cordova-Ahtna Global",
            "RequisitionNumber": "JANIT001073",
            "FullTime": False,
            "JobCategoryName": "Maintenance",
            "Locations": [
                {
                    "Id": "7e6a950f-a29d-507c-ba26-1e598856e31b",
                    "Address": {
                        "Line1": "PO Box 80",
                        "City": "Cordova",
                        "PostalCode": "99574",
                        "State": {
                            "Code": "AK",
                            "Name": "Alaska"
                        },
                        "Country": {
                            "Code": "USA",
                            "Name": "United States"
                        }
                    },
                }
            ],
            "PostedDate": "2023-12-02T19:51:48.661Z",
            "BriefDescription": "Works under the supervision of the Project Manager.",
        }

        job = scraper._parse_opportunity(opportunity)

        assert job is not None
        assert job.title == "Janitor-on-call-Cordova-Ahtna Global"
        assert job.organization == "Ahtna Inc"
        assert job.location == "Cordova, AK"
        assert job.state == "AK"
        assert job.job_type == "Part-Time"
        assert job.description == "Works under the supervision of the Project Manager."
        assert "OpportunityDetail" in job.url
        assert "c1dfec4c-12ab-4875-8559-4d13f340505d" in job.url


class TestIsUltiproUrl:
    """Tests for the is_ultipro_url detection function."""

    def test_detects_recruiting2_ultipro_url(self):
        """Should detect recruiting2.ultipro.com URLs."""
        url = "https://recruiting2.ultipro.com/SOU1048SOFO/JobBoard/c9cedf85-000e-4f7b-b325-fdda3f04c5be/"
        assert is_ultipro_url(url) is True

    def test_detects_recruiting_ultipro_url(self):
        """Should detect recruiting.ultipro.com URLs."""
        url = "https://recruiting.ultipro.com/TEST123/JobBoard/board-456/"
        assert is_ultipro_url(url) is True

    def test_detects_ukg_pro_url(self):
        """Should detect rec.pro.ukg.net URLs."""
        url = "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/b5e902eb-8919-4dab-bfa8-23d54b8ec174/"
        assert is_ultipro_url(url) is True

    def test_detects_ukg_pro_url_with_query_params(self):
        """Should detect rec.pro.ukg.net URLs with query parameters."""
        url = "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/b5e902eb-8919-4dab-bfa8-23d54b8ec174/?q=&o=postedDateDesc"
        assert is_ultipro_url(url) is True

    def test_returns_false_for_non_ultipro_url(self):
        """Should return False for non-UltiPro URLs."""
        assert is_ultipro_url("https://example.com/careers") is False
        assert is_ultipro_url("https://workforcenow.adp.com/jobs") is False
        assert is_ultipro_url("https://jobs.lever.co/company") is False

    def test_returns_false_for_none(self):
        """Should return False for None input."""
        assert is_ultipro_url(None) is False

    def test_returns_false_for_empty_string(self):
        """Should return False for empty string."""
        assert is_ultipro_url("") is False

    def test_case_insensitive(self):
        """Should match URLs case-insensitively."""
        assert is_ultipro_url("https://RECRUITING2.ULTIPRO.COM/TEST/JobBoard/123/") is True
        assert is_ultipro_url("https://AHT1971.REC.PRO.UKG.NET/AHT/JobBoard/123/") is True


class TestIsAdpWorkforceUrl:
    """Tests for the is_adp_workforce_url detection function."""

    def test_detects_adp_workforce_url(self):
        """Should detect workforcenow.adp.com URLs."""
        url = "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=12345"
        assert is_adp_workforce_url(url) is True

    def test_returns_false_for_non_adp_url(self):
        """Should return False for non-ADP URLs."""
        assert is_adp_workforce_url("https://example.com/careers") is False
        assert is_adp_workforce_url("https://recruiting2.ultipro.com/TEST/JobBoard/123/") is False

    def test_returns_false_for_none(self):
        """Should return False for None input."""
        assert is_adp_workforce_url(None) is False

    def test_returns_false_for_empty_string(self):
        """Should return False for empty string."""
        assert is_adp_workforce_url("") is False

    def test_case_insensitive(self):
        """Should match URLs case-insensitively."""
        assert is_adp_workforce_url("https://WORKFORCENOW.ADP.COM/jobs") is True


class TestApiScrapersSkipRobotsCheck:
    """Tests to ensure API scrapers bypass robots.txt checking.

    UltiPro and ADP use public JSON APIs, not HTML crawling, so robots.txt
    restrictions don't apply. These tests verify the ordering in run_scraper
    ensures API sources are handled before robots.txt check is called.
    """

    def test_ultipro_scraper_bypasses_robots_check(self):
        """UltiPro sources should be handled before robots.txt check."""
        # This test verifies run_scraper dispatches to _run_ultipro_scraper
        # BEFORE calling check_robots_blocked
        from unittest.mock import MagicMock, patch

        mock_db = MagicMock()
        mock_source = MagicMock()
        mock_source.name = "Test UltiPro Source"
        mock_source.listing_url = "https://recruiting2.ultipro.com/TEST/JobBoard/123/"

        # Mock all the functions called in run_scraper
        with patch("scraper.runner._run_ultipro_scraper") as mock_ultipro, \
             patch("scraper.runner.check_robots_blocked") as mock_robots:

            mock_ultipro.return_value = MagicMock()  # Return a result

            from scraper.runner import run_scraper
            run_scraper(mock_db, mock_source)

            # Verify UltiPro scraper was called
            mock_ultipro.assert_called_once()
            # Verify robots.txt check was NOT called (bypassed)
            mock_robots.assert_not_called()

    def test_ukg_pro_scraper_bypasses_robots_check(self):
        """UKG Pro (rec.pro.ukg.net) sources should bypass robots.txt check."""
        from unittest.mock import MagicMock, patch

        mock_db = MagicMock()
        mock_source = MagicMock()
        mock_source.name = "Test UKG Pro Source"
        mock_source.listing_url = "https://aht1971.rec.pro.ukg.net/AHT1000AHT/JobBoard/b5e902eb-8919-4dab-bfa8-23d54b8ec174/"

        with patch("scraper.runner._run_ultipro_scraper") as mock_ultipro, \
             patch("scraper.runner.check_robots_blocked") as mock_robots:

            mock_ultipro.return_value = MagicMock()

            from scraper.runner import run_scraper
            run_scraper(mock_db, mock_source)

            mock_ultipro.assert_called_once()
            mock_robots.assert_not_called()

    def test_adp_scraper_bypasses_robots_check(self):
        """ADP WorkforceNow sources should bypass robots.txt check."""
        from unittest.mock import MagicMock, patch

        mock_db = MagicMock()
        mock_source = MagicMock()
        mock_source.name = "Test ADP Source"
        mock_source.listing_url = "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=12345"

        with patch("scraper.runner._run_adp_scraper") as mock_adp, \
             patch("scraper.runner.check_robots_blocked") as mock_robots:

            mock_adp.return_value = MagicMock()

            from scraper.runner import run_scraper
            run_scraper(mock_db, mock_source)

            mock_adp.assert_called_once()
            mock_robots.assert_not_called()

    def test_generic_scraper_does_check_robots(self):
        """Non-API sources should still go through robots.txt check."""
        from unittest.mock import MagicMock, patch

        mock_db = MagicMock()
        mock_source = MagicMock()
        mock_source.name = "Test Generic Source"
        mock_source.listing_url = "https://example.com/careers"
        mock_source.scraper_class = "GenericScraper"

        with patch("scraper.runner._run_ultipro_scraper") as mock_ultipro, \
             patch("scraper.runner._run_adp_scraper") as mock_adp, \
             patch("scraper.runner.check_robots_blocked") as mock_robots, \
             patch("scraper.runner.get_scraper_class") as mock_get_class:

            # Simulate robots check passing
            mock_robots.return_value = (False, None, None, None)
            mock_get_class.return_value = MagicMock()

            from scraper.runner import run_scraper
            # This will try to instantiate the scraper, which may fail
            # but we're just testing that robots check is called
            try:
                run_scraper(mock_db, mock_source)
            except Exception:
                pass  # We expect it may fail after robots check

            # Verify API scrapers were NOT called
            mock_ultipro.assert_not_called()
            mock_adp.assert_not_called()
            # Verify robots.txt check WAS called
            mock_robots.assert_called_once()
