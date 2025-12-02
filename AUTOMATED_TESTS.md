# Automated Tests

This document catalogs all automated tests in the Far Reach Jobs test suite.

**Location:** `backend/tests/`
**Framework:** pytest
**Run tests:** `cd backend && python -m pytest tests/ -v`

---

## Test Files Overview

| File | Tests | Description |
|------|-------|-------------|
| `test_admin.py` | 70 | Admin panel authentication, sources, scraping, CSV import |
| `test_auth.py` | 21 | User registration, login, email verification, JWT tokens |
| `test_jobs.py` | 28 | Job listing, search, filtering, pagination |
| `test_saved_jobs.py` | 17 | Save/unsave jobs, user isolation |
| `test_models.py` | 49 | SQLAlchemy model validation, relationships, indexes |
| `test_stats.py` | 8 | Homepage stats banner endpoint |
| `test_robots.py` | 26 | robots.txt parsing, specificity-based matching |
| `test_scraper_utils.py` | 44 | State normalization, text cleaning, salary extraction |
| `test_ultipro_scraper.py` | 34 | UltiPro/UKG Pro API scraper |
| `test_adp_scraper.py` | 7 | ADP Workforce API scraper |
| `test_ai_analyzer.py` | 7 | AI scraper code generation and extraction |
| `test_playwright_fallback.py` | 7 | Playwright/httpx fallback behavior |

---

## Admin Panel Tests (`test_admin.py`)

### TestAdminAuthentication
| Test | Description |
|------|-------------|
| `test_login_page_renders` | Login page loads successfully |
| `test_login_page_redirects_if_already_logged_in` | Redirects authenticated users away from login |
| `test_login_success` | Valid credentials grant access |
| `test_login_wrong_username` | Invalid username rejected |
| `test_login_wrong_password` | Invalid password rejected |
| `test_login_empty_credentials` | Empty form rejected |
| `test_logout_success` | Logout endpoint works |
| `test_logout_clears_session` | Session cleared after logout |
| `test_dashboard_requires_auth` | Dashboard protected |
| `test_dashboard_accessible_when_authenticated` | Dashboard accessible with valid session |

### TestAdminDashboard
| Test | Description |
|------|-------------|
| `test_dashboard_shows_job_counts` | Displays correct job statistics |
| `test_dashboard_shows_sources_via_htmx` | Sources loaded via HTMX |
| `test_dashboard_shows_disabled_source_count` | Shows disabled source count badge |

### TestSourceManagement
| Test | Description |
|------|-------------|
| `test_list_sources_requires_auth` | Source list protected |
| `test_list_sources_returns_active_only` | Only active sources in main list |
| `test_create_source_requires_auth` | Source creation protected |
| `test_create_source_success` | Valid source created |
| `test_create_source_missing_name` | Name validation |
| `test_create_source_missing_url` | URL validation |
| `test_delete_source_requires_auth` | Deletion protected |
| `test_delete_source_success` | Source deleted |
| `test_delete_nonexistent_source` | 404 for missing source |
| `test_toggle_source_requires_auth` | Toggle protected |
| `test_toggle_source_active_to_inactive` | Disable source |
| `test_toggle_source_inactive_to_active` | Enable source |

### TestDisabledSources
| Test | Description |
|------|-------------|
| `test_disabled_sources_page_requires_auth` | Page protected |
| `test_disabled_sources_page_accessible` | Page loads |
| `test_disabled_sources_list_requires_auth` | List protected |
| `test_disabled_sources_list_returns_inactive_only` | Only disabled sources shown |
| `test_disabled_count_link_requires_auth` | Count badge protected |
| `test_disabled_count_returns_count` | Correct count returned |

### TestSourceEdit
| Test | Description |
|------|-------------|
| `test_edit_page_requires_auth` | Edit page protected |
| `test_edit_page_accessible` | Edit page loads |
| `test_edit_page_nonexistent_source` | 404 for missing source |
| `test_edit_source_requires_auth` | Edit action protected |
| `test_edit_source_success` | Source updated |
| `test_edit_source_validation_name_required` | Name required |
| `test_edit_source_validation_url_required` | URL required |
| `test_edit_source_validation_url_format` | URL format validated |

