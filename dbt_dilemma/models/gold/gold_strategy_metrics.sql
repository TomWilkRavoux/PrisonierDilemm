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
        score_a as score,
        cooperated_a as cooperated,
        betrayal_a as betrayal
    from turns

    union all

    select
        run_id,
        match_id,
        turn_number,
        strategy_b as strategy,
        choice_b as choice,
        score_b as score,
        cooperated_b as cooperated,
        betrayal_b as betrayal
    from turns
),

with_lag as (
    select
        *,
        lag(choice) over (
            partition by run_id, match_id, strategy order by turn_number
        ) as prev_choice
    from unpivoted
),

forgiveness as (
    select
        run_id,
        match_id,
        strategy,
        sum(case when choice = 'C' and prev_choice = 'D' then 1 else 0 end) as forgive_count,
        sum(case when prev_choice = 'D' then 1 else 0 end) as after_defect_count
    from with_lag
    group by run_id, match_id, strategy
),

strategy_stats as (
    select
        u.run_id,
        u.strategy,
        round(avg(u.score), 3) as avg_score,
        sum(u.score) as total_score,
        round(avg(u.cooperated), 3) as coop_rate,
        sum(u.betrayal) as total_betrayals,
        count(distinct u.match_id) as num_matches
    from unpivoted u
    group by u.run_id, u.strategy
),

forgiveness_agg as (
    select
        run_id,
        strategy,
        case
            when sum(after_defect_count) > 0
            then round(sum(forgive_count)::float / sum(after_defect_count), 3)
            else null
        end as forgiveness_rate
    from forgiveness
    group by run_id, strategy
)

select
    ss.run_id,
    ss.strategy,
    ss.avg_score,
    ss.total_score,
    ss.coop_rate,
    ss.total_betrayals,
    ss.num_matches,
    fa.forgiveness_rate,
    rank() over (partition by ss.run_id order by ss.total_score desc) as rank_in_run
from strategy_stats ss
left join forgiveness_agg fa on ss.run_id = fa.run_id and ss.strategy = fa.strategy
