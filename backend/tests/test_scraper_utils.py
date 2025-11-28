"""Tests for scraper utility functions."""

import pytest

from scraper.utils import (
    normalize_state,
    extract_state_from_location,
    clean_text,
    extract_salary,
    normalize_job_type,
    US_STATES,
    STATE_ABBREVS,
)


class TestNormalizeState:
    """Tests for normalize_state function."""

    def test_full_state_name(self):
        """Should convert full state name to abbreviation."""
        assert normalize_state("Alaska") == "AK"
        assert normalize_state("California") == "CA"
        assert normalize_state("New York") == "NY"
        assert normalize_state("West Virginia") == "WV"

    def test_lowercase_state_name(self):
        """Should handle lowercase state names."""
        assert normalize_state("alaska") == "AK"
        assert normalize_state("new hampshire") == "NH"

    def test_mixed_case_state_name(self):
        """Should handle mixed case state names."""
        assert normalize_state("AlAsKa") == "AK"
        assert normalize_state("NEW YORK") == "NY"

    def test_abbreviation_uppercase(self):
        """Should pass through uppercase abbreviations."""
        assert normalize_state("AK") == "AK"
        assert normalize_state("CA") == "CA"
        assert normalize_state("NY") == "NY"

    def test_abbreviation_lowercase(self):
        """Should normalize lowercase abbreviations to uppercase."""
        assert normalize_state("ak") == "AK"
        assert normalize_state("ny") == "NY"

    def test_whitespace_handling(self):
        """Should trim whitespace."""
        assert normalize_state("  Alaska  ") == "AK"
        assert normalize_state(" AK ") == "AK"

    def test_empty_input(self):
        """Should return None for empty input."""
        assert normalize_state("") is None
        assert normalize_state(None) is None

    def test_invalid_state(self):
        """Should return None for invalid state names."""
        assert normalize_state("Invalid") is None
        assert normalize_state("XX") is None
        assert normalize_state("United States") is None

    def test_all_states_have_mappings(self):
        """All 50 states should have valid mappings."""
        assert len(US_STATES) == 50
        for state_name, abbrev in US_STATES.items():
            assert len(abbrev) == 2
            assert abbrev.isupper()


class TestExtractStateFromLocation:
    """Tests for extract_state_from_location function."""

    def test_city_comma_state(self):
        """Should extract state from 'City, ST' format."""
        assert extract_state_from_location("Anchorage, AK") == "AK"
        assert extract_state_from_location("Los Angeles, CA") == "CA"
        assert extract_state_from_location("New York, NY") == "NY"

    def test_city_state_zip(self):
        """Should extract state from 'City, ST ZIP' format."""
        assert extract_state_from_location("Anchorage, AK 99501") == "AK"
        assert extract_state_from_location("Nome, AK 99762") == "AK"

    def test_state_zip_only(self):
        """Should extract state from 'ST ZIP' format."""
        assert extract_state_from_location("AK 99501") == "AK"

    def test_full_state_name(self):
        """Should extract state from full state name in location."""
        assert extract_state_from_location("Fairbanks, Alaska") == "AK"
        assert extract_state_from_location("Remote - Alaska") == "AK"
        assert extract_state_from_location("New York City, New York") == "NY"

    def test_state_name_case_insensitive(self):
        """Should match state names case-insensitively."""
        assert extract_state_from_location("ALASKA") == "AK"
        assert extract_state_from_location("alaska bush") == "AK"

    def test_no_state_found(self):
        """Should return None when no state found."""
        assert extract_state_from_location("Remote") is None
        assert extract_state_from_location("International") is None
        assert extract_state_from_location("123 Main St") is None

    def test_empty_input(self):
        """Should return None for empty input."""
        assert extract_state_from_location("") is None
        assert extract_state_from_location(None) is None

    def test_invalid_abbreviation(self):
        """Should not match invalid 2-letter codes."""
        assert extract_state_from_location("City, XX") is None
        assert extract_state_from_location("City, ZZ 12345") is None

    def test_substring_matching_caveat(self):
        """Document: substring matching may have false positives.

        The current implementation uses substring matching for full state names,
        which can match words containing state names. This is a known limitation.
        Consider word-boundary anchoring if this causes issues in production.
        """
        # These demonstrate the substring matching behavior
        # "Texasville" contains "texas" -> matches TX
        result = extract_state_from_location("Texasville, USA")
        assert result == "TX"  # Known behavior - may want to fix later

        # Proper match still works correctly
        assert extract_state_from_location("Austin, Texas") == "TX"


