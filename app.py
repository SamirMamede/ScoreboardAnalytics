import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="ScoreboardAnalytics", layout="wide")

API_KEY = os.getenv('FOOTBALL_API_KEY')
headers = {'X-Auth-Token': API_KEY}

COMPETITIONS = {
    'Premier League': {'id': 2021, 'country': 'England'},
    'La Liga': {'id': 2014, 'country': 'Spain'},
    'Italy Serie A': {'id': 2019, 'country': 'Italy'},
    'Bundesliga': {'id': 2002, 'country': 'Germany'}
}

@st.cache_data(ttl=3600)
def get_competition_info(competition_id):
    url = f'http://api.football-data.org/v4/competitions/{competition_id}'
    response = requests.get(url, headers=headers)
    return response.json()

@st.cache_data(ttl=1800)
def get_standings(competition_id):
    url = f'http://api.football-data.org/v4/competitions/{competition_id}/standings'
    response = requests.get(url, headers=headers)
    return response.json()

@st.cache_data(ttl=1800)
def get_matches(competition_id, status='SCHEDULED'):
    url = f'http://api.football-data.org/v4/competitions/{competition_id}/matches?status={status}'
    response = requests.get(url, headers=headers)
    return response.json()

@st.cache_data(ttl=1800)
def get_scorers(competition_id):
    url = f'http://api.football-data.org/v4/competitions/{competition_id}/scorers'
    response = requests.get(url, headers=headers)
    return response.json()

st.title("⚽ ScoreboardAnalytics")

league_tabs = st.tabs(list(COMPETITIONS.keys()))

