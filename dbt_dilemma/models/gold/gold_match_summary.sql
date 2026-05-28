with turns as (
    select * from {{ ref('stg_turns') }}
),

matches as (
    select * from {{ ref('stg_matches') }}
),

turn_agg as (
    select
        run_id,
        match_id,
        sum(cooperated_a) as coop_count_a,
        sum(cooperated_b) as coop_count_b,
        sum(betrayal_a) as betrayal_count_a,
        sum(betrayal_b) as betrayal_count_b,
        sum(case when choice_a = 'C' and choice_b = 'C' then 1 else 0 end) as mutual_coop,
        sum(case when choice_a = 'D' and choice_b = 'D' then 1 else 0 end) as mutual_defect,
        count(*) as total_turns
    from turns
    group by run_id, match_id
)

select
    m.run_id,
    m.match_id,
    m.player_a,
    m.player_b,
    m.strategy_a,
    m.strategy_b,
    m.total_score_a,
    m.total_score_b,
    m.num_turns,
    ta.coop_count_a,
    ta.coop_count_b,
    round(ta.coop_count_a::float / ta.total_turns, 3) as coop_rate_a,
    round(ta.coop_count_b::float / ta.total_turns, 3) as coop_rate_b,
    ta.betrayal_count_a,
    ta.betrayal_count_b,
    ta.mutual_coop,
    ta.mutual_defect,
    round(ta.mutual_coop::float / ta.total_turns, 3) as mutual_coop_rate
from matches m
join turn_agg ta on m.run_id = ta.run_id and m.match_id = ta.match_id
