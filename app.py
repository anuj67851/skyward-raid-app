import streamlit as st
import pandas as pd
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Skyward Bond Raid Lead", layout="wide")

SHEET_ID = "1BX70II8RqaoFFby2PnTsf9_Ayu2CxBqCFNSVJNI88Wo"
GID = "169148548"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# --- DATA ENGINE ---
@st.cache_data(ttl=300)
def get_live_data():
    try:
        data = pd.read_csv(CSV_URL)
        data.columns = [c.strip() for c in data.columns]
        return data
    except Exception as e:
        st.error(f"Error connecting to data: {e}")
        return pd.DataFrame()

# --- UPDATED ROLE LOGIC ---
def classify_role(build_text):
    text = str(build_text).strip()
    if "Stonesplit-Might (Tank)" in text:
        return '🛡️ Tank'
    elif "Silkbind-Deluge (Healer)" in text:
        return '🌿 Healer'
    elif "Bamboocut-Dust (Ropebrella)" in text:
        return '🎭 Buffer DPS'
    else:
        return '⚔️ DPS'

def clean_time_string(time_str, tz_pref="Pacific"):
    if pd.isna(time_str) or time_str == "": return ""
    parts = str(time_str).split('-')
    if len(parts) < 2: return time_str
    start_part, end_part = parts[0].strip(), parts[1].strip()
    try:
        if tz_pref == "Pacific":
            start = start_part.split(' ')[0]
            end = end_part.split('/')[0]
            return f"{start} - {end} PT"
        else:
            start = start_part.split('/')[1].split(' ')[0]
            end = end_part.split('/')[1]
            return f"{start} - {end} ET"
    except:
        return time_str

def extract_dps(dps_val):
    try:
        clean_val = str(dps_val).replace(',', '').lower()
        match = re.search(r'(\d+\.?\d*)', clean_val)
        if match:
            num = float(match.group(1))
            if 'k' in clean_val and num < 1000: num *= 1000
            return num
        return 0
    except:
        return 0

# --- MAIN APP ---
df = get_live_data()

if not df.empty:
    df['Role'] = df.iloc[:, 4].apply(classify_role)
    df['Clean_DPS'] = df.iloc[:, 8].apply(extract_dps)

    # Sidebar
    st.sidebar.title("🛠️ Raid Management")
    tz_choice = st.sidebar.radio("Timezone View", ["Pacific", "Eastern"])

    day_options = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    selected_day = st.sidebar.selectbox("📅 Choose Raid Day", day_options)
    day_col_name = [c for c in df.columns if selected_day in c][0]

    # Detailed Filters
    all_roles = ['🛡️ Tank', '🌿 Healer', '🎭 DeBuffer', '⚔️ DPS']
    role_filter = st.sidebar.multiselect("Filter Roles", options=all_roles, default=all_roles)

    # Filtering Logic
    filtered_df = df[
        (df[day_col_name].notna()) &
        (df[day_col_name] != "") &
        (df['Role'].isin(role_filter))
        ].copy()

    # --- UI DISPLAY ---
    st.title(f"Skyward Bond: {selected_day} Roster")

    col_stats, col_chart = st.columns([3, 1])

    with col_stats:
        # Metrics: Total, Tank, Healer, DeBuffer, DPS
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total", len(filtered_df))
        m2.metric("Tanks", len(filtered_df[filtered_df['Role'] == '🛡️ Tank']))
        m3.metric("Healers", len(filtered_df[filtered_df['Role'] == '🌿 Healer']))
        m4.metric("DeBuffer", len(filtered_df[filtered_df['Role'] == '🎭 DeBuffer']))
        m5.metric("DPS", len(filtered_df[filtered_df['Role'] == '⚔️ DPS']))

        # Discord Copy Box
        if not filtered_df.empty:
            discord_list = ", ".join([f"@{name}" for name in filtered_df['Discord ID'].tolist()])
            st.text_area("Discord Pings (Filter updates this list automatically)", discord_list, height=80)

    with col_chart:
        if not filtered_df.empty:
            role_counts = filtered_df['Role'].value_counts()
            st.bar_chart(role_counts)

    st.divider()

    # --- ROSTER LIST ---
    if not filtered_df.empty:
        # Define the priority of roles in the list
        role_order = {'🛡️ Tank': 0, '🌿 Healer': 1, '🎭 Buffer DPS': 2, '⚔️ DPS': 3}
        filtered_df['order'] = filtered_df['Role'].map(role_order)
        filtered_df = filtered_df.sort_values(['order', 'Clean_DPS'], ascending=[True, False])

        for _, row in filtered_df.iterrows():
            display_time = clean_time_string(row[day_col_name], tz_choice)

            # Using specific emoji logic for the color of the expander
            with st.expander(f"{row['Role']} | {row['Username']} | ⏱️ {display_time}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write("**Contact**")
                    st.code(row['Discord ID'])
                    st.write(f"Server: {row.iloc[7]}")
                with c2:
                    st.write("**Full Build String**")
                    st.info(row.iloc[4])
                with c3:
                    st.write("**Performance**")
                    st.write(f"Parse: {row.iloc[8]}")
                    if row['Clean_DPS'] > 0:
                        st.progress(min(row['Clean_DPS']/60000, 1.0), text=f"{int(row['Clean_DPS'])} DPS")
    else:
        st.warning(f"No sign-ups found for {selected_day}.")

else:
    st.info("Loading data from Skyward Bond Master Sheet...")