### TestSourceConfigure
| Test | Description |
|------|-------------|
| `test_configure_page_requires_auth` | Configure page protected |
| `test_configure_page_accessible` | Configure page loads |
| `test_configure_page_nonexistent_source` | 404 for missing source |
| `test_configure_source_requires_auth` | Configure action protected |
| `test_configure_source_success` | Configuration saved |
| `test_configure_source_warns_missing_selectors` | Warning for incomplete config |
| `test_configure_source_checkbox_use_playwright` | Playwright toggle works |

### TestScrapeHistory
| Test | Description |
|------|-------------|
| `test_history_page_requires_auth` | History page protected |
| `test_history_page_accessible` | History page loads |
| `test_history_page_shows_logs` | Scrape logs displayed |
| `test_history_page_shows_stats` | Summary stats displayed |

### TestTriggerScrape
| Test | Description |
|------|-------------|
| `test_scrape_all_requires_auth` | Bulk scrape protected |
| `test_scrape_all_no_sources` | Handles no sources |
| `test_scrape_all_success` | Bulk scrape works |
| `test_scrape_single_requires_auth` | Single scrape protected |
| `test_scrape_single_not_found` | 404 for missing source |
| `test_scrape_single_success` | Single scrape works |

### TestSourceExport
| Test | Description |
|------|-------------|
| `test_export_active_requires_auth` | Export protected |
| `test_export_disabled_requires_auth` | Export protected |
| `test_export_robots_blocked_requires_auth` | Export protected |
| `test_export_active_returns_csv` | CSV format correct |
| `test_export_active_excludes_inactive` | Only active sources |
| `test_export_active_excludes_robots_blocked` | Excludes blocked |
| `test_export_disabled_returns_csv` | CSV format correct |
| `test_export_disabled_excludes_active` | Only disabled sources |
| `test_export_robots_blocked_returns_csv` | CSV format correct |
| `test_export_robots_blocked_excludes_active` | Only blocked sources |
| `test_export_empty_returns_header_only` | Empty CSV has header |
| `test_export_alphabetical_order` | Sources sorted A-Z |
| `test_export_includes_listing_url` | Listing URL in export |

### TestAIFeatures
| Test | Description |
|------|-------------|
| `test_analyze_requires_auth` | AI analysis protected |
| `test_analyze_nonexistent_source` | 404 for missing source |
| `test_analyze_ai_not_available` | Graceful handling when AI unavailable |
| `test_analyze_success` | AI analysis works |
| `test_generate_scraper_requires_auth` | Generation protected |
| `test_generate_scraper_nonexistent_source` | 404 for missing source |
| `test_generate_scraper_ai_not_available` | Graceful handling when AI unavailable |
| `test_generated_scraper_escapes_html_in_code` | **XSS/parsing prevention** - ensures `</script>` in code is escaped |

### TestUrlNormalization
| Test | Description |
|------|-------------|
| `test_normalize_strips_trailing_slash` | URL normalization |
| `test_normalize_lowercase` | Case normalization |
| `test_normalize_strips_protocol` | Protocol removal |
| `test_normalize_strips_www` | www removal |
| `test_normalize_combined` | All normalizations combined |

### TestCSVImport
| Test | Description |
|------|-------------|
| `test_import_requires_auth` | Import protected |
| `test_import_requires_csv_file` | File required |
| `test_import_basic_success` | CSV import works |
| `test_import_detects_duplicate_name` | Duplicate name rejected |
| `test_import_detects_duplicate_base_url` | Duplicate URL rejected |
| `test_import_detects_duplicate_base_url_with_www_variation` | www variation detected |
| `test_import_detects_duplicate_base_url_with_protocol_variation` | http/https detected |
| `test_import_detects_cross_field_collision_base_matches_existing_listing` | Cross-field check |
| `test_import_detects_cross_field_collision_listing_matches_existing_base` | Cross-field check |
| `test_import_detects_in_batch_duplicates` | In-batch duplicate detection |
| `test_import_detects_in_batch_cross_field_duplicates` | In-batch cross-field check |

