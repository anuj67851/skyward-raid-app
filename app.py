import streamlit as st
import pandas as pd
import re

# --- 1. APP CONFIG & STYLING ---
st.set_page_config(page_title="Skyward Bond Raid Manager", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    div[data-testid="stMetricValue"] { font-size: 26px; color: #58a6ff; font-weight: bold; }
    div[data-testid="stMetric"] { 
        background-color: #161b22; 
        border: 1px solid #30363d; 
        padding: 15px; 
        border-radius: 10px; 
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
        st.error(f"Sheet Connection Error: {e}")
        return pd.DataFrame()

# --- 3. STRICT ROLE LOGIC ---
def get_role_list(build_text):
    text = str(build_text)
    roles = []
    if "Stonesplit-Might (Tank)" in text: roles.append('🛡️ Tank')
    if "Silkbind-Deluge (Healer)" in text: roles.append('🌿 Healer')
    if "Bamboocut-Dust (Ropebrella)" in text: roles.append('🎭 Debuffer')

    # Check for any remaining text to classify as DPS
    rem = text.replace("Stonesplit-Might (Tank)", "").replace("Silkbind-Deluge (Healer)", "").replace("Bamboocut-Dust (Ropebrella)", "").replace(",", "").strip()
    if rem or not roles:
        roles.append('⚔️ DPS')
    return list(set(roles))

def get_build_with_icons(build_text):
    text = str(build_text)
    icons = []
    if "Stonesplit-Might (Tank)" in text: icons.append('🛡️')
    if "Silkbind-Deluge (Healer)" in text: icons.append('🌿')
    if "Bamboocut-Dust (Ropebrella)" in text: icons.append('🎭')

    dps_classes = ["Nameless", "Strat", "Heng", "Gauntlets", "Fanbrella"]
    if any(d in text for d in dps_classes) or not icons:
        icons.append('⚔️')

    unique_icons = "".join(list(dict.fromkeys(icons)))
    return f"{unique_icons} {text}"

def clean_times(raw_str, tz="Pacific"):
    if pd.isna(raw_str) or str(raw_str).strip() == "": return []
    raw_slots = str(raw_str).split(',')
    cleaned = []
    for slot in raw_slots:
        times = re.findall(r'(\d+[ap]m)', slot)
        if len(times) == 4:
            if tz == "Pacific": cleaned.append(f"{times[0]}-{times[2]} PT")
            else: cleaned.append(f"{times[1]}-{times[3]} ET")
        else:
            cleaned.append(slot.strip())
    return cleaned

# --- 4. DATA PROCESSING ---
df = get_data()

if not df.empty:
    df['Roles_List'] = df.iloc[:, 4].apply(get_role_list)
    df['Icon_Build'] = df.iloc[:, 4].apply(get_build_with_icons)

    tab_roster, tab_search = st.tabs(["📅 Daily Roster", "🔍 Player Lookup"])

    # --- TAB 1: DAILY ROSTER ---
    with tab_roster:
        st.sidebar.header("🕹️ Roster Filters")
        day_options = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        sel_day = st.sidebar.selectbox("Select Raid Day", day_options)
        day_col = [c for c in df.columns if sel_day in c][0]
        tz_view = st.sidebar.radio("Timezone", ["Pacific", "Eastern"])

        # Time Filter logic
        df['Daily_Avail'] = df[day_col].apply(lambda x: clean_times(x, tz_view))
        all_times = sorted(list(set([t for sublist in df['Daily_Avail'] for t in sublist])))
        f_times = st.sidebar.multiselect("⏰ Time Slots", all_times, default=all_times)

        # Role Filter
        role_types = ['🛡️ Tank', '🌿 Healer', '🎭 Debuffer', '⚔️ DPS']
        f_roles = st.sidebar.multiselect("Roles", role_types, default=role_types)

        # Application of Filters
        mask = (df['Daily_Avail'].apply(lambda x: any(t in f_times for t in x))) & \
               (df['Roles_List'].apply(lambda x: any(r in f_roles for r in x)))
        f_df = df[mask].copy()

        st.title(f"{sel_day} Roster Sign-ups")

        # Metrics Summary
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total", len(f_df))
        m2.metric("Tanks", len(f_df[f_df['Roles_List'].apply(lambda x: '🛡️ Tank' in x)]))
        m3.metric("Healers", len(f_df[f_df['Roles_List'].apply(lambda x: '🌿 Healer' in x)]))
        m4.metric("Debuffer", len(f_df[f_df['Roles_List'].apply(lambda x: '🎭 Debuffer' in x)]))
        m5.metric("DPS", len(f_df[f_df['Roles_List'].apply(lambda x: '⚔️ DPS' in x)]))

        st.divider()

        if not f_df.empty:
            f_df['Display_Time'] = f_df['Daily_Avail'].apply(lambda x: ", ".join(x))

            # Priority Sort
            role_prio = {'🛡️ Tank': 0, '🌿 Healer': 1, '🎭 Debuffer': 2, '⚔️ DPS': 3}
            f_df['sort_val'] = f_df['Roles_List'].apply(lambda x: min([role_prio.get(r, 4) for r in x]))
            f_df = f_df.sort_values('sort_val')

            # Roster Table Display
            st.dataframe(
                f_df[['Icon_Build', 'Username', 'Display_Time', 'Discord ID', 'UID']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Icon_Build": st.column_config.TextColumn("Build / Class", width="medium"),
                    "Display_Time": st.column_config.TextColumn("Available Slots", width="medium"),
                }
            )
        else:
            st.warning("No sign-ups match these filters.")

    # --- TAB 2: PLAYER LOOKUP ---
    with tab_search:
        st.header("🔍 Member Lookup")
        p_name = st.selectbox("Search Player", sorted(df['Username'].unique()))

        if p_name:
            p = df[df['Username'] == p_name].iloc[0]

            # Simple Member Info Header
            st.markdown(f"### Player: {p['Username']}")

            info_col, _ = st.columns([2, 1])
            with info_col:
                st.write(f"**Discord:** `{p['Discord ID']}`")
                st.write(f"**UID:** `{p['UID']}`")
                st.write(f"**Server:** {p.iloc[7]}")
                st.write(f"**Builds:** {p['Icon_Build']}")

            st.divider()

            # Weekly Schedule
            st.markdown("### Weekly Availability")
            sched = []
            for d in day_options:
                c = [col for col in df.columns if d in col][0]
                sched.append({
                    "Day": d,
                    "Pacific": ", ".join(clean_times(p[c], "Pacific")) or "❌",
                    "Eastern": ", ".join(clean_times(p[c], "Eastern")) or "❌"
                })
            st.table(pd.DataFrame(sched))

else:
    st.error("Could not connect to Google Sheet.")