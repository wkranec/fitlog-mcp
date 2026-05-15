Feature: Workout logging tool

  # ---------------------------------------------------------------------------
  # log_exercise — 1. Log a bodyweight exercise
  # ---------------------------------------------------------------------------

  Scenario: Log a bodyweight exercise (ring_rows)
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "ring_rows" and sets [{"reps": 10}, {"reps": 8}]
    Then the result status is "ok"
    And the result exercise_id is "ring_rows"
    And the result sets_logged is 2
    And the file "logs/workouts/2025.jsonl" exists in the vault

  # ---------------------------------------------------------------------------
  # log_exercise — 2. Log a weighted exercise
  # ---------------------------------------------------------------------------

  Scenario: Log a weighted exercise (barbell_press)
    Given a temporary vault directory
    And an exercise "barbell_press" with name "Barbell Press" and load_type "weighted" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "barbell_press" and sets [{"reps": 5, "weight": 135.0, "weight_unit": "lbs"}]
    Then the result status is "ok"
    And the result exercise_id is "barbell_press"
    And the result sets_logged is 1

  # ---------------------------------------------------------------------------
  # log_exercise — 3. Log a timed exercise
  # ---------------------------------------------------------------------------

  Scenario: Log a timed exercise
    Given a temporary vault directory
    And an exercise "plank" with name "Plank" and load_type "timed" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "plank" and sets [{"duration_seconds": 60.0}, {"duration_seconds": 45.0}]
    Then the result status is "ok"
    And the result sets_logged is 2

  # ---------------------------------------------------------------------------
  # log_exercise — 4. Log exercise with notes and raw_input
  # ---------------------------------------------------------------------------

  Scenario: Log exercise with notes and raw_input
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "ring_rows" sets [{"reps": 10}] notes "felt strong" raw_input "ring rows 10"
    Then the result status is "ok"
    And the written workout entry has notes "felt strong" and raw_input "ring rows 10"

  # ---------------------------------------------------------------------------
  # log_exercise — 5. Log exercise without notes — no null notes field
  # ---------------------------------------------------------------------------

  Scenario: Log exercise without notes has no null fields
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "ring_rows" and sets [{"reps": 10}, {"reps": 8}]
    Then the written workout entry has no null fields

  # ---------------------------------------------------------------------------
  # log_exercise — 6. Two exercises on same day — same workout ID
  # ---------------------------------------------------------------------------

  Scenario: Two exercises on same day share the same workout ID
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    And an exercise "plank" with name "Plank" and load_type "timed" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "ring_rows" and sets [{"reps": 10}]
    And I call log_exercise with date "2025-05-13" exercise "plank" and sets [{"duration_seconds": 60.0}]
    Then the file "logs/workouts/2025.jsonl" contains 2 lines
    And both written entries have the same workout id "wo-20250513"

  # ---------------------------------------------------------------------------
  # log_exercise — 7. Exercise not found → error mentions create_exercise
  # ---------------------------------------------------------------------------

  Scenario: Exercise not found raises error mentioning create_exercise
    Given a temporary vault directory
    When I call log_exercise with date "2025-05-13" exercise "unknown_move" and sets [{"reps": 5}]
    Then a workout error is raised
    And the error message mentions "create_exercise"

  # ---------------------------------------------------------------------------
  # log_exercise — 8. Invalid date → rejected
  # ---------------------------------------------------------------------------

  Scenario: Invalid date is rejected
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call log_exercise with date "not-a-date" exercise "ring_rows" and sets [{"reps": 10}]
    Then a workout error is raised
    And no workout file is written

  # ---------------------------------------------------------------------------
  # log_exercise — 9. Empty sets list → rejected
  # ---------------------------------------------------------------------------

  Scenario: Empty sets list is rejected
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "ring_rows" and sets []
    Then a workout error is raised
    And no workout file is written

  # ---------------------------------------------------------------------------
  # log_exercise — 10. Bodyweight set with extra weight field → rejected
  # ---------------------------------------------------------------------------

  Scenario: Bodyweight set with extra weight field is rejected
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "ring_rows" and sets [{"reps": 10, "weight": 20.0}]
    Then a workout error is raised
    And no workout file is written

  # ---------------------------------------------------------------------------
  # log_exercise — 11. Weighted set missing weight → rejected
  # ---------------------------------------------------------------------------

  Scenario: Weighted set missing weight field is rejected
    Given a temporary vault directory
    And an exercise "barbell_press" with name "Barbell Press" and load_type "weighted" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "barbell_press" and sets [{"reps": 5}]
    Then a workout error is raised
    And no workout file is written

  # ---------------------------------------------------------------------------
  # log_exercise — 12. Timed set with reps instead of duration_seconds → rejected
  # ---------------------------------------------------------------------------

  Scenario: Timed set with reps instead of duration_seconds is rejected
    Given a temporary vault directory
    And an exercise "plank" with name "Plank" and load_type "timed" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "plank" and sets [{"reps": 10}]
    Then a workout error is raised
    And no workout file is written

  # ---------------------------------------------------------------------------
  # log_exercise — 13. Negative reps → rejected
  # ---------------------------------------------------------------------------

  Scenario: Negative reps value is rejected
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "ring_rows" and sets [{"reps": -5}]
    Then a workout error is raised
    And no workout file is written

  # ---------------------------------------------------------------------------
  # log_exercise — 14. sets_logged count is correct
  # ---------------------------------------------------------------------------

  Scenario: sets_logged count matches number of sets provided
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "ring_rows" and sets [{"reps": 10}, {"reps": 9}, {"reps": 8}]
    Then the result sets_logged is 3

  # ---------------------------------------------------------------------------
  # create_exercise — 15. Create a bodyweight exercise
  # ---------------------------------------------------------------------------

  Scenario: Create a bodyweight exercise
    Given a temporary vault directory
    When I call create_exercise with id "ring_rows" name "Ring Rows" load_type "bodyweight"
    Then the result status is "ok"
    And the exercise file "exercises/ring_rows.yaml" exists in the vault
    And the exercise file contains load_type "bodyweight"

  # ---------------------------------------------------------------------------
  # create_exercise — 16. Create a weighted exercise
  # ---------------------------------------------------------------------------

  Scenario: Create a weighted exercise
    Given a temporary vault directory
    When I call create_exercise with id "barbell_press" name "Barbell Press" load_type "weighted"
    Then the result status is "ok"
    And the exercise file "exercises/barbell_press.yaml" exists in the vault
    And the exercise file contains load_type "weighted"

  # ---------------------------------------------------------------------------
  # create_exercise — 17. Create a timed exercise
  # ---------------------------------------------------------------------------

  Scenario: Create a timed exercise
    Given a temporary vault directory
    When I call create_exercise with id "plank" name "Plank" load_type "timed"
    Then the result status is "ok"
    And the exercise file "exercises/plank.yaml" exists in the vault
    And the exercise file contains load_type "timed"

  # ---------------------------------------------------------------------------
  # create_exercise — 18. Duplicate exercise_id → error
  # ---------------------------------------------------------------------------

  Scenario: Duplicate exercise_id raises error
    Given a temporary vault directory
    And an exercise "ring_rows" with name "Ring Rows" and load_type "bodyweight" exists in the vault
    When I call create_exercise with id "ring_rows" name "Ring Rows Again" load_type "bodyweight"
    Then a workout error is raised
    And the error message mentions "already exists"

  # ---------------------------------------------------------------------------
  # create_exercise — 19. Invalid load_type → error
  # ---------------------------------------------------------------------------

  Scenario: Invalid load_type raises error
    Given a temporary vault directory
    When I call create_exercise with id "some_exercise" name "Some Exercise" load_type "invalid_type"
    Then a workout error is raised

  # ---------------------------------------------------------------------------
  # create_exercise — 20. Invalid exercise_id (contains space or hyphen) → error
  # ---------------------------------------------------------------------------

  Scenario: Exercise id with space is rejected
    Given a temporary vault directory
    When I call create_exercise with id "ring rows" name "Ring Rows" load_type "bodyweight"
    Then a workout error is raised

  Scenario: Exercise id with hyphen is rejected
    Given a temporary vault directory
    When I call create_exercise with id "ring-rows" name "Ring Rows" load_type "bodyweight"
    Then a workout error is raised

  # ---------------------------------------------------------------------------
  # breathwork — 22. Log a breathwork exercise
  # ---------------------------------------------------------------------------

  Scenario: Log a breathwork exercise
    Given a temporary vault directory
    And an exercise "box_breathing" with name "Box Breathing" and load_type "breathwork" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "box_breathing" and sets [{"duration_seconds": 300.0}]
    Then the result status is "ok"
    And the result exercise_id is "box_breathing"
    And the result sets_logged is 1

  # ---------------------------------------------------------------------------
  # breathwork — 23. Create a breathwork exercise
  # ---------------------------------------------------------------------------

  Scenario: Create a breathwork exercise
    Given a temporary vault directory
    When I call create_exercise with id "box_breathing" name "Box Breathing" load_type "breathwork"
    Then the result status is "ok"
    And the exercise file "exercises/box_breathing.yaml" exists in the vault
    And the exercise file contains load_type "breathwork"

  # ---------------------------------------------------------------------------
  # breathwork — 24. Breathwork set with reps field → rejected
  # ---------------------------------------------------------------------------

  Scenario: Breathwork set with reps field is rejected
    Given a temporary vault directory
    And an exercise "box_breathing" with name "Box Breathing" and load_type "breathwork" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "box_breathing" and sets [{"reps": 10}]
    Then a workout error is raised
    And no workout file is written

  # ---------------------------------------------------------------------------
  # breathwork — 25. Breathwork set with weight field → rejected
  # ---------------------------------------------------------------------------

  Scenario: Breathwork set with weight field is rejected
    Given a temporary vault directory
    And an exercise "box_breathing" with name "Box Breathing" and load_type "breathwork" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "box_breathing" and sets [{"duration_seconds": 60.0, "weight": 10.0}]
    Then a workout error is raised
    And no workout file is written

  # ---------------------------------------------------------------------------
  # breathwork — 26. Breathwork set with negative duration_seconds → rejected
  # ---------------------------------------------------------------------------

  Scenario: Breathwork set with negative duration_seconds is rejected
    Given a temporary vault directory
    And an exercise "box_breathing" with name "Box Breathing" and load_type "breathwork" exists in the vault
    When I call log_exercise with date "2025-05-13" exercise "box_breathing" and sets [{"duration_seconds": -30.0}]
    Then a workout error is raised
    And no workout file is written