---

## Authentication Tests (`test_auth.py`)

### TestRegistration
| Test | Description |
|------|-------------|
| `test_register_success` | User registration works |
| `test_register_duplicate_email` | Duplicate email rejected |
| `test_register_invalid_email` | Invalid email rejected |
| `test_register_password_too_short` | Password min length enforced |
| `test_register_password_too_long` | Password max length enforced |
| `test_register_auto_verify_in_dev_mode` | Auto-verify when SMTP not configured |

### TestLogin
| Test | Description |
|------|-------------|
| `test_login_success` | Valid login works |
| `test_login_wrong_password` | Wrong password rejected |
| `test_login_nonexistent_user` | Unknown user rejected |
| `test_login_unverified_user` | Unverified user rejected |

### TestEmailVerification
| Test | Description |
|------|-------------|
| `test_verify_valid_token` | Valid token verifies user |
| `test_verify_invalid_token` | Invalid token rejected |
| `test_verify_expired_token` | Expired token rejected (24h) |
| `test_verify_already_verified_user` | Already verified handled |

### TestLogout
| Test | Description |
|------|-------------|
| `test_logout_clears_cookie` | Cookie cleared on logout |

### TestResendVerification
| Test | Description |
|------|-------------|
| `test_resend_for_unverified_user` | Resend works for unverified |
| `test_resend_for_nonexistent_user` | Unknown user handled |
| `test_resend_for_verified_user` | Already verified handled |
| `test_resend_missing_email` | Email required |

### TestGetCurrentUser
| Test | Description |
|------|-------------|
| `test_get_me_authenticated` | Returns user info |
| `test_get_me_no_token` | 401 without token |
| `test_get_me_invalid_token` | Invalid token rejected |
| `test_get_me_expired_token` | Expired token rejected |
| `test_get_me_deleted_user` | Deleted user handled |

---

## Jobs API Tests (`test_jobs.py`)

### TestListJobs
| Test | Description |
|------|-------------|
| `test_list_jobs_empty` | Empty database returns empty list |
| `test_list_jobs_returns_non_stale_only` | Stale jobs excluded |
| `test_list_jobs_pagination` | Pagination works |
| `test_list_jobs_pagination_limits` | Page size limits enforced |
| `test_list_jobs_ordered_by_last_seen` | Jobs sorted by recency |

### TestSearchJobs
| Test | Description |
|------|-------------|
| `test_search_by_title` | Title search works |
| `test_search_by_organization` | Org search works |
| `test_search_by_description` | Description search works |
| `test_search_by_location` | Location search works |
| `test_search_case_insensitive` | Case-insensitive search |
| `test_search_no_results` | No results handled |

### TestFilterJobs
| Test | Description |
|------|-------------|
| `test_filter_by_state` | State filter works |
| `test_filter_by_location` | Location filter works |
| `test_filter_by_job_type` | Job type filter works |
| `test_filter_by_organization` | Org filter works |
| `test_filter_by_source_id` | Source filter works |
| `test_filter_by_date_posted_1_day` | 1 day filter |
| `test_filter_by_date_posted_7_days` | 7 day filter |
| `test_filter_by_date_posted_30_days` | 30 day filter |
| `test_combined_filters` | Multiple filters combined |
| `test_invalid_source_id_ignored` | Invalid filter ignored |
| `test_invalid_date_posted_ignored` | Invalid filter ignored |

### TestGetSingleJob
| Test | Description |
|------|-------------|
| `test_get_job_success` | Job retrieval works |
| `test_get_job_not_found` | 404 for missing job |
| `test_get_stale_job_returns_404` | Stale jobs return 404 |

### TestGetStates
| Test | Description |
|------|-------------|
| `test_get_states_empty` | Empty returns empty list |
| `test_get_states_returns_unique` | Unique states returned |
| `test_get_states_excludes_stale` | Stale jobs excluded |

### TestGetLocations
| Test | Description |
|------|-------------|
| `test_get_locations_empty` | Empty returns empty list |
| `test_get_locations_returns_unique` | Unique locations returned |
| `test_get_locations_htmx_returns_html` | HTMX response is HTML |

