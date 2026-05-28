import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "dilemma.duckdb"
DBT_DIR = Path(__file__).resolve().parent / "dbt_dilemma"

st.set_page_config(
    page_title="Dilemme du Prisonnier — Dashboard",
    page_icon="🎲",
    layout="wide",
)


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def query(sql: str):
    con = get_connection()
    con.execute(f"SET FILE_SEARCH_PATH='{DBT_DIR}'")
    return con.execute(sql).fetchdf()


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────

st.sidebar.title("🎲 Dilemme du Prisonnier")

runs = query("SELECT DISTINCT run_id FROM gold_strategy_metrics ORDER BY run_id")
run_ids = runs["run_id"].tolist()

selected_run = st.sidebar.selectbox("Run", run_ids, index=len(run_ids) - 1)

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Classement des strategies",
        "⚔️ Confrontations directes",
        "📈 Evolution temporelle",
        "🏆 Resume des matchs",
        "🔄 Comparaison multi-run",
    ],
)

# ──────────────────────────────────────────────
# Page 1 — Classement
# ──────────────────────────────────────────────

if page == "📊 Classement des strategies":
    st.title("Classement des strategies")

    metrics = query(f"""
        SELECT strategy, avg_score, total_score, coop_rate,
               total_betrayals, forgiveness_rate, rank_in_run
        FROM gold_strategy_metrics
        WHERE run_id = '{selected_run}'
        ORDER BY rank_in_run
    """)

    col1, col2, col3 = st.columns(3)
    col1.metric("🥇 1er", metrics.iloc[0]["strategy"])
    col2.metric("🥈 2eme", metrics.iloc[1]["strategy"])
    col3.metric("🥉 3eme", metrics.iloc[2]["strategy"])

    st.subheader("Score moyen par tour")
    fig_score = px.bar(
        metrics,
        x="strategy",
        y="avg_score",
        color="avg_score",
        color_continuous_scale="Viridis",
        text="avg_score",
    )
    fig_score.update_layout(xaxis_tickangle=-45, showlegend=False)
    fig_score.update_traces(textposition="outside")
    st.plotly_chart(fig_score, use_container_width=True)

    st.subheader("Taux de cooperation vs Score moyen")
    fig_scatter = px.scatter(
        metrics,
        x="coop_rate",
        y="avg_score",
        size="total_score",
        color="strategy",
        text="strategy",
        size_max=50,
    )
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.update_layout(
        xaxis_title="Taux de cooperation",
        yaxis_title="Score moyen par tour",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Cooperation / Trahison / Pardon")
    fig_radar_data = metrics[["strategy", "coop_rate", "forgiveness_rate"]].copy()
    fig_radar_data["forgiveness_rate"] = fig_radar_data["forgiveness_rate"].fillna(0)
    fig_radar_data["defect_rate"] = 1 - fig_radar_data["coop_rate"]

    fig_multi = px.bar(
        fig_radar_data.melt(
            id_vars="strategy",
            value_vars=["coop_rate", "defect_rate", "forgiveness_rate"],
            var_name="Metrique",
            value_name="Valeur",
        ),
        x="strategy",
        y="Valeur",
        color="Metrique",
        barmode="group",
        color_discrete_map={
            "coop_rate": "#2ecc71",
            "defect_rate": "#e74c3c",
            "forgiveness_rate": "#3498db",
        },
    )
    fig_multi.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_multi, use_container_width=True)

    st.subheader("Tableau complet")
    st.dataframe(metrics, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
# Page 2 — Head-to-head
# ──────────────────────────────────────────────

elif page == "⚔️ Confrontations directes":
    st.title("Confrontations directes")

    h2h = query(f"""
        SELECT strategy, opponent, score, opponent_score, score_diff, result
        FROM gold_head_to_head
        WHERE run_id = '{selected_run}'
        ORDER BY strategy, opponent
    """)

    st.subheader("Matrice des differences de score")
    pivot = h2h.pivot(index="strategy", columns="opponent", values="score_diff")
    pivot = pivot.fillna(0)

    fig_heatmap = px.imshow(
        pivot,
        text_auto=True,
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        aspect="auto",
    )
    fig_heatmap.update_layout(
        xaxis_title="Adversaire",
        yaxis_title="Strategie",
        height=500,
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.subheader("Bilan victoires / nuls / defaites")
    results_agg = h2h.groupby(["strategy", "result"]).size().reset_index(name="count")
    fig_results = px.bar(
        results_agg,
        x="strategy",
        y="count",
        color="result",
        barmode="stack",
        color_discrete_map={"win": "#2ecc71", "draw": "#f39c12", "loss": "#e74c3c"},
    )
    fig_results.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_results, use_container_width=True)

    st.subheader("Detail par strategie")
    selected_strategy = st.selectbox(
        "Choisir une strategie",
        sorted(h2h["strategy"].unique()),
    )
    detail = h2h[h2h["strategy"] == selected_strategy].sort_values("score_diff", ascending=False)

    fig_detail = px.bar(
        detail,
        x="opponent",
        y="score_diff",
        color="result",
        text="score_diff",
        color_discrete_map={"win": "#2ecc71", "draw": "#f39c12", "loss": "#e74c3c"},
    )
    fig_detail.update_layout(
        xaxis_title="Adversaire",
        yaxis_title="Difference de score",
        xaxis_tickangle=-45,
    )
    fig_detail.update_traces(textposition="outside")
    st.plotly_chart(fig_detail, use_container_width=True)

# ──────────────────────────────────────────────
# Page 3 — Evolution temporelle
# ──────────────────────────────────────────────

elif page == "📈 Evolution temporelle":
    st.title("Evolution temporelle")

    matches = query(f"""
        SELECT DISTINCT match_id, strategy_a, strategy_b
        FROM gold_match_summary
        WHERE run_id = '{selected_run}'
        ORDER BY strategy_a, strategy_b
    """)

    match_labels = {
        row["match_id"]: f"{row['strategy_a']} vs {row['strategy_b']}"
        for _, row in matches.iterrows()
    }
    selected_match_label = st.selectbox("Match", list(match_labels.values()))
    selected_match_id = [k for k, v in match_labels.items() if v == selected_match_label][0]

    evo = query(f"""
        SELECT turn_number, strategy, choice, score, cumulative_score,
               rolling_coop_rate_50
        FROM gold_turn_evolution
        WHERE run_id = '{selected_run}' AND match_id = '{selected_match_id}'
        ORDER BY strategy, turn_number
    """)

    st.subheader("Score cumule")
    fig_cum = px.line(
        evo,
        x="turn_number",
        y="cumulative_score",
        color="strategy",
        markers=False,
    )
    fig_cum.update_layout(
        xaxis_title="Tour",
        yaxis_title="Score cumule",
    )
    st.plotly_chart(fig_cum, use_container_width=True)

    st.subheader("Taux de cooperation glissant (50 tours)")
    fig_coop = px.line(
        evo,
        x="turn_number",
        y="rolling_coop_rate_50",
        color="strategy",
        markers=False,
    )
    fig_coop.update_layout(
        xaxis_title="Tour",
        yaxis_title="Taux de cooperation (rolling 50)",
    )
    st.plotly_chart(fig_coop, use_container_width=True)

    st.subheader("Choix tour par tour")
    strategies_in_match = sorted(evo["strategy"].unique())
    for strat in strategies_in_match:
        strat_data = evo[evo["strategy"] == strat].copy()
        strat_data["color"] = strat_data["choice"].map({"C": "#2ecc71", "D": "#e74c3c"})

        fig_choices = go.Figure()
        fig_choices.add_trace(go.Bar(
            x=strat_data["turn_number"],
            y=[1] * len(strat_data),
            marker_color=strat_data["color"],
            name=strat,
            hovertext=strat_data["choice"],
        ))
        fig_choices.update_layout(
            title=f"{strat}",
            xaxis_title="Tour",
            yaxis_visible=False,
            height=120,
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_choices, use_container_width=True)

# ──────────────────────────────────────────────
# Page 4 — Resume des matchs
# ──────────────────────────────────────────────

elif page == "🏆 Resume des matchs":
    st.title("Resume des matchs")

    summary = query(f"""
        SELECT strategy_a, strategy_b, total_score_a, total_score_b,
               coop_rate_a, coop_rate_b, mutual_coop_rate,
               betrayal_count_a, betrayal_count_b, mutual_coop, mutual_defect
        FROM gold_match_summary
        WHERE run_id = '{selected_run}'
        ORDER BY strategy_a, strategy_b
    """)

    st.subheader("Cooperation mutuelle par match")
    fig_mutual = px.bar(
        summary,
        x=summary.apply(lambda r: f"{r['strategy_a']} vs {r['strategy_b']}", axis=1),
        y="mutual_coop_rate",
        color="mutual_coop_rate",
        color_continuous_scale="Greens",
    )
    fig_mutual.update_layout(
        xaxis_title="Match",
        yaxis_title="Taux de cooperation mutuelle",
        xaxis_tickangle=-60,
        height=500,
    )
    st.plotly_chart(fig_mutual, use_container_width=True)

    st.subheader("Scores par match")
    fig_scores = go.Figure()
    labels = summary.apply(lambda r: f"{r['strategy_a']} vs {r['strategy_b']}", axis=1)
    fig_scores.add_trace(go.Bar(name="Joueur A", x=labels, y=summary["total_score_a"], marker_color="#3498db"))
    fig_scores.add_trace(go.Bar(name="Joueur B", x=labels, y=summary["total_score_b"], marker_color="#e67e22"))
    fig_scores.update_layout(
        barmode="group",
        xaxis_tickangle=-60,
        xaxis_title="Match",
        yaxis_title="Score total",
        height=500,
    )
    st.plotly_chart(fig_scores, use_container_width=True)

    st.subheader("Tableau complet")
    st.dataframe(summary, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
# Page 5 — Comparaison multi-run
# ──────────────────────────────────────────────

elif page == "🔄 Comparaison multi-run":
    st.title("Comparaison multi-run")

    comparison = query("""
        SELECT run_id, strategy, avg_score, total_score, coop_rate,
               forgiveness_rate, rank_in_run, global_rank
        FROM gold_run_comparison
        ORDER BY strategy, run_id
    """)

    num_runs = comparison["run_id"].nunique()
    st.info(f"Nombre de runs disponibles : **{num_runs}**")

    if num_runs < 2:
        st.warning("Lancez `make generate && make load && make transform` pour ajouter un 2eme run.")

    st.subheader("Score moyen par strategie et par run")
    fig_comp = px.bar(
        comparison,
        x="strategy",
        y="avg_score",
        color="run_id",
        barmode="group",
        text="rank_in_run",
    )
    fig_comp.update_layout(xaxis_tickangle=-45)
    fig_comp.update_traces(texttemplate="Rank %{text}", textposition="outside")
    st.plotly_chart(fig_comp, use_container_width=True)

    st.subheader("Evolution du classement entre les runs")
    fig_rank = px.line(
        comparison.sort_values(["strategy", "run_id"]),
        x="run_id",
        y="rank_in_run",
        color="strategy",
        markers=True,
    )
    fig_rank.update_layout(
        xaxis_title="Run",
        yaxis_title="Classement (1 = meilleur)",
        yaxis_autorange="reversed",
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    st.subheader("Taux de cooperation par run")
    fig_coop_run = px.bar(
        comparison,
        x="strategy",
        y="coop_rate",
        color="run_id",
        barmode="group",
    )
    fig_coop_run.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_coop_run, use_container_width=True)

    st.subheader("Classement global (tous runs confondus)")
    global_rank = comparison.drop_duplicates(subset=["strategy", "run_id"]).sort_values("global_rank")
    st.dataframe(
        global_rank[["global_rank", "strategy", "run_id", "avg_score", "coop_rate", "forgiveness_rate"]],
        use_container_width=True,
        hide_index=True,
    )
