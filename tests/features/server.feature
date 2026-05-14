Feature: fitlog HTTP server endpoints

  Scenario: GET /health returns 200 with status ok
    Given a fresh vault
    When I GET "/health"
    Then the response status is 200
    And the response JSON has "status" equal to "ok"

  Scenario: POST /v1/metrics/log with valid weight returns 200 and captured weight
    Given a fresh vault
    When I log weight 75.5 "kg" on date "2024-01-15"
    Then the response status is 200
    And the response JSON "captured" contains "weight"

  Scenario: POST /v1/metrics/log with invalid unit returns 400 or 422
    Given a fresh vault
    When I log weight 75.5 "stones" on date "2024-01-15"
    Then the response status is 400 or 422

  Scenario: POST /v1/metrics/log with no metrics returns 400 or 422
    Given a fresh vault
    When I POST metrics with only date "2024-01-15"
    Then the response status is 400 or 422

  Scenario: POST /v1/workouts/create-exercise creates exercise and returns 200
    Given a fresh vault
    When I create exercise "squat" named "Squat" with load_type "weighted"
    Then the response status is 200
    And the response JSON has "status" equal to "ok"

  Scenario: POST /v1/workouts/create-exercise with duplicate id returns 400
    Given a fresh vault
    And an exercise "pushup" with name "Push Up" and load_type "bodyweight" exists
    When I create exercise "pushup" named "Push Up" with load_type "bodyweight"
    Then the response status is 400

  Scenario: POST /v1/workouts/log-exercise with unknown exercise_id returns 400
    Given a fresh vault
    When I log exercise "unknown_exercise" on date "2024-01-15" with 1 bodyweight set of 10 reps
    Then the response status is 400

  Scenario: POST /v1/workouts/log-exercise with known exercise returns 200
    Given a fresh vault
    And an exercise "pullup" with name "Pull Up" and load_type "bodyweight" exists
    When I log exercise "pullup" on date "2024-01-15" with 1 bodyweight set of 8 reps
    Then the response status is 200
    And the response JSON has "status" equal to "ok"

  Scenario: GET /v1/analysis/metrics/weight-trend with no data returns 200 with data_points 0
    Given a fresh vault
    When I GET "/v1/analysis/metrics/weight-trend"
    Then the response status is 200
    And the response JSON has "data_points" equal to 0

  Scenario: GET /v1/analysis/metrics/weight-trend with days query param works
    Given a fresh vault
    When I GET "/v1/analysis/metrics/weight-trend?days=30"
    Then the response status is 200
    And the response JSON has "data_points" equal to 0

  Scenario: GET /v1/analysis/workouts/streak with no data returns 200 with current_streak 0
    Given a fresh vault
    When I GET "/v1/analysis/workouts/streak"
    Then the response status is 200
    And the response JSON has "current_streak" equal to 0

  Scenario: GET /v1/analysis/workouts/personal-records with no data returns sessions_analyzed 0
    Given a fresh vault
    When I GET "/v1/analysis/workouts/personal-records/squat"
    Then the response status is 200
    And the response JSON has "sessions_analyzed" equal to 0