### TestGetJobTypes
| Test | Description |
|------|-------------|
| `test_get_job_types_empty` | Empty returns empty list |
| `test_get_job_types_returns_unique` | Unique types returned |

### TestHTMXResponses
| Test | Description |
|------|-------------|
| `test_list_jobs_htmx_returns_html` | HTMX response is HTML partial |

---

## Saved Jobs Tests (`test_saved_jobs.py`)

### TestListSavedJobs
| Test | Description |
|------|-------------|
| `test_list_saved_jobs_unauthenticated` | 401 without auth |
| `test_list_saved_jobs_empty` | Empty list for new user |
| `test_list_saved_jobs_with_jobs` | Returns saved jobs |
| `test_list_saved_jobs_user_isolation` | Users see only their saved jobs |
| `test_list_saved_jobs_ordered_by_saved_at` | Sorted by save date |

### TestSaveJob
| Test | Description |
|------|-------------|
| `test_save_job_unauthenticated` | 401 without auth |
| `test_save_job_success` | Job saved |
| `test_save_job_idempotent` | Double-save is safe |
| `test_save_nonexistent_job` | 404 for missing job |
| `test_save_stale_job` | Cannot save stale job |

### TestUnsaveJob
| Test | Description |
|------|-------------|
| `test_unsave_job_unauthenticated` | 401 without auth |
| `test_unsave_job_success` | Job unsaved |
| `test_unsave_job_not_saved` | Unsave non-saved is safe |
| `test_unsave_other_users_job` | Cannot unsave other's job |

### TestHTMXResponses
| Test | Description |
|------|-------------|
| `test_list_saved_jobs_htmx` | HTMX response is HTML |
| `test_save_job_htmx` | Save button HTML returned |
| `test_unsave_job_htmx_from_listing` | Unsave from listing |
| `test_unsave_job_htmx_from_saved_page` | Unsave from saved page |

---

## Model Tests (`test_models.py`)

### TestUserModel
| Test | Description |
|------|-------------|
| `test_create_user_with_required_fields` | User creation |
| `test_user_email_unique_constraint` | Email uniqueness |
| `test_user_email_required` | Email required |
| `test_user_password_hash_required` | Password required |
| `test_user_default_values` | Default values set |
| `test_user_saved_jobs_relationship` | Relationship works |
| `test_user_cascade_delete_saved_jobs` | Cascade delete |

### TestJobModel
| Test | Description |
|------|-------------|
| `test_create_job_with_required_fields` | Job creation |
| `test_job_external_id_unique_constraint` | External ID unique |
| `test_job_source_id_required` | Source required |
| `test_job_default_values` | Default values set |
| `test_job_source_relationship` | Relationship works |
| `test_job_saved_by_relationship` | Relationship works |
| `test_job_cascade_delete_saved_jobs` | Cascade delete |
| `test_job_optional_fields` | Optional fields nullable |
| `test_display_location_combines_location_and_state` | Display helper |
| `test_display_location_normalizes_full_state_name` | State normalization |
| `test_display_job_type_full_time` | Job type display |
| `test_display_job_type_part_time` | Job type display |
| `test_display_job_type_none_for_categories` | Category handling |
| `test_display_job_type_preserves_other_types` | Other types preserved |

### TestSavedJobModel
| Test | Description |
|------|-------------|
| `test_create_saved_job` | SavedJob creation |
| `test_saved_job_unique_constraint` | User+job unique |
| `test_saved_job_user_relationship` | Relationship works |
| `test_saved_job_job_relationship` | Relationship works |
| `test_saved_job_cascade_on_user_delete` | Cascade on user delete |
| `test_saved_job_cascade_on_job_delete` | Cascade on job delete |

### TestScrapeSourceModel
| Test | Description |
|------|-------------|
| `test_create_source_with_required_fields` | Source creation |
| `test_source_default_values` | Default values set |
| `test_source_playwright_default_is_true` | Playwright enabled by default |
| `test_source_playwright_can_be_disabled` | Playwright can be disabled |
| `test_source_jobs_relationship` | Relationship works |
| `test_source_cascade_delete_jobs` | Cascade delete |
| `test_source_selector_fields` | Selector fields work |
| `test_source_custom_scraper_code` | Custom code storage |

