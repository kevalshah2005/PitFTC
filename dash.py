import streamlit as st
import requests
import pandas as pd
import constants
from datetime import datetime, timezone

MAX_MATCHES_DISPLAY = 5

FTCEVENTS_API_URL = "https://ftc-api.firstinspires.org/v2.0"
HEADERS = {"Authorization": f"Basic {constants.API_TOKEN}"}

RED = "#FF0000"
BLUE = "#0096FF"

# Function to predict winner based on OPR; for future use
def predict_winner(red_opr, blue_opr):
    red_score = sum(red_opr)
    blue_score = sum(blue_opr)
    return ("Red Alliance", red_score, blue_score) if red_score > blue_score else ("Blue Alliance", red_score, blue_score)

# Convert API timestamps to datetime objects
def parse_datetime(timestamp):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)

# Function to get the current match based on the modifiedOn field
def get_current_match(schedule_data, match_data):
    if not schedule_data or not match_data:
        return None  # No schedule or match data available

    if (len(match_data) >= len(schedule_data)):
        return None  # All matches have been played
    
    return schedule_data[len(match_data)]


st.set_page_config(layout="wide")

col1, col2, col3 = st.columns(3)

# TODO: Remove these defaults
season = col1.text_input("Enter Season Year:", "2024")
event_code = col2.text_input("Enter Event Code:", "ILCMPARC")
team_number = col3.text_input("Enter Team Number:", "14872")

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
    col1.subheader("Rankings")

    # Rankings dataframe
    rankings = fetch_rankings(season, event_code)
    if rankings:
        rankings_df = pd.DataFrame(rankings)
        
        # Add a new column 'Record' that combines Wins, Losses, and Ties
        rankings_df['Record'] = rankings_df.apply(
            lambda row: f"{row['wins']}-{row['losses']}-{row['ties']}", axis=1
        )

        # Rename columns for better display
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

    # Fetch schedule
    schedule_response = requests.get(
        f"{FTCEVENTS_API_URL}/{season}/schedule/{event_code}", 
        headers=HEADERS, 
        params={"tournamentLevel": "qual"}
    )
    schedule = schedule_response.json().get("schedule", [])

    # Fetch matches
    match_response = requests.get(
        f"{FTCEVENTS_API_URL}/{season}/matches/{event_code}", 
        headers=HEADERS
    )
    matches = match_response.json().get("matches", [])

    if schedule_response.status_code == 200 and match_response.status_code == 200:
        if schedule:
            current_match = get_current_match(schedule, matches)

            # Find all future matches for the team
            upcoming_team_matches = [
                match for match in schedule
                if current_match # If no current match, then no upcoming matches
                and any(team["teamNumber"] == int(team_number) for team in match["teams"])
                and match["matchNumber"] > current_match["matchNumber"]
            ]

            upcoming_team_match = min(upcoming_team_matches, default=None)

            time_until_next_match = parse_datetime(upcoming_team_match["startTime"]) - parse_datetime(current_match["startTime"]) if upcoming_team_match else None

            # Display current/next match and time until next match
            with col2:
                recent_match_text = f"Current Match:<br>{current_match['description']}" if current_match else "Current Match:<br> No Match Currently Playing"
                next_match_text = f"Next Match (Team {team_number}):<br>{upcoming_team_match['description']}<br>Estimated Time: {time_until_next_match}" if upcoming_team_match else f"Next Match (Team {team_number}):<br>No Upcoming Match"

                col2_1, col2_2 = st.columns(2)

                with col2_1:
                    st.markdown(
                        f"""
                        <div style="border: 2px solid #ddd; padding: 20px; border-radius: 8px; font-size: 24px; font-weight: bold; 
                                    display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; text-align: center;">
                            {recent_match_text}
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

            # Display each team in upcoming matches
            # TODO: remove logic for winner formatting - not needed since the matches HAVEN'T HAPPENED YET (nice one keval)
            for match in upcoming_team_matches[-MAX_MATCHES_DISPLAY:]:
                match_description = match["description"]
                red_teams = [team["teamNumber"] for team in match["teams"] if "Red" in team["station"]]
                blue_teams = [team["teamNumber"] for team in match["teams"] if "Blue" in team["station"]]
                red_score = match.get("scoreRedFinal", "?")
                blue_score = match.get("scoreBlueFinal", "?")

                # Determine winner for bold styling and text color
                if red_score != "?" and blue_score != "?":
                    if red_score > blue_score:
                        red_bold = "bold"
                        blue_bold = "normal"
                        red_color = RED
                        blue_color = "white"
                    elif blue_score > red_score:
                        red_bold = "normal"
                        blue_bold = "bold"
                        red_color = "white"
                        blue_color = BLUE
                    else:
                        red_bold = "normal"
                        blue_bold = "normal"
                        red_color = RED
                        blue_color = BLUE
                else:
                    red_bold = "normal"
                    blue_bold = "normal"
                    red_color = RED
                    blue_color = BLUE

                col2.markdown(
                    f"""
                    <div style="border: 2px solid #ddd; padding: 6px 12px; margin: 5px 0; border-radius: 8px; 
                                display: flex; justify-content: space-between; align-items: center; font-size: 16px;">
                        <b>{match_description}:</b> 
                        <span style="color: {red_color}; font-weight: {red_bold};"><b>🔴 {', '.join(map(str, red_teams))}</b></span> 
                        <span style="color: {red_color}; font-weight: {red_bold}; font-size: 18px;">{red_score}</span> 
                        <b>-</b> 
                        <span style="color: {blue_color}; font-weight: {blue_bold}; font-size: 18px;">{blue_score}</span>  
                        <span style="color: {blue_color}; font-weight: {blue_bold};"><b>🔵 {', '.join(map(str, blue_teams))}</b></span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


            st.subheader(f"Team {team_number} Statistics")

            # Get team record
            team_rank_data = next((team for team in rankings if str(team["teamNumber"]) == team_number), None)

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
                col2_1, col2_2, col2_3, col2_4 = st.columns(4)

                with col2_1:
                    st.markdown(f"<h2 style='text-align: center;'>{0}</h2>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align: center;'>Total</p>", unsafe_allow_html=True)

                with col2_2:
                    st.markdown(f"<h2 style='text-align: center;'>{0}</h2>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align: center;'>Auto</p>", unsafe_allow_html=True)

                with col2_3:
                    st.markdown(f"<h2 style='text-align: center;'>{0}</h2>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align: center;'>TeleOp</p>", unsafe_allow_html=True)

                with col2_4:
                    st.markdown(f"<h2 style='text-align: center;'>{0}</h2>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align: center;'>Endgame</p>", unsafe_allow_html=True)

            # Display OPR Rankings
            with col3:
                st.markdown("<h3 style='text-align: center;'>Rankings</h3>", unsafe_allow_html=True)
                col2_1, col2_2, col2_3 = st.columns(3)

                with col2_1:
                    st.markdown(f"<h2 style='text-align: center;'>{'0/0'}</h2>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align: center;'>World</p>", unsafe_allow_html=True)

                with col2_2:
                    st.markdown(f"<h2 style='text-align: center;'>{'0/0'}</h2>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align: center;'>Country</p>", unsafe_allow_html=True)

                with col2_3:
                    st.markdown(f"<h2 style='text-align: center;'>{'0/0'}</h2>", unsafe_allow_html=True)
                    st.markdown("<p style='text-align: center;'>Region</p>", unsafe_allow_html=True)


    elif schedule_response.status_code == 200:
        st.error(f"Failed to fetch match data. Status Code: {match_response.status_code}")
    elif match_response.status_code == 200:
        st.error(f"Failed to fetch schedule data. Status Code: {schedule_response.status_code}")
    else:
        st.error(f"Failed to fetch match and schedule data. Status Code: Schedule: {schedule_response.status_code} and Match: {match_response.status_code}")
