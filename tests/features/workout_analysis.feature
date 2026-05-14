Feature: Workout analysis functions

  Background:
    Given a temporary vault directory
    And today is mocked to "2025-03-01"

  # -----------------------------------------------------------------------
  # frequency_by_body_area
  # -----------------------------------------------------------------------

  Scenario: Single exercise with body areas counts sets correctly
    Given an exercise YAML "push_up" with primary body areas "chest,triceps"
    And a workout entry on "2025-01-10" with exercise "push_up" and 3 sets
    When I call frequency_by_body_area
    Then the body area "chest" count equals 3
    And the body area "triceps" count equals 3

  Scenario: Multiple exercises counts across all exercises
    Given an exercise YAML "push_up" with primary body areas "chest,triceps"
    And an exercise YAML "pull_up" with primary body areas "back,biceps"
    And a workout entry on "2025-01-10" with exercise "push_up" and 3 sets
    And a workout entry on "2025-01-10" with exercise "pull_up" and 2 sets
    When I call frequency_by_body_area
    Then the body area "chest" count equals 3
    And the body area "back" count equals 2

  Scenario: Exercise with no body_areas in YAML is skipped gracefully
    Given an exercise YAML "mystery_move" with no body areas
    And a workout entry on "2025-01-10" with exercise "mystery_move" and 4 sets
    When I call frequency_by_body_area
    Then the body_areas dict is empty

  Scenario: No workouts returns empty body_areas dict
    Given an exercise YAML "push_up" with primary body areas "chest"
    When I call frequency_by_body_area
    Then the body_areas dict is empty

  Scenario: Window filtering excludes entries outside window
    Given an exercise YAML "push_up" with primary body areas "chest"
    And a workout entry on "2025-01-10" with exercise "push_up" and 3 sets
    And a workout entry on "2024-10-01" with exercise "push_up" and 5 sets
    When I call frequency_by_body_area with start_date "2025-01-01" and end_date "2025-01-31"
    Then the body area "chest" count equals 3

  # -----------------------------------------------------------------------
  # workout_streak
  # -----------------------------------------------------------------------

  Scenario: Consecutive days streak equals number of days
    Given a workout entry on "2025-01-13" with exercise "push_up" and 1 sets
    And a workout entry on "2025-01-14" with exercise "push_up" and 1 sets
    And a workout entry on "2025-01-15" with exercise "push_up" and 1 sets
    When I call workout_streak
    Then the streak result field "current_streak" equals 3
    And the streak result field "last_workout_date" equals "2025-01-15"
    And the streak result field "total_workout_days" equals 3

  Scenario: Gap breaks streak and streak resets at gap
    Given a workout entry on "2025-01-10" with exercise "push_up" and 1 sets
    And a workout entry on "2025-01-12" with exercise "push_up" and 1 sets
    And a workout entry on "2025-01-13" with exercise "push_up" and 1 sets
    When I call workout_streak
    Then the streak result field "current_streak" equals 2
    And the streak result field "total_workout_days" equals 3

  Scenario: Single workout day has streak of 1
    Given a workout entry on "2025-01-10" with exercise "push_up" and 1 sets
    When I call workout_streak
    Then the streak result field "current_streak" equals 1
    And the streak result field "last_workout_date" equals "2025-01-10"

  Scenario: No workouts returns streak of 0
    When I call workout_streak
    Then the streak result field "current_streak" equals 0
    And the streak result field "last_workout_date" is None
    And the streak result field "total_workout_days" equals 0

  Scenario: Window filtering only counts days within window for streak
    Given a workout entry on "2024-12-30" with exercise "push_up" and 1 sets
    And a workout entry on "2025-01-14" with exercise "push_up" and 1 sets
    And a workout entry on "2025-01-15" with exercise "push_up" and 1 sets
    When I call workout_streak with start_date "2025-01-01" and end_date "2025-01-31"
    Then the streak result field "current_streak" equals 2
    And the streak result field "total_workout_days" equals 2

  # -----------------------------------------------------------------------
  # personal_records
  # -----------------------------------------------------------------------

  Scenario: Weighted exercise PR is the highest weight times reps session
    Given a weighted workout on "2025-01-10" for exercise "bench_press" with weight 100 reps 5
    And a weighted workout on "2025-01-15" for exercise "bench_press" with weight 110 reps 5
    When I call personal_records for exercise "bench_press"
    Then the pr result field "pr_date" equals string "2025-01-15"
    And the pr result field "pr_total_work" equals float 550.0
    And the pr result field "sessions_analyzed" equals int 2

  Scenario: Bodyweight exercise PR is the highest reps session
    Given a bodyweight workout on "2025-01-10" for exercise "pull_up" with reps 8
    And a bodyweight workout on "2025-01-15" for exercise "pull_up" with reps 12
    When I call personal_records for exercise "pull_up"
    Then the pr result field "pr_date" equals string "2025-01-15"
    And the pr result field "pr_total_work" equals float 12.0
    And the pr result field "sessions_analyzed" equals int 2

  Scenario: PR is on a middle date when that session has the highest total work
    Given a weighted workout on "2025-01-10" for exercise "squat" with weight 80 reps 5
    And a weighted workout on "2025-01-17" for exercise "squat" with weight 100 reps 5
    And a weighted workout on "2025-01-24" for exercise "squat" with weight 90 reps 5
    When I call personal_records for exercise "squat"
    Then the pr result field "pr_date" equals string "2025-01-17"
    And the pr result field "pr_total_work" equals float 500.0

  Scenario: No sessions for exercise returns None pr_date
    When I call personal_records for exercise "nonexistent_exercise"
    Then the pr result field "pr_date" is None
    And the pr result field "pr_total_work" is None
    And the pr result field "pr_sets" is None
    And the pr result field "sessions_analyzed" equals int 0

  Scenario: sessions_analyzed count reflects only sessions with the target exercise
    Given a bodyweight workout on "2025-01-10" for exercise "push_up" with reps 10
    And a bodyweight workout on "2025-01-11" for exercise "push_up" with reps 12
    And a workout entry on "2025-01-12" with exercise "pull_up" and 3 sets
    When I call personal_records for exercise "push_up"
    Then the pr result field "sessions_analyzed" equals int 2

  # -----------------------------------------------------------------------
  # incomplete_session_rate
  # -----------------------------------------------------------------------

  Scenario: Always returns 0 incomplete and total_sessions reflects workout count
    Given a workout entry on "2025-01-10" with exercise "push_up" and 2 sets
    And a workout entry on "2025-01-11" with exercise "pull_up" and 3 sets
    When I call incomplete_session_rate
    Then the incomplete result field "total_sessions" equals int 2
    And the incomplete result field "incomplete_sessions" equals int 0
    And the incomplete result field "incomplete_rate" equals float 0.0