for idx, (league_name, league_info) in enumerate(COMPETITIONS.items()):
    with league_tabs[idx]:
        competition_info = get_competition_info(league_info['id'])
        standings_data = get_standings(league_info['id'])
        upcoming_matches = get_matches(league_info['id'], 'SCHEDULED')
        finished_matches = get_matches(league_info['id'], 'FINISHED')

        if 'currentSeason' in competition_info:
            season_info = competition_info['currentSeason']
            st.subheader(f"Temporada: {season_info['startDate'][:4]}/{season_info['endDate'][:4]}")

        data_tabs = st.tabs(["📊 Classificação", "⚽ Artilheiros", "🎯 Próximos Jogos", "📅 Últimos Resultados"])

        with data_tabs[0]:
            if 'standings' in standings_data:
                standings_list = []
                for team in standings_data['standings'][0]['table']:
                    standings_list.append({
                        'Posição': team['position'],
                        'Time': team['team']['name'],
                        'Pontos': team['points'],
                        'Jogos': team['playedGames'],
                        'Vitórias': team['won'],
                        'Empates': team['draw'],
                        'Derrotas': team['lost'],
                        'Gols Pró': team['goalsFor'],
                        'Gols Contra': team['goalsAgainst'],
                        'Saldo': team['goalDifference'],
                        'Saldo_Format': f"+{team['goalDifference']}" if team['goalDifference'] > 0 else str(team['goalDifference']),
                        'Aproveitamento': round((team['points'] / (team['playedGames'] * 3)) * 100, 1)
                    })
                
                df_standings = pd.DataFrame(standings_list)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Classificação Geral")
                    df_basic = df_standings[['Posição', 'Time', 'Pontos', 'Jogos', 'Saldo_Format', 'Aproveitamento']]
                    df_basic = df_basic.rename(columns={'Saldo_Format': 'Saldo'})
                    df_basic = df_basic.style.format({
                        'Aproveitamento': '{:.1f}%'
                    }).background_gradient(subset=['Pontos', 'Aproveitamento'], cmap='RdYlGn')
                    st.dataframe(df_basic, hide_index=True)
                
                with col2:
                    st.subheader("Análise de Gols")
                    df_goals = pd.DataFrame({
                        'Time': df_standings['Time'],
                        'Gols Pró': df_standings['Gols Pró'],
                        'Gols Contra': df_standings['Gols Contra'],
                        'Saldo': df_standings['Saldo_Format'],
                        'Média por Jogo': round(df_standings['Gols Pró'] / df_standings['Jogos'], 2)
                    })
                    df_goals = df_goals.style.background_gradient(subset=['Gols Pró', 'Média por Jogo'], cmap='RdYlGn')
                    st.dataframe(df_goals, hide_index=True)

                fig_goals = px.bar(df_standings, 
                                x='Time', 
                                y=['Gols Pró', 'Gols Contra'],
                                title='Comparação de Gols Marcados e Sofridos',
                                barmode='group')
                st.plotly_chart(fig_goals, use_container_width=True)

                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_goals = df_standings['Gols Pró'].sum()
                    avg_goals = round(total_goals / (len(df_standings) * df_standings['Jogos'].iloc[0]), 2)
                    st.metric("Média de Gols por Jogo na Liga", f"{avg_goals}")
                
                with col2:
                    highest_scoring = df_standings.nlargest(1, 'Gols Pró').iloc[0]
                    st.metric("Time mais Goleador", 
                            highest_scoring['Time'],
                            f"{highest_scoring['Gols Pró']} gols ({round(highest_scoring['Gols Pró']/highest_scoring['Jogos'], 2)}/jogo)")
                
                with col3:
                    best_balance = df_standings.nlargest(1, 'Saldo').iloc[0]
                    st.metric("Melhor Saldo de Gols", 
                            best_balance['Time'],
                            best_balance['Saldo_Format'])
                    
        with data_tabs[1]:
            scorers_data = get_scorers(league_info['id'])
            if 'scorers' in scorers_data:
                st.subheader("Artilheiros da Competição")
                
                scorers_list = []
                for scorer in scorers_data['scorers']:
                    goals = scorer['goals']
                    matches = scorer.get('playedMatches', 0)
                    avg_goals = round(goals / matches, 2) if matches > 0 else 0
            
                    scorers_list.append({
                        'Jogador': scorer['player']['name'],
                        'Time': scorer['team']['name'],
                        'Gols': goals,
                        'Jogos': matches,
                        'Média': avg_goals
                    })
        
                df_scorers = pd.DataFrame(scorers_list)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    top_scorer = df_scorers.iloc[0]
                    st.metric("Artilheiro", 
                            f"{top_scorer['Jogador']} ({top_scorer['Time']})",
                            f"{top_scorer['Gols']} gols em {top_scorer['Jogos']} jogos")
        
                with col2:
                    st.metric("Média de Gols", 
                            f"{top_scorer['Média']} por jogo",
                            f"Total: {top_scorer['Gols']} gols")
        
                fig_scorers = px.bar(df_scorers,
                                x='Jogador',
                                y='Gols',
                                color='Time',
                                title='Gols por Jogador',
                                text='Gols')
        
                fig_scorers.update_layout(
                    xaxis_tickangle=-45,
                    showlegend=True,
                    height=500
                )
        
                fig_scorers.update_traces(textposition='outside')
        
                st.plotly_chart(fig_scorers, use_container_width=True)
        
                st.subheader("Tabela de Artilheiros")
                df_display = df_scorers.style.format({
                    'Média': '{:.2f}',
                    'Gols': '{:.0f}',
                    'Jogos': '{:.0f}'
                }).background_gradient(subset=['Gols', 'Média'], cmap='RdYlGn')
        
                st.dataframe(df_display, hide_index=True, width=800)

        with data_tabs[2]:
            if 'matches' in upcoming_matches:
                st.subheader("Próximas Partidas")
                upcoming_list = []
                for match in upcoming_matches['matches'][:5]:
                    home_team = next((team for team in standings_data['standings'][0]['table'] 
                                    if team['team']['name'] == match['homeTeam']['name']), None)
                    away_team = next((team for team in standings_data['standings'][0]['table'] 
                                    if team['team']['name'] == match['awayTeam']['name']), None)
                    
                    home_goal_diff = f"(SG: {home_team['goalDifference']:+d})" if home_team else ""
                    away_goal_diff = f"(SG: {away_team['goalDifference']:+d})" if away_team else ""
                    
                    match_date = datetime.strptime(match['utcDate'], '%Y-%m-%dT%H:%M:%SZ')
                    upcoming_list.append({
                        'Data': match_date.strftime('%d/%m/%Y'),
                        'Hora': match_date.strftime('%H:%M'),
                        'Mandante': f"{match['homeTeam']['name']} {home_goal_diff}",
                        'Visitante': f"{match['awayTeam']['name']} {away_goal_diff}"
                    })
                
                df_upcoming = pd.DataFrame(upcoming_list)
                st.dataframe(df_upcoming, hide_index=True, width=800)

        with data_tabs[3]:
            if 'matches' in finished_matches:
                st.subheader("Últimos Resultados")
                finished_list = []
                for match in finished_matches['matches'][-5:]:
                    home_team = next((team for team in standings_data['standings'][0]['table'] 
                                    if team['team']['name'] == match['homeTeam']['name']), None)
                    away_team = next((team for team in standings_data['standings'][0]['table'] 
                                    if team['team']['name'] == match['awayTeam']['name']), None)
                    
                    home_goal_diff = f"(SG: {home_team['goalDifference']:+d})" if home_team else ""
                    away_goal_diff = f"(SG: {away_team['goalDifference']:+d})" if away_team else ""
                    
                    finished_list.append({
                        'Data': datetime.strptime(match['utcDate'], '%Y-%m-%dT%H:%M:%SZ').strftime('%d/%m/%Y'),
                        'Mandante': f"{match['homeTeam']['name']} {home_goal_diff}",
                        'Placar': f"{match['score']['fullTime']['home']} x {match['score']['fullTime']['away']}",
                        'Visitante': f"{match['awayTeam']['name']} {away_goal_diff}"
                    })
                
                df_finished = pd.DataFrame(finished_list)
                st.dataframe(df_finished, hide_index=True, width=800)

st.markdown("---")
st.markdown(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")