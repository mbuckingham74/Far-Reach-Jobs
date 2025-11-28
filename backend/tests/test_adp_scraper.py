"""Tests for ADP WorkforceNow scraper."""

import pytest
from unittest.mock import patch, MagicMock

from scraper.sources.adp_workforce import ADPWorkforceScraper


class TestADPWorkforceScraper:
    """Tests for the ADP WorkforceNow API scraper."""

    def test_extracts_cid_and_ccid_from_url(self):
        """Should extract cid and ccId parameters from listing URL."""
        scraper = ADPWorkforceScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/"
                "recruitment.html?cid=c3cf205d-9677-4dfd-ab98-87a0f91551f4"
                "&ccId=19000101_000001&lang=en_US"
            ),
        )

        assert scraper._cid == "c3cf205d-9677-4dfd-ab98-87a0f91551f4"
        assert scraper._cc_id == "19000101_000001"

    def test_builds_correct_api_url(self):
        """Should build the correct API URL from parameters."""
        scraper = ADPWorkforceScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url=(
                "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/"
                "recruitment.html?cid=test-cid&ccId=test-ccid&lang=en_US"
            ),
        )

        api_url = scraper._get_api_url()
        assert "job-requisitions" in api_url
        assert "cid=test-cid" in api_url
        assert "ccId=test-ccid" in api_url

    def test_parses_job_from_api_response(self):
        """Should correctly parse a job requisition from API response."""
        scraper = ADPWorkforceScraper(
            source_name="Bristol Bay Area Health Corporation (BBAHC)",
            base_url="https://www.bbahc.org",
            listing_url=(
                "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/"
                "recruitment.html?cid=c3cf205d-9677-4dfd-ab98-87a0f91551f4"
                "&ccId=19000101_000001&lang=en_US"
            ),
        )

        # Sample requisition from actual API response
        requisition = {
            "itemID": "9201361300322_1",
            "requisitionTitle": "Registered Nurse",
            "workLevelCode": {"shortName": "Full-Time"},
            "requisitionLocations": [
                {
                    "nameCode": {"shortName": " Dillingham, AK, US"},
                    "address": {
                        "cityName": "Dillingham",
                        "countrySubdivisionLevel1": {"codeValue": "AK"},
                        "postalCode": "99576",
                    },
                }
            ],
            "customFieldGroup": {
                "stringFields": [
                    {"stringValue": "558460", "nameCode": {"codeValue": "ExternalJobID"}},
                ]
            },
        }

        job = scraper._parse_requisition(requisition)

        assert job is not None
        assert job.title == "Registered Nurse"
        assert job.organization == "Bristol Bay Area Health Corporation (BBAHC)"
        assert job.state == "AK"
        assert job.job_type == "Full-Time"
        assert "Dillingham" in job.location
        assert "jobId=9201361300322_1" in job.url

    def test_run_fetches_from_api(self):
        """Should fetch jobs from the ADP API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "jobRequisitions": [
                {
                    "itemID": "123",
                    "requisitionTitle": "Test Job",
                    "workLevelCode": {"shortName": "Full-Time"},
                    "requisitionLocations": [
                        {
                            "nameCode": {"shortName": "Anchorage, AK"},
                            "address": {
                                "cityName": "Anchorage",
                                "countrySubdivisionLevel1": {"codeValue": "AK"},
                            },
                        }
                    ],
                    "customFieldGroup": {"stringFields": []},
                },
                {
                    "itemID": "456",
                    "requisitionTitle": "Another Job",
                    "workLevelCode": {"shortName": "Part-Time"},
                    "requisitionLocations": [],
                    "customFieldGroup": {"stringFields": []},
                },
            ]
        }

        with patch("scraper.sources.adp_workforce.httpx.get", return_value=mock_response):
            scraper = ADPWorkforceScraper(
                source_name="Test Org",
                base_url="https://example.org",
                listing_url=(
                    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/"
                    "recruitment.html?cid=test-cid&ccId=test-ccid"
                ),
            )

            jobs, errors = scraper.run()

            assert len(jobs) == 2
            assert len(errors) == 0
            assert jobs[0].title == "Test Job"
            assert jobs[1].title == "Another Job"

    def test_handles_missing_cid(self):
        """Should return error when cid is missing from URL."""
        scraper = ADPWorkforceScraper(
            source_name="Test Org",
            base_url="https://example.org",
            listing_url="https://workforcenow.adp.com/recruitment?ccId=test",  # Missing cid
        )

        jobs, errors = scraper.run()

        assert len(jobs) == 0
        assert len(errors) == 1
        assert "missing cid" in errors[0].lower()

    def test_handles_api_error(self):
        """Should handle API errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = Exception("HTTP 500")

        with patch("scraper.sources.adp_workforce.httpx.get", return_value=mock_response):
            scraper = ADPWorkforceScraper(
                source_name="Test Org",
                base_url="https://example.org",
                listing_url=(
                    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/"
                    "recruitment.html?cid=test-cid&ccId=test-ccid"
                ),
            )

            jobs, errors = scraper.run()

            assert len(jobs) == 0
            assert len(errors) == 1
