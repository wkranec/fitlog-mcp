Feature: JSONL log reads and writes

  # ---------------------------------------------------------------------------
  # append_entry
  # ---------------------------------------------------------------------------

  Scenario: append_entry creates the log file and parent directories on first write
    Given a temporary vault directory
    When I append a metrics entry with date "2025-01-15" and weight 80.5
    Then the file "logs/metrics/2025.jsonl" exists in the vault
    And the file "logs/metrics/2025.jsonl" contains 1 line

  Scenario: append_entry writes valid JSON on each line
    Given a temporary vault directory
    When I append a metrics entry with date "2025-03-10" and weight 75.0
    Then line 1 of "logs/metrics/2025.jsonl" is valid JSON containing date "2025-03-10"

  Scenario: append_entry appends successive entries as separate lines
    Given a temporary vault directory
    When I append a metrics entry with date "2025-04-01" and weight 70.0
    And I append a metrics entry with date "2025-04-02" and weight 70.5
    Then the file "logs/metrics/2025.jsonl" contains 2 lines

  Scenario: append_entry routes to the correct annual file based on the entry date
    Given a temporary vault directory
    When I append a metrics entry with date "2024-12-31" and weight 85.0
    And I append a metrics entry with date "2025-01-01" and weight 84.5
    Then the file "logs/metrics/2024.jsonl" exists in the vault
    And the file "logs/metrics/2024.jsonl" contains 1 line
    And the file "logs/metrics/2025.jsonl" exists in the vault
    And the file "logs/metrics/2025.jsonl" contains 1 line

  Scenario: append_entry works for the workouts log type
    Given a temporary vault directory
    When I append a workouts entry with date "2025-06-01" id "abc123" and exercise "squat"
    Then the file "logs/workouts/2025.jsonl" exists in the vault
    And the file "logs/workouts/2025.jsonl" contains 1 line

  # ---------------------------------------------------------------------------
  # read_merged — metrics, single entry
  # ---------------------------------------------------------------------------

  Scenario: read_merged returns a single metrics entry indexed by date
    Given a temporary vault directory
    And a metrics log entry date "2025-01-10" weight 80.0
    When I call read_merged for "metrics" with no filter
    Then the result contains key "2025-01-10"
    And result key "2025-01-10" field "weight_kg" equals float 80.0

  # ---------------------------------------------------------------------------
  # read_merged — metrics, same-date deep merge
  # ---------------------------------------------------------------------------

  Scenario: read_merged deep-merges metrics entries for the same date — later scalar wins
    Given a temporary vault directory
    And a metrics log entry date "2025-02-01" weight 80.0 notes "morning"
    And a metrics log entry date "2025-02-01" weight 80.2
    When I call read_merged for "metrics" with no filter
    Then the result contains key "2025-02-01"
    And result key "2025-02-01" field "weight_kg" equals float 80.2
    And result key "2025-02-01" field "notes" equals string "morning"

  Scenario: read_merged concatenates list fields when merging metrics entries for the same date
    Given a temporary vault directory
    And a metrics log entry date "2025-02-05" tags "cardio"
    And a metrics log entry date "2025-02-05" tags "strength"
    When I call read_merged for "metrics" with no filter
    Then the result contains key "2025-02-05"
    And result key "2025-02-05" field "tags" is list ["cardio", "strength"]

  # ---------------------------------------------------------------------------
  # read_merged — metrics, multiple dates
  # ---------------------------------------------------------------------------

  Scenario: read_merged returns entries for multiple different dates
    Given a temporary vault directory
    And a metrics log entry date "2025-03-01" weight 79.0
    And a metrics log entry date "2025-03-02" weight 78.5
    When I call read_merged for "metrics" with no filter
    Then the result contains key "2025-03-01"
    And the result contains key "2025-03-02"
    And result key "2025-03-01" field "weight_kg" equals float 79.0
    And result key "2025-03-02" field "weight_kg" equals float 78.5

  # ---------------------------------------------------------------------------
  # read_merged — metrics, date filtering with days=N
  # ---------------------------------------------------------------------------

  Scenario: read_merged with days=7 returns only entries within the last 7 days
    Given a temporary vault directory
    And today is mocked to "2025-05-10"
    And a metrics log entry date "2025-05-04" weight 77.0
    And a metrics log entry date "2025-05-10" weight 76.5
    And a metrics log entry date "2025-04-01" weight 90.0
    When I call read_merged for "metrics" with days=7
    Then the result contains key "2025-05-04"
    And the result contains key "2025-05-10"
    And the result does not contain key "2025-04-01"

  Scenario: read_merged with days=1 returns only today's entry
    Given a temporary vault directory
    And today is mocked to "2025-05-10"
    And a metrics log entry date "2025-05-09" weight 77.0
    And a metrics log entry date "2025-05-10" weight 76.5
    When I call read_merged for "metrics" with days=1
    Then the result contains key "2025-05-10"
    And the result does not contain key "2025-05-09"

  # ---------------------------------------------------------------------------
  # read_merged — metrics, start_date/end_date range
  # ---------------------------------------------------------------------------

  Scenario: read_merged with start_date and end_date returns entries in inclusive range
    Given a temporary vault directory
    And a metrics log entry date "2025-06-01" weight 75.0
    And a metrics log entry date "2025-06-05" weight 74.5
    And a metrics log entry date "2025-06-10" weight 74.0
    When I call read_merged for "metrics" with start_date "2025-06-01" and end_date "2025-06-05"
    Then the result contains key "2025-06-01"
    And the result contains key "2025-06-05"
    And the result does not contain key "2025-06-10"

  Scenario: read_merged with only start_date returns entries from that date onward
    Given a temporary vault directory
    And a metrics log entry date "2025-07-01" weight 73.0
    And a metrics log entry date "2025-07-15" weight 72.5
    When I call read_merged for "metrics" with start_date "2025-07-10" and no end_date
    Then the result does not contain key "2025-07-01"
    And the result contains key "2025-07-15"

  Scenario: read_merged with only end_date returns entries up to that date
    Given a temporary vault directory
    And a metrics log entry date "2025-08-01" weight 72.0
    And a metrics log entry date "2025-08-20" weight 71.0
    When I call read_merged for "metrics" with no start_date and end_date "2025-08-10"
    Then the result contains key "2025-08-01"
    And the result does not contain key "2025-08-20"

  # ---------------------------------------------------------------------------
  # read_merged — year boundary crossing
  # ---------------------------------------------------------------------------

  Scenario: read_merged with days spanning a year boundary reads both annual files
    Given a temporary vault directory
    And today is mocked to "2025-01-03"
    And a metrics log entry date "2024-12-31" weight 85.0
    And a metrics log entry date "2025-01-03" weight 84.0
    When I call read_merged for "metrics" with days=7
    Then the result contains key "2024-12-31"
    And the result contains key "2025-01-03"

  Scenario: read_merged with years list reads those files without date filtering
    Given a temporary vault directory
    And a metrics log entry date "2024-06-15" weight 88.0
    And a metrics log entry date "2025-06-15" weight 82.0
    When I call read_merged for "metrics" with years 2024 and 2025
    Then the result contains key "2024-06-15"
    And the result contains key "2025-06-15"

  # ---------------------------------------------------------------------------
  # read_merged — empty vault
  # ---------------------------------------------------------------------------

  Scenario: read_merged returns an empty dict when no log files exist
    Given a temporary vault directory
    When I call read_merged for "metrics" with no filter
    Then the result is an empty dict

  Scenario: read_merged returns an empty dict when no entries match the filter
    Given a temporary vault directory
    And a metrics log entry date "2025-01-01" weight 80.0
    When I call read_merged for "metrics" with start_date "2025-06-01" and end_date "2025-06-30"
    Then the result is an empty dict

  # ---------------------------------------------------------------------------
  # read_merged — workouts, single workout
  # ---------------------------------------------------------------------------

  Scenario: read_merged for workouts returns list of workouts indexed by date
    Given a temporary vault directory
    And a workouts log entry date "2025-01-20" id "w001" exercise "squat" sets 3
    When I call read_merged for "workouts" with no filter
    Then the result contains key "2025-01-20"
    And result key "2025-01-20" is a list with 1 item
    And workout 0 on "2025-01-20" field "exercise" equals string "squat"

  # ---------------------------------------------------------------------------
  # read_merged — workouts, multiple workouts same date different ids
  # ---------------------------------------------------------------------------

  Scenario: read_merged for workouts groups multiple different-id workouts on same date
    Given a temporary vault directory
    And a workouts log entry date "2025-02-10" id "w001" exercise "squat" sets 3
    And a workouts log entry date "2025-02-10" id "w002" exercise "deadlift" sets 1
    When I call read_merged for "workouts" with no filter
    Then the result contains key "2025-02-10"
    And result key "2025-02-10" is a list with 2 items

  # ---------------------------------------------------------------------------
  # read_merged — workouts, same id same date merge
  # ---------------------------------------------------------------------------

  Scenario: read_merged merges workout entries with the same id and date — later scalar wins
    Given a temporary vault directory
    And a workouts log entry date "2025-03-01" id "w001" exercise "press" sets 3
    And a workouts log entry date "2025-03-01" id "w001" sets 4 notes "pb"
    When I call read_merged for "workouts" with no filter
    Then the result contains key "2025-03-01"
    And result key "2025-03-01" is a list with 1 item
    And workout 0 on "2025-03-01" field "sets" equals int 4
    And workout 0 on "2025-03-01" field "notes" equals string "pb"
    And workout 0 on "2025-03-01" field "exercise" equals string "press"

  Scenario: read_merged concatenates list fields when merging workout entries with same id
    Given a temporary vault directory
    And a workouts log entry date "2025-03-05" id "w001" exercise "curl" reps "10,8"
    And a workouts log entry date "2025-03-05" id "w001" reps "6"
    When I call read_merged for "workouts" with no filter
    Then the result contains key "2025-03-05"
    And workout 0 on "2025-03-05" reps equals [10, 8, 6]

  # ---------------------------------------------------------------------------
  # read_merged — workouts, multiple dates
  # ---------------------------------------------------------------------------

  Scenario: read_merged for workouts returns entries for multiple different dates
    Given a temporary vault directory
    And a workouts log entry date "2025-04-01" id "w001" exercise "squat" sets 1
    And a workouts log entry date "2025-04-03" id "w002" exercise "bench" sets 1
    When I call read_merged for "workouts" with no filter
    Then the result contains key "2025-04-01"
    And the result contains key "2025-04-03"

  # ---------------------------------------------------------------------------
  # read_merged_list — metrics
  # ---------------------------------------------------------------------------

  Scenario: read_merged_list for metrics returns a flat list sorted by date ascending
    Given a temporary vault directory
    And a metrics log entry date "2025-09-03" weight 70.0
    And a metrics log entry date "2025-09-01" weight 71.0
    And a metrics log entry date "2025-09-02" weight 70.5
    When I call read_merged_list for "metrics" with no filter
    Then the list result has 3 items
    And list item 0 has date "2025-09-01"
    And list item 1 has date "2025-09-02"
    And list item 2 has date "2025-09-03"

  Scenario: read_merged_list for metrics each item includes a date field
    Given a temporary vault directory
    And a metrics log entry date "2025-10-01" weight 69.0
    When I call read_merged_list for "metrics" with no filter
    Then the list result has 1 items
    And list item 0 has date "2025-10-01"

  # ---------------------------------------------------------------------------
  # read_merged_list — workouts
  # ---------------------------------------------------------------------------

  Scenario: read_merged_list for workouts returns flat list sorted by date
    Given a temporary vault directory
    And a workouts log entry date "2025-11-01" id "w001" exercise "squat" sets 1
    And a workouts log entry date "2025-11-01" id "w002" exercise "bench" sets 1
    And a workouts log entry date "2025-11-03" id "w003" exercise "deadlift" sets 1
    When I call read_merged_list for "workouts" with no filter
    Then the list result has 3 items
    And list item 0 has date "2025-11-01"
    And list item 2 has date "2025-11-03"

  Scenario: read_merged_list returns empty list when no log files exist
    Given a temporary vault directory
    When I call read_merged_list for "metrics" with no filter
    Then the list result has 0 items

  # ---------------------------------------------------------------------------
  # read_merged_list — with date filter
  # ---------------------------------------------------------------------------

  Scenario: read_merged_list respects start_date and end_date filters
    Given a temporary vault directory
    And a metrics log entry date "2025-12-01" weight 68.0
    And a metrics log entry date "2025-12-15" weight 67.5
    And a metrics log entry date "2025-12-31" weight 67.0
    When I call read_merged_list for "metrics" with start_date "2025-12-01" and end_date "2025-12-15"
    Then the list result has 2 items
    And list item 0 has date "2025-12-01"
    And list item 1 has date "2025-12-15"
