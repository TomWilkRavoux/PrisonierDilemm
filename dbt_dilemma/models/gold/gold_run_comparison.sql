with metrics as (
    select * from {{ ref('gold_strategy_metrics') }}
)

select
    run_id,
    strategy,
    avg_score,
    total_score,
    coop_rate,
    forgiveness_rate,
    rank_in_run,
    rank() over (order by avg_score desc) as global_rank
from metrics
