with raw as (
    select * from {{ source('silver', 'turns') }}
)

select
    run_id,
    match_id,
    turn_number,
    player_a,
    player_b,
    strategy_a,
    strategy_b,
    choice_a,
    choice_b,
    score_a,
    score_b,
    cumulative_score_a,
    cumulative_score_b,
    reasoning_a,
    reasoning_b,
    case when choice_a = 'C' then 1 else 0 end as cooperated_a,
    case when choice_b = 'C' then 1 else 0 end as cooperated_b,
    case when choice_a = 'D' and choice_b = 'C' then 1 else 0 end as betrayal_a,
    case when choice_b = 'D' and choice_a = 'C' then 1 else 0 end as betrayal_b
from raw
