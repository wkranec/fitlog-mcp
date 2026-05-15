Feature: Goals system

  Background:
    Given a temporary vault directory
    And today is mocked to "2025-05-13"

  # -------------------------------------------------------------------------
  # list_goals
  # -------------------------------------------------------------------------

  Scenario: Returns all goals when goals.yaml exists
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
        weekly_workouts:
          description: "Work out 4 days per week"
          type: frequency
          exercise_ids: []
          period: week
          operator: ">="
          target: 4
      """
    When I call list_goals
    Then the goals list has 2 entries
    And the goals list contains goal_id "daily_sleep" with type "metric"
    And the goals list contains goal_id "weekly_workouts" with type "frequency"

  Scenario: Returns empty list when goals.yaml is absent
    When I call list_goals
    Then the goals list has 0 entries

  # -------------------------------------------------------------------------
  # check_goal_status — metric goal
  # -------------------------------------------------------------------------

  Scenario: Metric goal met today returns met=True and correct value
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-13" and sleep duration 8.5 no quality
    When I call check_goal_status for goal "daily_sleep"
    Then the status field "met" is True
    And the status field "value" equals float 8.5
    And the status field "streak" equals int 1

  Scenario: Metric goal not met today returns met=False
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-13" and sleep duration 7.0 no quality
    When I call check_goal_status for goal "daily_sleep"
    Then the status field "met" is False
    And the status field "streak" equals int 0

  Scenario: No data for as_of_date returns met=None
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    When I call check_goal_status for goal "daily_sleep"
    Then the status field "met" is None
    And the status field "value" is None

  Scenario: Streak of 3 consecutive met days
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-11" and sleep duration 8.5 no quality
    And a metrics entry with date "2025-05-12" and sleep duration 9.0 no quality
    And a metrics entry with date "2025-05-13" and sleep duration 8.2 no quality
    When I call check_goal_status for goal "daily_sleep"
    Then the status field "streak" equals int 3

  Scenario: Streak breaks on a not-met day
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-11" and sleep duration 8.5 no quality
    And a metrics entry with date "2025-05-12" and sleep duration 6.0 no quality
    And a metrics entry with date "2025-05-13" and sleep duration 8.2 no quality
    When I call check_goal_status for goal "daily_sleep"
    Then the status field "streak" equals int 1

  Scenario: No-data days are transparent to streak
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-10" and sleep duration 8.5 no quality
    And a metrics entry with date "2025-05-13" and sleep duration 8.2 no quality
    When I call check_goal_status for goal "daily_sleep"
    Then the status field "streak" equals int 2

  Scenario: pct_met_last_30_days reflects only days with data
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-11" and sleep duration 8.5 no quality
    And a metrics entry with date "2025-05-12" and sleep duration 6.0 no quality
    And a metrics entry with date "2025-05-13" and sleep duration 8.2 no quality
    When I call check_goal_status for goal "daily_sleep"
    Then the status field "days_with_data" equals int 3
    And the status pct_met_last_30_days is approximately 0.6667

  # -------------------------------------------------------------------------
  # check_goal_status — activity goal
  # -------------------------------------------------------------------------

  Scenario: Activity goal duration meets target returns met=True
    Given a goals.yaml with content:
      """
      goals:
        daily_meditation:
          description: "Meditate 12 minutes"
          type: activity
          exercise_ids:
            - meditation
          target_minutes: 12.0
          operator: ">="
      """
    And a timed workout on "2025-05-13" for exercise "meditation" with duration 720 seconds
    When I call check_goal_status for goal "daily_meditation"
    Then the status field "met" is True
    And the status field "value" equals float 12.0

  Scenario: Activity goal duration below target returns met=False
    Given a goals.yaml with content:
      """
      goals:
        daily_meditation:
          description: "Meditate 12 minutes"
          type: activity
          exercise_ids:
            - meditation
          target_minutes: 12.0
          operator: ">="
      """
    And a timed workout on "2025-05-13" for exercise "meditation" with duration 300 seconds
    When I call check_goal_status for goal "daily_meditation"
    Then the status field "met" is False

  Scenario: Activity goal exercise_ids filter counts only matching exercises
    Given a goals.yaml with content:
      """
      goals:
        daily_meditation:
          description: "Meditate 12 minutes"
          type: activity
          exercise_ids:
            - meditation
          target_minutes: 12.0
          operator: ">="
      """
    And a timed workout on "2025-05-13" for exercise "box_breathing" with duration 900 seconds
    When I call check_goal_status for goal "daily_meditation"
    Then the status field "met" is None

  Scenario: Activity goal with empty exercise_ids counts all exercises
    Given a goals.yaml with content:
      """
      goals:
        daily_breathwork:
          description: "Any 10 minutes of breathwork"
          type: activity
          exercise_ids: []
          target_minutes: 10.0
          operator: ">="
      """
    And a timed workout on "2025-05-13" for exercise "box_breathing" with duration 900 seconds
    When I call check_goal_status for goal "daily_breathwork"
    Then the status field "met" is True

  # -------------------------------------------------------------------------
  # check_goal_status — frequency goal
  # -------------------------------------------------------------------------

  Scenario: Current week partially done reflects current progress
    Given a goals.yaml with content:
      """
      goals:
        weekly_workouts:
          description: "Work out 4 days per week"
          type: frequency
          exercise_ids: []
          period: week
          operator: ">="
          target: 4
      """
    And a workout entry on "2025-05-12" with exercise "push_up" and 3 sets
    And a workout entry on "2025-05-13" with exercise "push_up" and 3 sets
    When I call check_goal_status for goal "weekly_workouts"
    Then the status field "met" is False
    And the status field "value" equals int 2
    And the status field "period_start" equals "2025-05-12"
    And the status field "period_end" equals "2025-05-18"

  Scenario: Current week target met returns met=True
    Given a goals.yaml with content:
      """
      goals:
        weekly_workouts:
          description: "Work out 2 days per week"
          type: frequency
          exercise_ids: []
          period: week
          operator: ">="
          target: 2
      """
    And a workout entry on "2025-05-12" with exercise "push_up" and 1 sets
    And a workout entry on "2025-05-13" with exercise "push_up" and 1 sets
    When I call check_goal_status for goal "weekly_workouts"
    Then the status field "met" is True

  Scenario: Frequency streak counts consecutive complete weeks met
    Given a goals.yaml with content:
      """
      goals:
        weekly_workouts:
          description: "Work out 3 days per week"
          type: frequency
          exercise_ids: []
          period: week
          operator: ">="
          target: 3
      """
    And a workout entry on "2025-04-28" with exercise "push_up" and 1 sets
    And a workout entry on "2025-04-29" with exercise "push_up" and 1 sets
    And a workout entry on "2025-04-30" with exercise "push_up" and 1 sets
    And a workout entry on "2025-05-05" with exercise "push_up" and 1 sets
    And a workout entry on "2025-05-06" with exercise "push_up" and 1 sets
    And a workout entry on "2025-05-07" with exercise "push_up" and 1 sets
    When I call check_goal_status for goal "weekly_workouts"
    Then the status field "streak" equals int 2

  # -------------------------------------------------------------------------
  # check_goal_status — error cases
  # -------------------------------------------------------------------------

  Scenario: Goal not in goals.yaml raises KeyError
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    When I call check_goal_status for goal "nonexistent_goal" expecting error
    Then a KeyError is raised

  # -------------------------------------------------------------------------
  # get_goal_history — metric goal
  # -------------------------------------------------------------------------

  Scenario: Metric goal history contains only dates with data in ascending order
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-11" and sleep duration 8.5 no quality
    And a metrics entry with date "2025-05-12" and sleep duration 7.0 no quality
    When I call get_goal_history for goal "daily_sleep" with days 30
    Then the history has 2 entries
    And the history entry 0 has date "2025-05-11" and met True
    And the history entry 1 has date "2025-05-12" and met False

  Scenario: Activity goal history shows daily duration values
    Given a goals.yaml with content:
      """
      goals:
        daily_meditation:
          description: "Meditate 12 minutes"
          type: activity
          exercise_ids:
            - meditation
          target_minutes: 12.0
          operator: ">="
      """
    And a timed workout on "2025-05-12" for exercise "meditation" with duration 900 seconds
    And a timed workout on "2025-05-13" for exercise "meditation" with duration 600 seconds
    When I call get_goal_history for goal "daily_meditation" with days 30
    Then the history has 2 entries
    And the history entry 0 has date "2025-05-12" and met True
    And the history entry 1 has date "2025-05-13" and met False

  Scenario: Frequency goal history shows periods with met/value/complete
    Given a goals.yaml with content:
      """
      goals:
        weekly_workouts:
          description: "Work out 3 days per week"
          type: frequency
          exercise_ids: []
          period: week
          operator: ">="
          target: 3
      """
    And a workout entry on "2025-05-05" with exercise "push_up" and 1 sets
    And a workout entry on "2025-05-06" with exercise "push_up" and 1 sets
    And a workout entry on "2025-05-07" with exercise "push_up" and 1 sets
    When I call get_goal_history for goal "weekly_workouts" with days 14
    Then the frequency history contains a complete period "2025-W19" with met True

  Scenario: Dates with no data are excluded from history
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-13" and sleep duration 8.5 no quality
    When I call get_goal_history for goal "daily_sleep" with days 30
    Then the history has 1 entries
    And the history entry 0 has date "2025-05-13" and met True

  Scenario: History respects start_date and end_date window
    Given a goals.yaml with content:
      """
      goals:
        daily_sleep:
          description: "Sleep at least 8 hours"
          type: metric
          metric: sleep
          field: duration_hours
          operator: ">="
          target: 8.0
      """
    And a metrics entry with date "2025-05-10" and sleep duration 8.5 no quality
    And a metrics entry with date "2025-05-11" and sleep duration 8.5 no quality
    And a metrics entry with date "2025-05-12" and sleep duration 8.5 no quality
    When I call get_goal_history for goal "daily_sleep" with start_date "2025-05-11" and end_date "2025-05-12"
    Then the history has 2 entries
    And the history entry 0 has date "2025-05-11" and met True
    And the history entry 1 has date "2025-05-12" and met True