### TestScrapeLogModel
| Test | Description |
|------|-------------|
| `test_create_scrape_log` | Log creation |
| `test_scrape_log_default_values` | Default values set |
| `test_scrape_log_source_relationship` | Relationship works |
| `test_scrape_log_preserves_source_name_on_delete` | Name preserved after source delete |
| `test_scrape_log_with_results` | Results stored |
| `test_scrape_log_with_errors` | Errors stored |
| `test_scrape_log_trigger_type_required` | Trigger type required |
| `test_scrape_log_source_name_required` | Source name required |

### TestModelIndexes
| Test | Description |
|------|-------------|
| `test_user_email_index` | Email index exists |
| `test_job_external_id_index` | External ID index exists |
| `test_job_state_index` | State index exists |
| `test_job_is_stale_index` | Is stale index exists |

---

## Stats Tests (`test_stats.py`)

| Test | Description |
|------|-------------|
| `test_stats_empty_database` | Empty DB returns zeros |
| `test_stats_counts_active_sources_only` | Only active sources counted |
| `test_stats_excludes_stale_jobs` | Stale jobs excluded |
| `test_stats_new_this_week_includes_recent_jobs` | Recent jobs counted |
| `test_stats_new_this_week_excludes_old_jobs` | Old jobs excluded |
| `test_stats_new_this_week_excludes_stale_jobs` | Stale jobs excluded |
| `test_stats_combined_scenario` | Complex scenario |
| `test_stats_returns_html_for_htmx_request` | HTMX response is HTML |

---

## Robots.txt Tests (`test_robots.py`)

### TestSpecificityBasedMatching
| Test | Description |
|------|-------------|
| `test_allow_overrides_disallow_when_more_specific` | Longer Allow wins |
| `test_disallow_overrides_allow_when_more_specific` | Longer Disallow wins |
| `test_equal_length_allow_wins` | Tie goes to Allow |
| `test_order_does_not_matter` | Order independent |
| `test_wildcard_in_pattern` | Wildcards work |
| `test_end_anchor` | End anchors work |
| `test_query_string_handling` | Query strings handled |
| `test_no_matching_rules_allows` | No rules = allowed |
| `test_paycomonline_real_robots` | Real-world robots.txt |

### TestPatternMatches
| Test | Description |
|------|-------------|
| `test_simple_prefix_match` | Prefix matching |
| `test_wildcard_match` | Wildcard matching |
| `test_end_anchor_match` | End anchor matching |

### TestParseRobotsRules
| Test | Description |
|------|-------------|
| `test_parses_allow_and_disallow` | Rule parsing |
| `test_ignores_other_user_agents` | UA filtering |
| `test_handles_comments` | Comment handling |
| `test_ignores_empty_values` | Empty value handling |
| `test_specific_ua_takes_precedence_over_wildcard` | UA precedence |
| `test_multiple_ua_lines_in_group` | Multi-UA groups |
| `test_multiple_ua_lines_with_wildcard` | Wildcard in group |
| `test_specific_after_wildcard_still_wins` | Specificity wins |
| `test_longest_ua_match_wins` | Longest UA match |
| `test_longer_ua_wins_regardless_of_order` | Order independent |
| `test_equal_length_ua_first_wins` | Tie-breaker |

### TestRobotsCheckerCrossDomain
| Test | Description |
|------|-------------|
| `test_cross_domain_uses_target_domain_robots` | Cross-domain fetch |
| `test_same_domain_uses_base_robots` | Same-domain reuse |
| `test_cross_domain_caches_results` | Caching works |
| `test_cross_domain_no_robots_allows_all` | Missing = allowed |
| `test_real_world_scenario_bbahc` | Real-world scenario |

### TestRobotsCheckerHttpScheme
| Test | Description |
|------|-------------|
| `test_http_base_url_uses_http_for_robots` | HTTP scheme preserved |
| `test_cross_domain_http_url_uses_http` | HTTP preserved cross-domain |

---

