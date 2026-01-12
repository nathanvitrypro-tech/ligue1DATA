import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. CONFIGURATION DE LA PAGE
st.set_page_config(page_title="Ligue 1 - Ultimate Dashboard", layout="wide", page_icon="⚽")

# 2. SÉCURITÉ : RÉCUPÉRATION DE LA CLÉ API
try:
    # Le code cherche la clé dans les secrets de Streamlit Cloud
    API_KEY = st.secrets["API_KEY"]
except FileNotFoundError:
    # Fallback pour test local (à ne pas commiter sur GitHub idéalement)
    # Tu peux laisser ça vide ou mettre une instruction pour l'utilisateur
    st.error("⚠️ Clé API non trouvée ! Configurez le secret 'API_KEY' sur Streamlit Cloud.")
    st.stop()

# 3. DESIGN CSS PERSONNALISÉ
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    h1, h2, h3, h4 { color: #1e293b; font-family: 'Helvetica Neue', sans-serif; }
    
    /* Style des cartes (Containers blancs) */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background-color: white; padding: 25px; border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Métriques en bleu */
    div[data-testid="stMetricValue"] { color: #2563eb; font-weight: 800; }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem; color: #64748b; }
    </style>
""", unsafe_allow_html=True)

# 4. FONCTIONS API (MOTEUR DE DONNÉES)
def get_headers():
    return {
        'x-rapidapi-host': "api-football-v1.p.rapidapi.com",
        'x-rapidapi-key': API_KEY
    }

@st.cache_data(ttl=3600)
def get_ligue1_data():
    """Récupère le Classement général et les Prochains Matchs"""
    LEAGUE_ID = 61
    SEASON = 2025 # Saison 2025/2026
    headers = get_headers()
    
    # A. CLASSEMENT
    url_standings = "https://api-football-v1.p.rapidapi.com/v3/standings"
    try:
        data_standings = requests.get(url_standings, headers=headers, params={'league': LEAGUE_ID, 'season': SEASON}).json()
    except:
        return pd.DataFrame(), pd.DataFrame()
    
    standings_list = []
    if 'response' in data_standings and data_standings['response']:
        # On cible le premier tableau (Ligue 1)
        for t in data_standings['response'][0]['league']['standings'][0]:
            standings_list.append({
                'ID': t['team']['id'],
                'Rang': t['rank'],
                'Equipe': t['team']['name'],
                'Logo': t['team']['logo'],
                'MJ': t['all']['played'],
                'V': t['all']['win'],
                'N': t['all']['draw'],
                'D': t['all']['lose'],
                'Pts': t['points'],
                'Diff': t['goalsDiff'],
                'BP': t['all']['goals']['for'],
                'BC': t['all']['goals']['against'],
                'Forme': t['form'] # ex: "WWDLW"
            })
    
    # B. PROCHAINS MATCHS (FIXTURES)
    url_fixtures = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    # On demande les 10 prochains matchs
    params_fix = {'league': LEAGUE_ID, 'season': SEASON, 'next': 10} 
    try:
        data_fixtures = requests.get(url_fixtures, headers=headers, params=params_fix).json()
    except:
        data_fixtures = {}
    
    fixtures_list = []
    if 'response' in data_fixtures:
        for f in data_fixtures['response']:
            # Formatage de la date ISO vers lisible
            try:
                date_obj = datetime.fromisoformat(f['fixture']['date'].replace('Z', '+00:00'))
                date_str = date_obj.strftime("%d/%m %H:%M")
            except:
                date_str = f['fixture']['date']
            
            fixtures_list.append({
                'Date': date_str,
                'Domicile': f['teams']['home']['name'],
                'Logo_Dom': f['teams']['home']['logo'],
                'Exterieur': f['teams']['away']['name'],
                'Logo_Ext': f['teams']['away']['logo'],
                'Stade': f['fixture']['venue']['name']
            })

    return pd.DataFrame(standings_list), pd.DataFrame(fixtures_list)

@st.cache_data(ttl=3600)
def get_team_details(team_id):
    """Récupère l'effectif complet d'une équipe"""
    url = "https://api-football-v1.p.rapidapi.com/v3/players"
    # On demande la page 1 seulement pour économiser le quota gratuit
    params = {'league': 61, 'season': 2025, 'team': team_id}
    
    try:
        data = requests.get(url, headers=get_headers(), params=params).json()
    except:
        return pd.DataFrame()
    
    players = []
    if 'response' in data:
        for p in data['response']:
            info = p['player']
            stats = p['statistics'][0]
            
            # Gestion des notes nulles
            rating = stats['games']['rating']
            rating_val = float(rating) if rating else 0.0

            players.append({
                'Photo': info['photo'],
                'Nom': info['name'],
                'Age': info['age'],
                'Poste': stats['games']['position'],
                'Note': rating_val,
                'Min': stats['games']['minutes'] or 0,
                'Buts': stats['goals']['total'] or 0,
                'Passes': stats['goals']['assists'] or 0,
                'Jaunes': stats['cards']['yellow'] or 0,
                'Rouges': stats['cards']['red'] or 0
            })
    return pd.DataFrame(players)

# 5. CHARGEMENT DES DONNÉES PRINCIPALES
with st.spinner('Analyse de la Ligue 1 en cours...'):
    df_standings, df_fixtures = get_ligue1_data()

# 6. INTERFACE UTILISATEUR
st.title("🇫🇷 Ligue 1 • Ultimate Dashboard")

if not df_standings.empty:
    
    # NAVIGATION PAR ONGLETS
    tab1, tab2, tab3 = st.tabs(["🏆 Classement & Forme", "📅 Prochains Matchs", "🔍 Focus Club (Détaillé)"])
    
    # --- ONGLET 1 : VUE GÉNÉRALE ---
    with tab1:
        # KPI du haut
        c1, c2, c3, c4 = st.columns(4)
        leader = df_standings.iloc[0]
        c1.metric("Leader", leader['Equipe'], f"{leader['Pts']} pts")
        
        best_attack = df_standings.sort_values('BP', ascending=False).iloc[0]
        c2.metric("Meilleure Attaque", best_attack['Equipe'], f"{best_attack['BP']} buts")
        
        best_defense = df_standings.sort_values('BC', ascending=True).iloc[0]
        c3.metric("Meilleure Défense", best_defense['Equipe'], f"{best_defense['BC']} buts")
        
        c4.metric("Journée en cours", f"{leader['MJ']} Matchs joués")
        
        st.divider()
        
        # Graphique Forme (Scatter Plot)
        st.subheader("📊 Dynamique : Attaque vs Défense")
        fig = px.scatter(df_standings, x="BC", y="BP", 
                         text="Equipe", size="Pts", color="Forme",
                         color_discrete_sequence=px.colors.qualitative.Bold,
                         title="Plus on est en haut à gauche, mieux c'est !",
                         hover_data=["Rang", "Diff"])
        # On inverse l'axe X (moins de buts encaissés = mieux)
        fig.update_xaxes(autorange="reversed", title="Solidité (Buts Encaissés)")
        fig.update_yaxes(title="Puissance (Buts Marqués)")
        fig.update_layout(height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau Classement
        st.subheader("Classement Détaillé")
        st.dataframe(
            df_standings[['Rang', 'Logo', 'Equipe', 'MJ', 'Pts', 'Diff', 'Forme']],
            column_config={
                "Logo": st.column_config.ImageColumn("Club", width="small"),
                "Forme": st.column_config.TextColumn("Derniers 5 matchs"),
                "Pts": st.column_config.ProgressColumn("Points", format="%d", min_value=0, max_value=100)
            },
            hide_index=True, use_container_width=True
        )

    # --- ONGLET 2 : CALENDRIER ---
    with tab2:
        st.subheader("📅 Les 10 prochains chocs")
        if not df_fixtures.empty:
            for index, row in df_fixtures.iterrows():
                with st.container():
                    c_date, c_dom, c_vs, c_ext, c_stade = st.columns([2, 3, 1, 3, 3])
                    c_date.write(f"**{row['Date']}**")
                    
                    with c_dom:
                        col_img, col_txt = st.columns([1, 3])
                        col_img.image(row['Logo_Dom'], width=30)
                        col_txt.write(row['Domicile'])
                    
                    c_vs.markdown("<div style='text-align: center; color: #888; font-weight:bold;'>VS</div>", unsafe_allow_html=True)
                    
                    with c_ext:
                        col_img, col_txt = st.columns([1, 3])
                        col_img.image(row['Logo_Ext'], width=30)
                        col_txt.write(row['Exterieur'])
                        
                    c_stade.caption(f"📍 {row['Stade']}")
                st.divider()
        else:
            st.info("Aucun match programmé prochainement ou limite API atteinte.")

    # --- ONGLET 3 : ANALYSE CLUB ---
    with tab3:
        st.subheader("🔎 Analyse Approfondie par Club")
        
        # Sélecteur d'équipe
        teams_map = dict(zip(df_standings['Equipe'], df_standings['ID']))
        selected_team = st.selectbox("Choisir une équipe pour voir l'analyse :", df_standings['Equipe'].unique())
        
        # Appel API joueurs
        with st.spinner(f"Scouting {selected_team}..."):
            df_players = get_team_details(teams_map[selected_team])
        
        if not df_players.empty:
            
            # --- BLOC 1 : RADAR CHART INTELLIGENT ---
            st.markdown("#### 🕸️ Profil Tactique & Performance")
            
            club_data = df_standings[df_standings['Equipe'] == selected_team].iloc[0]
            
            # Calculs pour le Radar
            max_bp = df_standings['BP'].max()
            score_attaque = (club_data['BP'] / max_bp) * 100
            
            max_bc = df_standings['BC'].max()
            min_bc = df_standings['BC'].min()
            # Score Défense (Inversé : proche de 100 si peu de buts encaissés)
            if max_bc != min_bc:
                score_defense = ((max_bc - club_data['BC']) / (max_bc - min_bc)) * 100
            else:
                score_defense = 50
            
            score_win_rate = (club_data['V'] / club_data['MJ']) * 100
            
            # Score Forme (WWDLW -> Points)
            form_str = club_data['Forme']
            pts_forme = 0
            for char in form_str:
                if char == 'W': pts_forme += 3
                elif char == 'D': pts_forme += 1
            score_forme = (pts_forme / 15) * 100
            
            # Score Dominance (Pts obtenus / Pts max possibles)
            score_puissance = (club_data['Pts'] / (club_data['MJ'] * 3)) * 100

            # Affichage Radar
            col_kpi, col_radar = st.columns([1, 2])
            
            with col_kpi:
                st.image(club_data['Logo'], width=100)
                st.metric("Points", f"{club_data['Pts']}")
                st.metric("Différence", f"{club_data['Diff']}")
                
                badges = form_str.replace('W', '🟢').replace('D', '🟡').replace('L', '🔴')
                st.write(f"**Forme :** {badges}")

            with col_radar:
                categories = ['Attaque 🔥', 'Défense 🛡️', 'Victoires 🎯', 'Forme (5m) ⚡', 'Dominance 👑']
                values = [score_attaque, score_defense, score_win_rate, score_forme, score_puissance]
                
                # Fermeture du polygone
                values += values[:1]
                categories += categories[:1]
                
                fig_radar = go.Figure()
                
                # Zone du Club
                fig_radar.add_trace(go.Scatterpolar(
                    r=values, theta=categories, fill='toself', name=selected_team,
                    line_color='#2563eb', fillcolor='rgba(37, 99, 235, 0.2)'
                ))
                
                # Ligne Moyenne (50%)
                fig_radar.add_trace(go.Scatterpolar(
                    r=[50]*6, theta=categories, name='Moyenne Ligue',
                    line_color='gray', line_dash='dot', hoverinfo='skip'
                ))

                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=8))),
                    showlegend=True,
                    margin=dict(t=20, b=20, l=40, r=40), height=350,
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            # --- BLOC 2 : TABLEAU JOUEURS ---
            st.write("#### 🏃 Effectif & Stats Détaillées")
            st.dataframe(
                df_players.sort_values(by='Min', ascending=False),
                column_config={
                    "Photo": st.column_config.ImageColumn("J", width="small"),
                    "Note": st.column_config.ProgressColumn("Note", format="%.1f", min_value=0, max_value=10),
                    "Min": st.column_config.NumberColumn("Minutes", format="%d'"),
                    "Buts": st.column_config.NumberColumn("Buts", format="%d ⚽"),
                    "Passes": st.column_config.NumberColumn("Passes", format="%d 🎯"),
                    "Jaunes": st.column_config.NumberColumn("Jaunes", format="%d 🟨"),
                    "Rouges": st.column_config.NumberColumn("Rouges", format="%d 🟥"),
                },
                hide_index=True, use_container_width=True, height=600
            )
        else:
            st.warning("Données joueurs indisponibles (quota API atteint ou équipe non trouvée).")

else:
    st.error("Impossible de récupérer les données de Ligue 1. Vérifiez votre clé API ou votre connexion.")
