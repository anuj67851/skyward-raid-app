import streamlit as st
import pandas as pd
import re

# --- 1. APP CONFIG & STYLING ---
st.set_page_config(page_title="Skyward Bond Roster", layout="wide")

# Custom CSS for a "Prettier" Tabular Look
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .role-badge { padding: 4px 8px; border-radius: 5px; font-weight: bold; font-size: 0.8rem; }
    .tank { background-color: #1f6feb; color: white; }
    .healer { background-color: #238636; color: white; }
    .debuffer { background-color: #8957e5; color: white; }
    .dps { background-color: #da3633; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA CONSTANTS ---
SHEET_ID = "1BX70II8RqaoFFby2PnTsf9_Ayu2CxBqCFNSVJNI88Wo"
GID = "169148548"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# --- 3. CORE LOGIC ---
@st.cache_data(ttl=300)
def get_data():
    df = pd.read_csv(CSV_URL)
    df.columns = [c.strip() for c in df.columns]
    return df

def classify_role(build):
    b = str(build)
    if "Stonesplit-Might (Tank)" in b: return '🛡️ Tank'
    if "Silkbind-Deluge (Healer)" in b: return '🌿 Healer'
    if "Bamboocut-Dust (Ropebrella)" in b: return '🎭 DeBuffer'
    return '⚔️ DPS'

def parse_time_logic(raw_str, tz="Pacific"):
    """
    Handles messy Google Form strings using Regex.
    Input: '12pm Pacific/3pm Eastern - 3pm/6pm'
    """
    if pd.isna(raw_str) or raw_str == "": return []

    slots = str(raw_str).split(',')
    cleaned_slots = []

    for slot in slots:
        # Regex to find times: [Time] Pacific/[Time] Eastern - [Time]/[Time]
        times = re.findall(r'(\d+[ap]m)', slot)
        if len(times) == 4:
            if tz == "Pacific":
                cleaned_slots.append(f"{times[0]} - {times[2]} PT")
            else:
                cleaned_slots.append(f"{times[1]} - {times[3]} ET")
        else:
            cleaned_slots.append(slot.strip())

    return cleaned_slots

# --- 4. DATA PROCESSING ---
df = get_data()
if not df.empty:
    # Set Roles
    df['Role'] = df.iloc[:, 4].apply(classify_role)

    # Sidebar Filters
    st.sidebar.header("🛡️ Roster Controls")

    # Day Selection
    day_options = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    sel_day = st.sidebar.selectbox("📅 Raid Day", day_options)
    day_col = [c for c in df.columns if sel_day in c][0]

    # Timezone Toggle
    tz_view = st.sidebar.radio("Timezone Display", ["Pacific", "Eastern"])

    # Clean the Day Column for the selected timezone
    df['DisplayTime'] = df[day_col].apply(lambda x: ", ".join(parse_time_logic(x, tz_view)))

    # Advanced Filters
    role_list = ['🛡️ Tank', '🌿 Healer', '🎭 DeBuffer', '⚔️ DPS']
    f_roles = st.sidebar.multiselect("Roles", role_list, default=role_list)

    # Time Slot Filter
    unique_times = sorted(list(set([t for sublist in df['DisplayTime'].str.split(', ') for t in sublist if t])))
    f_times = st.sidebar.multiselect("⏰ Time Slots", unique_times, default=unique_times)

    # Apply Filters
    mask = (df['Role'].isin(f_roles)) & (df['DisplayTime'] != "")
    f_df = df[mask].copy()

    # Filter by specific time slots (if time slot filter is used)
    if f_times:
        f_df = f_df[f_df['DisplayTime'].apply(lambda x: any(t in x for t in f_times))]

    # --- 5. MAIN DASHBOARD ---
    st.title(f"Skyward Bond: {sel_day} Roster")

    # Statistics Row
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Total", len(f_df))
    s2.metric("Tanks", len(f_df[f_df['Role'] == '🛡️ Tank']))
    s3.metric("Healers", len(f_df[f_df['Role'] == '🌿 Healer']))
    s4.metric("DeBuffer", len(f_df[f_df['Role'] == '🎭 DeBuffer']))
    s5.metric("DPS", len(f_df[f_df['Role'] == '⚔️ DPS']))

    st.divider()

    # Layout: Table + Chart
    col_table, col_chart = st.columns([3, 1])

    with col_chart:
        st.subheader("Role Balance")
        if not f_df.empty:
            role_counts = f_df['Role'].value_counts()
            st.bar_chart(role_counts, color="#1f6feb")

    with col_table:
        st.subheader("Available Members")
        if not f_df.empty:
            # Sorting logic
            role_order = {'🛡️ Tank': 0, '🌿 Healer': 1, '🎭 DeBuffer': 2, '⚔️ DPS': 3}
            f_df['sort'] = f_df['Role'].map(role_order)
            f_df = f_df.sort_values('sort')

            # Create a clean tabular dataframe for display
            display_df = f_df[[
                'Role',
                'Username',
                'DisplayTime',
                'Discord ID',
                'UID'
            ]].copy()

            display_df.columns = ['Role', 'Player Name', 'Availability', 'Discord', 'UID']

            # Use Streamlit's new built-in table (highly interactive)
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Role": st.column_config.TextColumn("Role", width="small"),
                    "Availability": st.column_config.TextColumn("Availability", width="large")
                }
            )
        else:
            st.warning("No players match your filters.")

else:
    st.error("Data connection failed.")