class TestCleanText:
    """Tests for clean_text function."""

    def test_multiple_spaces(self):
        """Should collapse multiple spaces to single space."""
        assert clean_text("Hello    World") == "Hello World"
        assert clean_text("Too   many   spaces") == "Too many spaces"

    def test_newlines_and_tabs(self):
        """Should replace newlines and tabs with spaces."""
        assert clean_text("Hello\nWorld") == "Hello World"
        assert clean_text("Hello\tWorld") == "Hello World"
        assert clean_text("Line1\n\n\nLine2") == "Line1 Line2"

    def test_leading_trailing_whitespace(self):
        """Should trim leading and trailing whitespace."""
        assert clean_text("  Hello World  ") == "Hello World"
        assert clean_text("\n\tText\n\t") == "Text"

    def test_mixed_whitespace(self):
        """Should handle mixed whitespace."""
        assert clean_text("  Hello  \n\t  World  ") == "Hello World"

    def test_already_clean(self):
        """Should not modify already clean text."""
        assert clean_text("Clean text") == "Clean text"

    def test_empty_input(self):
        """Should return None for empty input."""
        assert clean_text("") is None
        assert clean_text(None) is None

    def test_whitespace_only(self):
        """Should return empty string for whitespace-only input."""
        result = clean_text("   ")
        assert result == ""


class TestExtractSalary:
    """Tests for extract_salary function."""

    def test_dollar_amount(self):
        """Should extract simple dollar amounts."""
        assert "$50,000" in extract_salary("Salary: $50,000")
        assert "$75,000" in extract_salary("Pay is $75,000 per year")

    def test_salary_range(self):
        """Should extract salary ranges."""
        result = extract_salary("$50,000 - $70,000/year")
        assert "$50,000" in result
        assert "$70,000" in result

    def test_hourly_rate(self):
        """Should extract hourly rates."""
        result = extract_salary("$25/hour")
        assert "$25" in result
        assert "hour" in result.lower()

    def test_per_hour_format(self):
        """Should handle 'per hour' format."""
        result = extract_salary("Pay: $30 per hour")
        assert "$30" in result

    def test_annual_salary(self):
        """Should extract annual salary."""
        result = extract_salary("$80,000/year")
        assert "$80,000" in result

    def test_salary_in_description(self):
        """Should find salary in longer text."""
        text = "Great opportunity! Competitive salary of $65,000 annually with benefits."
        result = extract_salary(text)
        assert result is not None
        assert "65,000" in result

    def test_no_salary_found(self):
        """Should return None when no salary found."""
        assert extract_salary("Great job opportunity!") is None
        assert extract_salary("Benefits included") is None

    def test_empty_input(self):
        """Should return None for empty input."""
        assert extract_salary("") is None
        assert extract_salary(None) is None


class TestNormalizeJobType:
    """Tests for normalize_job_type function."""

    def test_full_time_variations(self):
        """Should normalize full-time variations."""
        assert normalize_job_type("Full-time") == "Full-time"
        assert normalize_job_type("full time") == "Full-time"
        assert normalize_job_type("FULL-TIME") == "Full-time"
        assert normalize_job_type("fulltime") == "Full-time"
        assert normalize_job_type("Full Time Position") == "Full-time"

    def test_part_time_variations(self):
        """Should normalize part-time variations."""
        assert normalize_job_type("Part-time") == "Part-time"
        assert normalize_job_type("part time") == "Part-time"
        assert normalize_job_type("parttime") == "Part-time"
        assert normalize_job_type("PART-TIME") == "Part-time"

    def test_seasonal(self):
        """Should normalize seasonal."""
        assert normalize_job_type("Seasonal") == "Seasonal"
        assert normalize_job_type("seasonal position") == "Seasonal"
        assert normalize_job_type("SEASONAL") == "Seasonal"

    def test_contract(self):
        """Should normalize contract."""
        assert normalize_job_type("Contract") == "Contract"
        assert normalize_job_type("contract position") == "Contract"

    def test_temporary(self):
        """Should normalize temporary."""
        assert normalize_job_type("Temporary") == "Temporary"
        assert normalize_job_type("temp") == "Temporary"
        assert normalize_job_type("Temp Position") == "Temporary"

    def test_internship(self):
        """Should normalize internship."""
        assert normalize_job_type("Internship") == "Internship"
        assert normalize_job_type("intern") == "Internship"
        assert normalize_job_type("Summer Intern") == "Internship"

    def test_unknown_type_cleaned(self):
        """Should clean but preserve unknown types."""
        assert normalize_job_type("On-call") == "On-call"
        assert normalize_job_type("  Volunteer  ") == "Volunteer"

    def test_empty_input(self):
        """Should return None for empty input."""
        assert normalize_job_type("") is None
        assert normalize_job_type(None) is None


class TestStateConstants:
    """Tests for state constant data."""

    def test_state_abbrevs_reverse_lookup(self):
        """STATE_ABBREVS should contain all abbreviations."""
        for abbrev in US_STATES.values():
            assert abbrev in STATE_ABBREVS

    def test_alaska_is_present(self):
        """Alaska should be in the states (relevant for this app)."""
        assert US_STATES["alaska"] == "AK"
        assert "AK" in STATE_ABBREVS
