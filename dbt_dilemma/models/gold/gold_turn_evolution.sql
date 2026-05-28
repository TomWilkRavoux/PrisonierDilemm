with turns as (
    select * from {{ ref('stg_turns') }}
),

unpivoted as (
    select
        run_id,
        match_id,
        turn_number,
        strategy_a as strategy,
        choice_a as choice,
        cooperated_a as cooperated,
        score_a as score,
        cumulative_score_a as cumulative_score
    from turns

    union all

    select
        run_id,
        match_id,
        turn_number,
        strategy_b as strategy,
        choice_b as choice,
        cooperated_b as cooperated,
        score_b as score,
        cumulative_score_b as cumulative_score
    from turns
)

select
    run_id,
    match_id,
    turn_number,
    strategy,
    choice,
    score,
    cumulative_score,
    cooperated,
    round(avg(cooperated) over (
        partition by run_id, match_id, strategy
        order by turn_number
        rows between 49 preceding and current row
    ), 3) as rolling_coop_rate_50,
    lag(choice, 1) over (
        partition by run_id, match_id, strategy order by turn_number
    ) as prev_choice_1,
    lag(choice, 2) over (
        partition by run_id, match_id, strategy order by turn_number
    ) as prev_choice_2,
    lag(choice, 3) over (
        partition by run_id, match_id, strategy order by turn_number
    ) as prev_choice_3
from unpivoted