## Scraper Utility Tests (`test_scraper_utils.py`)

### State Normalization
| Test | Description |
|------|-------------|
| `test_full_state_name` | Full name → abbreviation |
| `test_lowercase_state_name` | Case insensitive |
| `test_mixed_case_state_name` | Mixed case handled |
| `test_abbreviation_uppercase` | Uppercase abbrev |
| `test_abbreviation_lowercase` | Lowercase abbrev |
| `test_whitespace_handling` | Whitespace trimmed |
| `test_empty_input` | Empty returns None |
| `test_invalid_state` | Invalid returns None |
| `test_all_states_have_mappings` | All 50 states mapped |

### TestExtractStateFromLocation
| Test | Description |
|------|-------------|
| `test_city_comma_state` | "City, ST" format |
| `test_city_state_zip` | "City, ST 12345" format |
| `test_state_zip_only` | "ST 12345" format |
| `test_full_state_name` | Full state name |
| `test_state_name_case_insensitive` | Case insensitive |
| `test_no_state_found` | Returns None |
| `test_empty_input` | Empty returns None |
| `test_invalid_abbreviation` | Invalid abbrev |
| `test_substring_matching_caveat` | Substring edge case |

### TestCleanText
| Test | Description |
|------|-------------|
| `test_multiple_spaces` | Multiple spaces collapsed |
| `test_newlines_and_tabs` | Whitespace normalized |
| `test_leading_trailing_whitespace` | Trimmed |
| `test_mixed_whitespace` | All whitespace handled |
| `test_already_clean` | Clean text unchanged |
| `test_empty_input` | Empty returns empty |
| `test_whitespace_only` | Whitespace-only returns empty |

### TestExtractSalary
| Test | Description |
|------|-------------|
| `test_dollar_amount` | Dollar amount extracted |
| `test_salary_range` | Range extracted |
| `test_hourly_rate` | Hourly rate extracted |
| `test_per_hour_format` | "/hour" format |
| `test_annual_salary` | Annual salary |
| `test_salary_in_description` | Salary in description |
| `test_no_salary_found` | Returns None |
| `test_empty_input` | Empty returns None |

### TestNormalizeJobType
| Test | Description |
|------|-------------|
| `test_full_time_variations` | Full-time variants |
| `test_part_time_variations` | Part-time variants |
| `test_seasonal` | Seasonal type |
| `test_contract` | Contract type |
| `test_temporary` | Temporary type |
| `test_internship` | Internship type |
| `test_unknown_type_cleaned` | Unknown cleaned |
| `test_empty_input` | Empty returns None |

### TestStateConstants
| Test | Description |
|------|-------------|
| `test_state_abbrevs_reverse_lookup` | Reverse lookup works |
| `test_alaska_is_present` | Alaska in constants |

---

## UltiPro/UKG Scraper Tests (`test_ultipro_scraper.py`)

### TestUltiProScraper
| Test | Description |
|------|-------------|
| `test_extracts_tenant_and_board_id_from_url` | URL parsing |
| `test_extracts_from_url_without_trailing_slash` | No trailing slash |
| `test_builds_correct_api_url` | API URL construction |
| `test_builds_correct_job_detail_url` | Job detail URL |
| `test_parses_job_from_api_response` | Job parsing |
| `test_parses_part_time_job` | Part-time parsing |
| `test_handles_missing_location` | Missing location handled |
| `test_handles_null_locations` | Null locations handled |
| `test_run_fetches_from_api` | API fetch works |
| `test_handles_pagination` | Pagination works |
| `test_handles_missing_tenant` | Missing tenant error |
| `test_handles_api_error` | API errors handled |
| `test_uses_requisition_number_for_external_id` | External ID format |
| `test_handles_city_only_location` | City-only location |
| `test_handles_state_as_object` | State as object |
| `test_normalizes_job_detail_url_to_board_url` | URL normalization |
| `test_preserves_host_from_input_url` | Host preserved |
| `test_builds_normalized_board_url` | Board URL |
| `test_extracts_tenant_and_board_id_from_ukg_pro_url` | UKG Pro parsing |
| `test_builds_correct_api_url_for_ukg_pro` | UKG Pro API URL |
| `test_builds_correct_job_detail_url_for_ukg_pro` | UKG Pro detail URL |
| `test_handles_ukg_pro_url_with_query_params` | Query params |
| `test_parses_job_from_ukg_pro_api_response` | UKG Pro response |

