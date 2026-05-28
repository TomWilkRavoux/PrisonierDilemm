select
    run_id,
    match_id,
    player_a,
    player_b,
    strategy_a,
    strategy_b,
    total_score_a,
    total_score_b,
    num_turns
from {{ source('silver', 'matches') }}
