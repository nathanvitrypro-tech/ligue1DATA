import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# 1. CONFIGURATION
st.set_page_config(page_title="Ligue 1 - Pro Dashboard", layout="wide", page_icon="⚽")

# 2. GESTION SÉCURISÉE DE LA CLÉ API
# Le code va chercher la clé dans les secrets de Streamlit Cloud
try:
    API_KEY = st.secrets["API_KEY"]
except FileNotFoundError:
    st.error("⚠️ Clé API non trouvée ! Pensez à configurer les 'Secrets' sur Streamlit Cloud.")
    st.stop()

# 3. CSS DESIGN
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1, h2, h3, h4, h5, p, span, div, label { color: #2c3e50 !important; }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background-color: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #e0e0e0;
    }
    div[data-testid="stMetricValue"] { color: #2c3e50 !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)


# 4. FONCTIONS API
def get_headers():
    return {
        'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
        'x-rapidapi-key': API_KEY
    }


@st.cache_data(ttl=3600)
def get_ligue1_standings():
    """Récupère le classement général"""
    LEAGUE_ID = 61
    SEASON = 2025  # Saison 2025-2026

    url = "https://api-football-v1.p.rapidapi.com/v3/standings"
    params = {'league': LEAGUE_ID, 'season': SEASON}

    try:
        response = requests.get(url, headers=get_headers(), params=params)
        data = response.json()

        standings_list = []
        if 'response' in data and len(data['response']) > 0:
            league_table = data['response'][0]['league']['standings'][0]
            for team in league_table:
                standings_list.append({
                    'ID': team['team']['id'],
                    'Rang': team['rank'],
                    'Equipe': team['team']['name'],
                    'Logo': team['team']['logo'],
                    'MJ': team['all']['played'],
                    'V': team['all']['win'],
                    'N': team['all']['draw'],
                    'D': team['all']['lose'],
                    'BP': team['all']['goals']['for'],
                    'BC': team['all']['goals']['against'],
                    'Diff': team['goalsDiff'],
                    'Pts': team['points'],
                    'Forme': team['form']
                })
            return pd.DataFrame(standings_list)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur Classement : {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_team_squad_stats(team_id):
    """Récupère les stats des joueurs d'une équipe"""
    LEAGUE_ID = 61
    SEASON = 2025

    url = "https://api-football-v1.p.rapidapi.com/v3/players"
    # On limite à la page 1 pour économiser les requêtes (Plan Gratuit)
    params = {'league': LEAGUE_ID, 'season': SEASON, 'team': team_id}

    try:
        response = requests.get(url, headers=get_headers(), params=params)
        data = response.json()

        players_list = []
        if 'response' in data:
            for item in data['response']:
                p = item['player']
                s = item['statistics'][0]

                note = s['games']['rating']
                note_val = float(note) if note else 0.0

                players_list.append({
                    'Photo': p['photo'],
                    'Nom': p['name'],
                    'Age': p['age'],
                    'Poste': s['games']['position'],
                    'Matchs': s['games']['appearences'] or 0,
                    'Minutes': s['games']['minutes'] or 0,
                    'Note': note_val,
                    'Buts': s['goals']['total'] or 0,
                    'Passes': s['goals']['assists'] or 0
                })
            return pd.DataFrame(players_list)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()


# 5. CHARGEMENT
with st.spinner('Chargement Ligue 1...'):
    df_standings = get_ligue1_standings()

# 6. UI DASHBOARD
st.title("🇫🇷 Ligue 1 • Saison 2025/2026")

if df_standings is not None and not df_standings.empty:

    # PODIUM
    c1, c2, c3 = st.columns(3)
    if len(df_standings) >= 3:
        with c1:
            st.markdown(f"### 🥇 {df_standings.iloc[0]['Equipe']}")
            st.image(df_standings.iloc[0]['Logo'], width=60)
            st.metric("Leader", f"{df_standings.iloc[0]['Pts']} pts")
        with c2:
            st.markdown(f"### 🥈 {df_standings.iloc[1]['Equipe']}")
            st.image(df_standings.iloc[1]['Logo'], width=60)
            st.metric("Chasseur", f"{df_standings.iloc[1]['Pts']} pts")
        with c3:
            st.markdown(f"### 🥉 {df_standings.iloc[2]['Equipe']}")
            st.image(df_standings.iloc[2]['Logo'], width=60)
            st.metric("Podium", f"{df_standings.iloc[2]['Pts']} pts")

    st.divider()

    # GRAPHIQUE
    st.subheader("📊 Performance Globale (Attaque/Défense)")
    fig = px.scatter(df_standings, x="BC", y="BP",
                     text="Equipe", size="Pts", color="Pts",
                     color_continuous_scale="Viridis",
                     hover_data=["Forme"])
    fig.update_xaxes(autorange="reversed", title="Buts Encaissés")
    fig.update_yaxes(title="Buts Marqués")
    fig.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # FOCUS CLUB
    st.markdown("### 🔎 Focus Club & Effectif")

    teams_dict = dict(zip(df_standings['Equipe'], df_standings['ID']))
    selected_team_name = st.selectbox("Sélectionner un club :", df_standings['Equipe'].unique())
    selected_team_id = teams_dict[selected_team_name]

    with st.spinner(f"Analyse de {selected_team_name}..."):
        df_players = get_team_squad_stats(selected_team_id)

    if not df_players.empty:
        # KPI Club
        club_stats = df_standings[df_standings['Equipe'] == selected_team_name].iloc[0]
        k1, k2, k3, k4 = st.columns(4)
        k1.image(club_stats['Logo'], width=70)
        k2.metric("Classement", f"{club_stats['Rang']}e", f"{club_stats['Pts']} pts")
        k3.metric("Attaque", f"{club_stats['BP']} buts")
        k4.metric("Forme", club_stats['Forme'])

        st.write("#### 🏃‍♂️ Joueurs Clés")

        st.dataframe(
            df_players[['Photo', 'Nom', 'Poste', 'Age', 'Matchs', 'Buts', 'Passes', 'Note']].sort_values(by='Note',
                                                                                                         ascending=False),
            column_config={
                "Photo": st.column_config.ImageColumn("Avatar", width="small"),
                "Note": st.column_config.ProgressColumn("Note Moy.", format="%.1f", min_value=0, max_value=10),
                "Buts": st.column_config.NumberColumn("Buts", format="%d ⚽"),
                "Passes": st.column_config.NumberColumn("Passes", format="%d 🎯"),
            },
            hide_index=True,
            use_container_width=True,
            height=500
        )
    else:
        st.info("Données détaillées non disponibles pour ce club (Limite API gratuite).")

else:
    st.warning("Impossible de récupérer le classement. Vérifiez la clé API dans les Secrets.")