### TestIsUltiproUrl
| Test | Description |
|------|-------------|
| `test_detects_recruiting2_ultipro_url` | recruiting2 URL |
| `test_detects_recruiting_ultipro_url` | recruiting URL |
| `test_detects_ukg_pro_url` | UKG Pro URL |
| `test_detects_ukg_pro_url_with_query_params` | UKG Pro with params |
| `test_returns_false_for_non_ultipro_url` | Non-UltiPro rejected |
| `test_returns_false_for_none` | None rejected |
| `test_returns_false_for_empty_string` | Empty rejected |
| `test_case_insensitive` | Case insensitive |

### TestIsAdpWorkforceUrl
| Test | Description |
|------|-------------|
| `test_detects_adp_workforce_url` | ADP URL detected |
| `test_returns_false_for_non_adp_url` | Non-ADP rejected |
| `test_returns_false_for_none` | None rejected |
| `test_returns_false_for_empty_string` | Empty rejected |
| `test_case_insensitive` | Case insensitive |

### TestApiScrapersSkipRobotsCheck
| Test | Description |
|------|-------------|
| `test_ultipro_scraper_bypasses_robots_check` | UltiPro skips robots |
| `test_ukg_pro_scraper_bypasses_robots_check` | UKG Pro skips robots |
| `test_adp_scraper_bypasses_robots_check` | ADP skips robots |
| `test_generic_scraper_does_check_robots` | Generic checks robots |

---

## ADP Scraper Tests (`test_adp_scraper.py`)

### TestADPWorkforceScraper
| Test | Description |
|------|-------------|
| `test_extracts_cid_and_ccid_from_url` | URL parameter extraction |
| `test_builds_correct_api_url` | API URL construction |
| `test_parses_job_from_api_response` | Job parsing |
| `test_run_fetches_from_api` | API fetch works |
| `test_handles_missing_cid` | Missing CID error |
| `test_handles_api_error` | API errors handled |
| `test_handles_null_custom_field_group` | Null fields handled |

---

## AI Analyzer Tests (`test_ai_analyzer.py`)

### TestCodeExtraction
| Test | Description |
|------|-------------|
| `test_extracts_code_from_markdown_with_explanation` | Markdown extraction |
| `test_extracts_code_from_pure_markdown_block` | Pure markdown |
| `test_extracts_code_without_python_lang_specifier` | No lang specifier |
| `test_handles_raw_code_without_markdown` | Raw code handling |
| `test_strips_import_statements` | Import stripping |
| `test_rejects_response_without_required_methods` | Validation |
| `test_extracts_code_from_unterminated_code_block` | Unterminated block |

---

## Playwright Fallback Tests (`test_playwright_fallback.py`)

### TestPlaywrightFallback
| Test | Description |
|------|-------------|
| `test_playwright_success_no_fallback` | No fallback when successful |
| `test_playwright_failure_falls_back_to_httpx` | Fallback on failure |
| `test_playwright_unavailable_uses_httpx` | httpx when unavailable |
| `test_robots_txt_blocks_before_playwright` | robots.txt checked first |
| `test_playwright_disabled_uses_httpx_only` | httpx when disabled |

### TestPlaywrightFetcherAvailability
| Test | Description |
|------|-------------|
| `test_fetcher_unavailable_without_url` | Unavailable without URL |
| `test_fetcher_available_with_url` | Available with URL |

---

## Running Tests

```bash
# Run all tests
cd backend && python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_admin.py -v

# Run specific test class
python -m pytest tests/test_admin.py::TestAdminAuthentication -v

# Run specific test
python -m pytest tests/test_admin.py::TestAIFeatures::test_generated_scraper_escapes_html_in_code -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

## CI/CD

Tests run automatically on:
- Push to `main` branch
- Pull requests targeting `main`

See `.github/workflows/ci.yml` for configuration.
