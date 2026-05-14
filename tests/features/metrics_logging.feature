Feature: Metrics logging tool

  # ---------------------------------------------------------------------------
  # 1. Log a single metric (weight in lbs)
  # ---------------------------------------------------------------------------

  Scenario: Log a single weight metric in lbs
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and weight value 182.4 unit "lbs"
    Then the result status is "ok"
    And the result date is "2025-05-13"

  # ---------------------------------------------------------------------------
  # 2. Log multiple metrics in one call
  # ---------------------------------------------------------------------------

  Scenario: Log multiple metrics in one call
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" weight 182.4 lbs and hrv 55.0 ms
    Then the result status is "ok"
    And the result date is "2025-05-13"

  # ---------------------------------------------------------------------------
  # 3. Return value includes correct captured list
  # ---------------------------------------------------------------------------

  Scenario: Return value includes correct captured list for weight only
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and weight value 182.4 unit "lbs"
    Then the captured list is ["weight"]

  Scenario: Return value includes correct captured list for multiple metrics
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" weight 182.4 lbs and hrv 55.0 ms
    Then the captured list is ["weight", "hrv"]

  # ---------------------------------------------------------------------------
  # 4. No null fields written to JSONL
  # ---------------------------------------------------------------------------

  Scenario: No null fields written when only weight is provided
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and weight value 182.4 unit "lbs"
    Then the written entry has no null fields

  # ---------------------------------------------------------------------------
  # 5. Invalid unit rejected (weight unit "stone")
  # ---------------------------------------------------------------------------

  Scenario: Invalid weight unit is rejected
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and invalid weight unit "stone"
    Then a validation error is raised
    And no file is written

  # ---------------------------------------------------------------------------
  # 6. Invalid sleep quality rejected
  # ---------------------------------------------------------------------------

  Scenario: Invalid sleep quality 6 is rejected
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and sleep quality 6
    Then a validation error is raised
    And no file is written

  # ---------------------------------------------------------------------------
  # 7. Negative value rejected
  # ---------------------------------------------------------------------------

  Scenario: Negative weight value is rejected
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and weight value -1.0 unit "lbs"
    Then a validation error is raised
    And no file is written

  # ---------------------------------------------------------------------------
  # 8. Date-only call rejected
  # ---------------------------------------------------------------------------

  Scenario: Date-only call with no metrics is rejected
    Given a temporary vault directory
    When I call log_metrics with only date "2025-05-13"
    Then a validation error is raised
    And no file is written

  # ---------------------------------------------------------------------------
  # 9. Invalid date string rejected
  # ---------------------------------------------------------------------------

  Scenario: Invalid date string is rejected
    Given a temporary vault directory
    When I call log_metrics with date "not-a-date" and weight value 182.4 unit "lbs"
    Then a validation error is raised
    And no file is written

  # ---------------------------------------------------------------------------
  # 10. Entry written to correct annual JSONL file
  # ---------------------------------------------------------------------------

  Scenario: Entry is written to the correct annual JSONL file
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and weight value 182.4 unit "lbs"
    Then the file "logs/metrics/2025.jsonl" exists in the vault
    And the file "logs/metrics/2025.jsonl" contains 1 line

  # ---------------------------------------------------------------------------
  # 11. Sleep with optional quality and source fields
  # ---------------------------------------------------------------------------

  Scenario: Log sleep with duration only
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and sleep duration 7.5
    Then the result status is "ok"
    And the captured list is ["sleep"]

  Scenario: Log sleep with quality and source
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and sleep duration 7.5 quality 4 source "Oura"
    Then the result status is "ok"
    And the captured list is ["sleep"]

  # ---------------------------------------------------------------------------
  # 12. HRV with optional source field
  # ---------------------------------------------------------------------------

  Scenario: Log hrv with source
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and hrv value 55.0 source "Garmin"
    Then the result status is "ok"
    And the captured list is ["hrv"]

  # ---------------------------------------------------------------------------
  # 13. Blood pressure logging
  # ---------------------------------------------------------------------------

  Scenario: Log blood pressure
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and blood_pressure 120 over 80
    Then the result status is "ok"
    And the captured list is ["blood_pressure"]

  # ---------------------------------------------------------------------------
  # 14. SpO2 logging
  # ---------------------------------------------------------------------------

  Scenario: Log spo2
    Given a temporary vault directory
    When I call log_metrics with date "2025-05-13" and spo2 value 98.5
    Then the result status is "ok"
    And the captured list is ["spo2"]
