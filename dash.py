import streamlit as st
import requests
import pandas as pd
import constants

MAX_MATCHES_DISPLAY = 5

FTCEVENTS_API_URL = "https://ftc-api.firstinspires.org/v2.0"
HEADERS = {"Authorization": f"Basic {constants.API_TOKEN}"}

# Function to predict winner based on OPR; for future use
def predict_winner(red_opr, blue_opr):
    red_score = sum(red_opr)
    blue_score = sum(blue_opr)
    return ("Red Alliance", red_score, blue_score) if red_score > blue_score else ("Blue Alliance", red_score, blue_score)

st.set_page_config(layout="wide")

col1, col2, col3 = st.columns(3)

# TODO: Remove these defaults
season = col1.text_input("Enter Season Year:", "2024")
event_code = col2.text_input("Enter Event Code:", "USNCCMP")
team_number = col3.text_input("Enter Team Number:", "10195")

col1, col2 = st.columns([2, 3])

def fetch_rankings(season, event_code):
    url = f"{FTCEVENTS_API_URL}/{season}/rankings/{event_code}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("rankings", [])
    else:
        st.error(f"Failed to fetch rankings. Status Code: {response.status_code}")
        return []

if season and event_code and team_number:
    # Fetch Rankings
    col1.subheader("Rankings")
    rankings = fetch_rankings(season, event_code)
    if rankings:
        rankings_df = pd.DataFrame(rankings)
        
        # Add a new column 'Record' that combines Wins, Losses, and Ties
        rankings_df['Record'] = rankings_df.apply(
            lambda row: f"{row['wins']}-{row['losses']}-{row['ties']}", axis=1
        )

        # Renaming columns for better display
        rankings_df.rename(columns={
            "rank": "Rank",
            "teamNumber": "Team Number",
            "teamName": "Team Name",
            "wins": "Wins",
            "losses": "Losses",
            "ties": "Ties",
            "sortOrder2": "TBP1",
            "sortOrder3": "TBP2"
        }, inplace=True)
        
        if not rankings_df.empty:
            col1.dataframe(rankings_df[['Rank', 'Team Number', 'Team Name', 'Record', 'TBP1', 'TBP2']], hide_index=True)
        else:
            col1.write("No ranking data available.")

    # Fetch Matches
    matches_response = requests.get(f"{FTCEVENTS_API_URL}/{season}/matches/{event_code}?team={team_number}", headers=HEADERS)
    if matches_response.status_code == 200:
        data = matches_response.json()
        matches = data.get("matches", [])

        if matches:
            # Find the first match that is not completed yet (current match)
            current_match = next(
                (match for match in matches if match["postResultTime"] is None),
                None  # If all matches are completed
            )

            # Find the next match for the team
            team_matches = [match for match in matches if any(team["teamNumber"] == int(team_number) for team in match["teams"])]
            upcoming_team_match = next(
                (match for match in team_matches if match["postResultTime"] is None),
                None  # If no upcoming match
            )

            # Display Current and Next Match
            with col2:
                current_match_text = f"Current Match:<br>{current_match['description']}" if current_match else "Current Match:<br>All Matches Completed"
                next_match_text = f"Next Match (Team {team_number}):<br>{upcoming_team_match['description']}" if upcoming_team_match else f"Next Match (Team {team_number}):<br>No Upcoming Match"
                
                col2_1, col2_2 = st.columns(2)

                with col2_1:
                    st.markdown(
                        f"""
                        <div style="border: 2px solid #ddd; padding: 20px; border-radius: 8px; font-size: 24px; font-weight: bold; 
                                    display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; text-align: center;">
                            {current_match_text}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with col2_2:
                    st.markdown(
                        f"""
                        <div style="border: 2px solid #ddd; padding: 20px; border-radius: 8px; font-size: 24px; font-weight: bold; 
                                    display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; text-align: center;">
                            {next_match_text}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            
            col2.subheader("Upcoming Matches")

            # Filter matches by team number
            if team_number:
                filtered_matches = [match for match in matches if any(team["teamNumber"] == int(team_number) for team in match["teams"])]
            else:
                filtered_matches = matches

            for match in filtered_matches[-MAX_MATCHES_DISPLAY:]:
                match_description = match["description"]
                red_teams = [team["teamNumber"] for team in match["teams"] if "Red" in team["station"]]
                blue_teams = [team["teamNumber"] for team in match["teams"] if "Blue" in team["station"]]
                red_score = match.get("scoreRedFinal", "?")
                blue_score = match.get("scoreBlueFinal", "?")

                # Determine winner for bold styling
                if red_score != "?" and blue_score != "?":
                    red_bold = "bold" if red_score > blue_score else "normal"
                    blue_bold = "bold" if blue_score > red_score else "normal"
                else:
                    red_bold = "normal"
                    blue_bold = "normal"

                col2.markdown(
                    f"""
                    <div style="border: 2px solid #ddd; padding: 6px 12px; margin: 5px 0; border-radius: 8px; 
                                display: flex; justify-content: space-between; align-items: center; font-size: 16px;">
                        <b>{match_description}:</b> 
                        <span style="color: #FF0000;"><b>🔴 {', '.join(map(str, red_teams))}</b></span> 
                        <span style="color: #FF0000; font-weight: {red_bold}; font-size: 18px;">{red_score}</span> 
                        <b>-</b> 
                        <span style="color: #0096FF; font-weight: {blue_bold}; font-size: 18px;">{blue_score}</span>  
                        <span style="color: #0096FF;"><b>🔵 {', '.join(map(str, blue_teams))}</b></span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.subheader(f"Team {team_number} Statistics")

        team_rank_data = next((team for team in rankings if str(team["teamNumber"]) == team_number), None)

        # Get team record
        if team_rank_data:
            wins = team_rank_data['wins']
            losses = team_rank_data['losses']
            ties = team_rank_data['ties']
        else:
            wins, losses, ties = 0, 0, 0

        col1, col2, col3 = st.columns(3)

        # Display record
        with col1:
            st.markdown("<h3 style='text-align: center; margin: auto;'>Record</h3>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center; margin: auto;'>{wins} - {losses} - {ties}</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; margin: auto;'>Wins - Losses - Ties</p>", unsafe_allow_html=True)

        # Display OPR Stats
        with col2:
            st.markdown("<h3 style='text-align: center;'>OPR Stats</h3>", unsafe_allow_html=True)
            subcol1, subcol2, subcol3, subcol4 = st.columns(4)  # Four equal sub-columns

            with subcol1:
                st.markdown(f"<h2 style='text-align: center;'>{0}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center;'>Total</p>", unsafe_allow_html=True)

            with subcol2:
                st.markdown(f"<h2 style='text-align: center;'>{0}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center;'>Auto</p>", unsafe_allow_html=True)

            with subcol3:
                st.markdown(f"<h2 style='text-align: center;'>{0}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center;'>TeleOp</p>", unsafe_allow_html=True)

            with subcol4:
                st.markdown(f"<h2 style='text-align: center;'>{0}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center;'>Endgame</p>", unsafe_allow_html=True)

        # Display OPR Rankings
        with col3:
            st.markdown("<h3 style='text-align: center;'>Rankings</h3>", unsafe_allow_html=True)
            subcol1, subcol2, subcol3 = st.columns(3)  # Three equal sub-columns

            with subcol1:
                st.markdown(f"<h2 style='text-align: center;'>{'0/0'}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center;'>World</p>", unsafe_allow_html=True)

            with subcol2:
                st.markdown(f"<h2 style='text-align: center;'>{'0/0'}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center;'>Country</p>", unsafe_allow_html=True)

            with subcol3:
                st.markdown(f"<h2 style='text-align: center;'>{'0/0'}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center;'>Region</p>", unsafe_allow_html=True)


    else:
        st.error(f"Failed to fetch match data. Status Code: {matches_response.status_code}")
