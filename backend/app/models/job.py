import re

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("scrape_sources.id"), nullable=False)
    external_id = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    organization = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    state = Column(String(50), nullable=True, index=True)
    description = Column(Text, nullable=True)
    job_type = Column(String(100), nullable=True, index=True)
    salary_info = Column(String(255), nullable=True)
    url = Column(String(1000), nullable=False)
    first_seen_at = Column(DateTime, server_default=func.now())
    last_seen_at = Column(DateTime, server_default=func.now())
    is_stale = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    source = relationship("ScrapeSource", back_populates="jobs")
    saved_by = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")

    @property
    def display_location(self) -> str | None:
        """Return location with state appended if not already included.

        Examples:
            - location="Bethel", state="AK" -> "Bethel, AK"
            - location="Anchorage, AK", state="AK" -> "Anchorage, AK" (no duplication)
            - location="Bristol Bay Region, Alaska", state="AK" -> "Bristol Bay Region, AK"
            - location=None, state="AK" -> "AK"
            - location="Bethel", state=None -> "Bethel"
        """
        if not self.location and not self.state:
            return None

        if not self.location:
            return self.state

        if not self.state:
            return self.location

        # Check if state abbreviation is already in location to avoid duplication
        if self.state in self.location:
            return self.location

        # Normalize: remove full state name if present and replace with abbreviation
        # This handles cases like "Bristol Bay Region, Alaska" + state="AK"
        normalized = self._normalize_location_state(self.location, self.state)
        if normalized != self.location:
            return normalized

        return f"{self.location}, {self.state}"

    def _normalize_location_state(self, location: str, state: str) -> str:
        """Remove redundant full state name from location if abbreviation is provided.

        Handles patterns like:
            - "Bristol Bay Region, Alaska" + "AK" -> "Bristol Bay Region, AK"
            - "Fairbanks, Alaska" + "AK" -> "Fairbanks, AK"
        """
        # Map of state abbreviations to full names (50 states + DC + territories)
        state_names = {
            "AK": "Alaska",
            "AL": "Alabama",
            "AR": "Arkansas",
            "AS": "American Samoa",
            "AZ": "Arizona",
            "CA": "California",
            "CO": "Colorado",
            "CT": "Connecticut",
            "DC": "District of Columbia",
            "DE": "Delaware",
            "FL": "Florida",
            "GA": "Georgia",
            "GU": "Guam",
            "HI": "Hawaii",
            "IA": "Iowa",
            "ID": "Idaho",
            "IL": "Illinois",
            "IN": "Indiana",
            "KS": "Kansas",
            "KY": "Kentucky",
            "LA": "Louisiana",
            "MA": "Massachusetts",
            "MD": "Maryland",
            "ME": "Maine",
            "MI": "Michigan",
            "MN": "Minnesota",
            "MO": "Missouri",
            "MP": "Northern Mariana Islands",
            "MS": "Mississippi",
            "MT": "Montana",
            "NC": "North Carolina",
            "ND": "North Dakota",
            "NE": "Nebraska",
            "NH": "New Hampshire",
            "NJ": "New Jersey",
            "NM": "New Mexico",
            "NV": "Nevada",
            "NY": "New York",
            "OH": "Ohio",
            "OK": "Oklahoma",
            "OR": "Oregon",
            "PA": "Pennsylvania",
            "PR": "Puerto Rico",
            "RI": "Rhode Island",
            "SC": "South Carolina",
            "SD": "South Dakota",
            "TN": "Tennessee",
            "TX": "Texas",
            "UT": "Utah",
            "VA": "Virginia",
            "VI": "Virgin Islands",
            "VT": "Vermont",
            "WA": "Washington",
            "WI": "Wisconsin",
            "WV": "West Virginia",
            "WY": "Wyoming",
        }

        full_name = state_names.get(state.upper())
        if not full_name:
            return location

        # Check if full state name appears at the end (with comma or standalone)
        # Pattern: ", Alaska" or " Alaska" at the end
        pattern = rf",?\s*{re.escape(full_name)}\s*$"
        if re.search(pattern, location, re.IGNORECASE):
            # Replace with abbreviation
            normalized = re.sub(pattern, "", location, flags=re.IGNORECASE).strip()
            if normalized:
                return f"{normalized}, {state}"
            return state

        return location

    @property
    def display_job_type(self) -> str | None:
        """Return cleaned job type for display.

        Handles specific patterns like "80 Full time" -> "Full-Time".
        Returns the original value for other job types (Contract, etc).
        Returns None for category-style values that aren't employment types.
        """
        if not self.job_type:
            return None

        job_type_lower = self.job_type.lower().strip()

        # Pattern: "80 Full time" or "40 Part time" - hours followed by full/part
        hours_type_match = re.match(r"^(\d+)\s+(full|part)\s*[-\s]?time\s*$", job_type_lower, re.IGNORECASE)
        if hours_type_match:
            employment_type = hours_type_match.group(2).lower()
            if employment_type == "full":
                return "Full-Time"
            else:
                return "Part-Time"

        # Normalize common full-time/part-time variations
        if re.match(r"^full\s*[-\s]?time$", job_type_lower):
            return "Full-Time"
        if re.match(r"^part\s*[-\s]?time$", job_type_lower):
            return "Part-Time"

        # Keep other valid employment types as-is (using word boundaries)
        valid_types = [
            "contract", "temporary", "seasonal", "internship",
            "volunteer", "per diem", "prn", "on-call", "casual",
            "regular", "permanent", "freelance", "consulting"
        ]
        for valid in valid_types:
            # Use word boundary to avoid matching "internal" for "intern", etc.
            if re.search(rf"\b{re.escape(valid)}\b", job_type_lower):
                return self.job_type.strip()

        # Filter out category-style values that aren't employment types
        # These are job categories, not employment types
        category_keywords = [
            "healthcare", "administrative", "management", "education",
            "clinical", "nursing", "finance", "marketing", "executive",
            "facilities", "maintenance", "support", "program", "open",
            "various", "multiple"
        ]
        for keyword in category_keywords:
            if keyword in job_type_lower:
                return None

        # For anything else, return the original value
        return self.job_type.strip()

    __table_args__ = (
        Index("ix_jobs_stale_last_seen", "is_stale", "last_seen_at"),
        Index("ix_jobs_location", "location"),
    )
