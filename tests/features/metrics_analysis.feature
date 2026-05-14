Feature: Metrics analysis functions

  Background:
    Given a temporary vault directory
    And today is mocked to "2025-03-01"

  # -----------------------------------------------------------------------
  # weight_trend
  # -----------------------------------------------------------------------

  Scenario: weight_trend single data point has no slope or delta
    Given a metrics entry with date "2025-01-10" and weight value 180.0 unit "lbs"
    When I call weight_trend with no date filter
    Then the trend result field "data_points" equals int 1
    And the trend result field "slope" is None
    And the trend result field "delta" is None
    And the trend result field "average" equals float 180.0
    And the trend result field "min" equals float 180.0
    And the trend result field "max" equals float 180.0
    And the trend result field "unit" equals string "lbs"

  Scenario: weight_trend two data points compute slope and delta
    Given a metrics entry with date "2025-01-01" and weight value 180.0 unit "lbs"
    And a metrics entry with date "2025-01-11" and weight value 175.0 unit "lbs"
    When I call weight_trend with no date filter
    Then the trend result field "data_points" equals int 2
    And the trend result field "delta" equals float -5.0
    And the trend result field "slope" equals float -0.5
    And the trend result field "average" equals float 177.5

  Scenario: weight_trend multiple data points computes all stats correctly
    Given a metrics entry with date "2025-01-01" and weight value 200.0 unit "lbs"
    And a metrics entry with date "2025-01-03" and weight value 198.0 unit "lbs"
    And a metrics entry with date "2025-01-05" and weight value 196.0 unit "lbs"
    When I call weight_trend with no date filter
    Then the trend result field "data_points" equals int 3
    And the trend result field "average" equals float 198.0
    And the trend result field "min" equals float 196.0
    And the trend result field "max" equals float 200.0
    And the trend result field "delta" equals float -4.0

  Scenario: weight_trend no data returns all-None result
    When I call weight_trend with no date filter
    Then the trend result field "data_points" equals int 0
    And the trend result field "slope" is None
    And the trend result field "average" is None
    And the trend result field "min" is None
    And the trend result field "max" is None
    And the trend result field "delta" is None
    And the trend result field "unit" is None
    And the trend result field "start_date" is None
    And the trend result field "end_date" is None

  Scenario: weight_trend window filtering excludes entries outside range
    Given today is mocked to "2025-03-01"
    And a metrics entry with date "2025-03-01" and weight value 175.0 unit "lbs"
    And a metrics entry with date "2024-12-01" and weight value 200.0 unit "lbs"
    When I call weight_trend with days=60
    Then the trend result field "data_points" equals int 1
    And the trend result field "average" equals float 175.0

  Scenario: weight_trend unit in result matches logged unit
    Given a metrics entry with date "2025-01-10" and weight value 80.0 unit "kg"
    When I call weight_trend with no date filter
    Then the trend result field "unit" equals string "kg"
    And the trend result field "average" equals float 80.0

  Scenario: weight_trend mixed units normalizes to first entry unit
    Given a metrics entry with date "2025-01-01" and weight value 100.0 unit "kg"
    And a metrics entry with date "2025-01-02" and weight value 220.462 unit "lbs"
    When I call weight_trend with no date filter
    Then the trend result field "data_points" equals int 2
    And the trend result field "unit" equals string "kg"

  # -----------------------------------------------------------------------
  # hrv_trend
  # -----------------------------------------------------------------------

  Scenario: hrv_trend multiple entries compute slope and average
    Given a metrics entry with date "2025-01-01" and hrv value 50.0
    And a metrics entry with date "2025-01-03" and hrv value 54.0
    And a metrics entry with date "2025-01-05" and hrv value 58.0
    When I call hrv_trend with no date filter
    Then the trend result field "data_points" equals int 3
    And the trend result field "unit" equals string "ms"
    And the trend result field "average" equals float 54.0
    And the trend result field "slope" equals float 2.0

  Scenario: hrv_trend no data returns all-None result
    When I call hrv_trend with no date filter
    Then the trend result field "data_points" equals int 0
    And the trend result field "slope" is None
    And the trend result field "average" is None

  # -----------------------------------------------------------------------
  # sleep_summary
  # -----------------------------------------------------------------------

  Scenario: sleep_summary entries with quality
    Given a metrics entry with date "2025-01-01" and sleep duration 7.0 quality 4
    And a metrics entry with date "2025-01-02" and sleep duration 8.0 quality 5
    When I call sleep_summary with no date filter
    Then the trend result field "data_points" equals int 2
    And the trend result field "average_duration_hours" equals float 7.5
    And the trend result field "average_quality" equals float 4.5
    And the trend result field "quality_data_points" equals int 2

  Scenario: sleep_summary entries without quality
    Given a metrics entry with date "2025-01-01" and sleep duration 7.0 no quality
    And a metrics entry with date "2025-01-02" and sleep duration 9.0 no quality
    When I call sleep_summary with no date filter
    Then the trend result field "data_points" equals int 2
    And the trend result field "average_duration_hours" equals float 8.0
    And the trend result field "average_quality" is None
    And the trend result field "quality_data_points" equals int 0

  Scenario: sleep_summary mixed quality presence
    Given a metrics entry with date "2025-01-01" and sleep duration 7.0 quality 3
    And a metrics entry with date "2025-01-02" and sleep duration 8.0 no quality
    When I call sleep_summary with no date filter
    Then the trend result field "data_points" equals int 2
    And the trend result field "quality_data_points" equals int 1
    And the trend result field "average_quality" equals float 3.0

  Scenario: sleep_summary no data returns all-None result
    When I call sleep_summary with no date filter
    Then the trend result field "data_points" equals int 0
    And the trend result field "average_duration_hours" is None
    And the trend result field "average_quality" is None

  # -----------------------------------------------------------------------
  # resting_hr_trend
  # -----------------------------------------------------------------------

  Scenario: resting_hr_trend multiple entries compute average and slope
    Given a metrics entry with date "2025-01-01" and resting_hr value 60
    And a metrics entry with date "2025-01-03" and resting_hr value 58
    And a metrics entry with date "2025-01-05" and resting_hr value 56
    When I call resting_hr_trend with no date filter
    Then the trend result field "data_points" equals int 3
    And the trend result field "unit" equals string "bpm"
    And the trend result field "average" equals float 58.0
    And the trend result field "slope" equals float -1.0

  Scenario: resting_hr_trend no data returns all-None result
    When I call resting_hr_trend with no date filter
    Then the trend result field "data_points" equals int 0
    And the trend result field "slope" is None
    And the trend result field "average" is None

  # -----------------------------------------------------------------------
  # Window parameter scenarios
  # -----------------------------------------------------------------------

  Scenario: days=60 default window excludes entries older than 60 days
    Given today is mocked to "2025-03-01"
    And a metrics entry with date "2025-03-01" and weight value 170.0 unit "lbs"
    And a metrics entry with date "2024-12-31" and weight value 185.0 unit "lbs"
    When I call weight_trend with days=60
    Then the trend result field "data_points" equals int 1
    And the trend result field "average" equals float 170.0

  Scenario: start_date and end_date override days parameter
    Given today is mocked to "2025-03-01"
    And a metrics entry with date "2025-01-05" and weight value 180.0 unit "lbs"
    And a metrics entry with date "2025-01-10" and weight value 178.0 unit "lbs"
    And a metrics entry with date "2025-02-01" and weight value 175.0 unit "lbs"
    When I call weight_trend with start_date "2025-01-01" and end_date "2025-01-31"
    Then the trend result field "data_points" equals int 2

  Scenario: start_date and end_date together bound both sides
    Given a metrics entry with date "2025-01-01" and weight value 185.0 unit "lbs"
    And a metrics entry with date "2025-01-15" and weight value 182.0 unit "lbs"
    And a metrics entry with date "2025-02-01" and weight value 178.0 unit "lbs"
    When I call weight_trend with start_date "2025-01-10" and end_date "2025-01-20"
    Then the trend result field "data_points" equals int 1
    And the trend result field "average" equals float 182.0
