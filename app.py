import streamlit as st
import pandas as pd
import re

# --- 1. APP CONFIG & STYLING ---
st.set_page_config(page_title="Skyward Bond Raid Manager", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #58a6ff; }
    div[data-testid="stMetric"] { 
        background-color: #161b22; 
        border: 1px solid #30363d; 
        padding: 10px; 
        border-radius: 8px; 
    }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
SHEET_ID = "1BX70II8RqaoFFby2PnTsf9_Ayu2CxBqCFNSVJNI88Wo"
GID = "169148548"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=300)
def get_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Failed to fetch sheet: {e}")
        return pd.DataFrame()

def get_player_roles(build_text):
    """Returns a list of roles found in the build text"""
    text = str(build_text)
    roles = []
    if "Stonesplit-Might (Tank)" in text: roles.append('🛡️ Tank')
    if "Silkbind-Deluge (Healer)" in text: roles.append('🌿 Healer')
    if "Bamboocut-Dust (Ropebrella)" in text: roles.append('🎭 Buffer')
    # If it contains none of the above or other text, it's DPS
    if not roles or any(x in text for x in ["Nameless", "Strat", "Heng", "Gauntlets", "Fanbrella"]):
        roles.append('⚔️ DPS')
    return list(set(roles))

def clean_times(raw_str, tz="Pacific"):
    if pd.isna(raw_str) or str(raw_str).strip() == "": return []
    raw_slots = str(raw_str).split(',')
    cleaned = []
    for slot in raw_slots:
        times = re.findall(r'(\d+[ap]m)', slot)
        if len(times) == 4:
            if tz == "Pacific": cleaned.append(f"{times[0]}-{times[2]} PT")
            else: cleaned.append(f"{times[1]}-{times[3]} ET")
        else: cleaned.append(slot.strip())
    return cleaned

# --- 3. LOAD DATA ---
df = get_data()

if not df.empty:
    # Pre-process columns
    df['Detected_Roles'] = df.iloc[:, 4].apply(get_player_roles)

    # Create Tabs
    tab1, tab2 = st.tabs(["📅 Daily Roster", "🔍 Player Lookup"])

    # --- TAB 1: DAILY ROSTER ---
    with tab1:
        st.sidebar.header("📅 Roster Filters")
        day_options = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        sel_day = st.sidebar.selectbox("Select Day", day_options)
        day_col = [c for c in df.columns if sel_day in c][0]
        tz_view = st.sidebar.radio("View Timezone", ["Pacific", "Eastern"])

        # Role filter: uses the list of detected roles
        all_role_types = ['🛡️ Tank', '🌿 Healer', '🎭 Buffer', '⚔️ DPS']
        f_roles = st.sidebar.multiselect("Show Roles", all_role_types, default=all_role_types)

        # Process availability
        df['Daily_Avail'] = df[day_col].apply(lambda x: clean_times(x, tz_view))

        # Filtering
        mask = (df['Daily_Avail'].apply(len) > 0) & \
               (df['Detected_Roles'].apply(lambda x: any(r in f_roles for r in x)))
        f_df = df[mask].copy()

        # Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Players", len(f_df))
        m2.metric("Tanks", len(f_df[f_df['Detected_Roles'].apply(lambda x: '🛡️ Tank' in x)]))
        m3.metric("Heals", len(f_df[f_df['Detected_Roles'].apply(lambda x: '🌿 Healer' in x)]))
        m4.metric("Buff", len(f_df[f_df['Detected_Roles'].apply(lambda x: '🎭 Buffer' in x)]))
        m5.metric("DPS", len(f_df[f_df['Detected_Roles'].apply(lambda x: '⚔️ DPS' in x)]))

        st.divider()

        if not f_df.empty:
            # Table View
            f_df['Display Avail'] = f_df['Daily_Avail'].apply(lambda x: ", ".join(x))

            # Sort by Roles (Tanks first)
            f_df['sort_val'] = f_df['Detected_Roles'].apply(lambda x: min([all_role_types.index(r) for r in x if r in all_role_types] or [99]))
            f_df = f_df.sort_values('sort_val')

            st.dataframe(
                f_df[[df.columns[4], 'Username', 'Display Avail', 'Discord ID', 'UID']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    df.columns[4]: st.column_config.TextColumn("Builds / Classes", width="medium"),
                    "Display Avail": st.column_config.TextColumn("Time Slot", width="small")
                }
            )

            # Simple Chart
            st.subheader("Role Distribution")
            role_counts = pd.Series([r for sublist in f_df['Detected_Roles'] for r in sublist]).value_counts()
            st.bar_chart(role_counts, color="#58a6ff")
        else:
            st.warning(f"No sign-ups for {sel_day}.")

    # --- TAB 2: PLAYER LOOKUP ---
    with tab2:
        st.subheader("Search Member Data")
        search_name = st.selectbox("Select or Type Player Name", options=sorted(df['Username'].unique()))

        if search_name:
            p_data = df[df['Username'] == search_name].iloc[0]

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"### Player: {p_data['Username']}")
                st.write(f"**Builds:** {p_data.iloc[4]}")
                st.write(f"**Discord:** `{p_data['Discord ID']}`")
                st.write(f"**UID:** `{p_data['UID']}`")
                st.write(f"**Server:** {p_data.iloc[7]}")

            with c2:
                st.markdown("### Performance")
                st.info(f"**Best Parse:** {p_data.iloc[8]}")
                st.write(f"**Guild Tech Maxed:** {p_data.iloc[9]}")

            st.divider()
            st.markdown("### Weekly Schedule")

            # Create a small table for their weekly availability
            week_data = []
            for day in day_options:
                col = [c for c in df.columns if day in c][0]
                raw_time = p_data[col]
                pt_times = clean_times(raw_time, "Pacific")
                et_times = clean_times(raw_time, "Eastern")

                week_data.append({
                    "Day": day,
                    "Pacific Time": ", ".join(pt_times) if pt_times else "---",
                    "Eastern Time": ", ".join(et_times) if et_times else "---"
                })

            st.table(pd.DataFrame(week_data))

else:
    st.error("Data could not be loaded from Google Sheets.")