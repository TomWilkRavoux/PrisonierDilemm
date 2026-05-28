with matches as (
    select * from {{ ref('gold_match_summary') }}
),

directional as (
    select
        run_id,
        strategy_a as strategy,
        strategy_b as opponent,
        total_score_a as score,
        total_score_b as opponent_score,
        coop_rate_a as coop_rate,
        case
            when total_score_a > total_score_b then 'win'
            when total_score_a = total_score_b then 'draw'
            else 'loss'
        end as result
    from matches

    union all

    select
        run_id,
        strategy_b as strategy,
        strategy_a as opponent,
        total_score_b as score,
        total_score_a as opponent_score,
        coop_rate_b as coop_rate,
        case
            when total_score_b > total_score_a then 'win'
            when total_score_b = total_score_a then 'draw'
            else 'loss'
        end as result
    from matches
)

select
    run_id,
    strategy,
    opponent,
    score,
    opponent_score,
    score - opponent_score as score_diff,
    coop_rate,
    result
from directional
