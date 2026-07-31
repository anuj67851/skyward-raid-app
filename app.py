import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Skyward Bond Raid Lead", layout="wide", initial_sidebar_state="expanded")

# This is the direct CSV export link for your specific sheet and tab (gid)
SHEET_ID = "1BX70II8RqaoFFby2PnTsf9_Ayu2CxBqCFNSVJNI88Wo"
GID = "169148548"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# --- DATA ENGINE ---
@st.cache_data(ttl=300)  # Refreshes every 5 minutes
def get_live_data():
    try:
        data = pd.read_csv(CSV_URL)
        # Standardize column names
        data.columns = [c.strip() for c in data.columns]
        return data
    except Exception as e:
        st.error(f"Unable to connect to Google Sheets: {e}")
        return pd.DataFrame()

def classify_role(build_text):
    text = str(build_text).lower()
    if any(word in text for word in ['tank', 'might']): return '🛡️ Tank'
    if any(word in text for word in ['healer', 'deluge', 'silkbind']): return '🌿 Healer'
    return '⚔️ DPS'

# --- APP UI ---
df = get_live_data()

if not df.empty:
    # 1. Process Roles based on the 5th column (Builds)
    build_col = df.columns[4]
    df['Role'] = df[build_col].apply(classify_role)

    # 2. Sidebar Filters
    st.sidebar.title("Filters")
    day_options = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    selected_day = st.sidebar.selectbox("Choose a Day", day_options)

    server_filter = st.sidebar.multiselect("Server", options=df.iloc[:, 7].unique(), default=df.iloc[:, 7].unique())
    role_filter = st.sidebar.multiselect("Roles", options=['🛡️ Tank', '🌿 Healer', '⚔️ DPS'], default=['🛡️ Tank', '🌿 Healer', '⚔️ DPS'])

    # 3. Filter the Data
    # Find the specific column for the selected day
    day_col_name = [c for c in df.columns if selected_day in c][0]

    filtered_df = df[
        (df[day_col_name].notna()) &
        (df[day_col_name] != "") &
        (df.iloc[:, 7].isin(server_filter)) &
        (df['Role'].isin(role_filter))
        ]

    # 4. Main Dashboard
    st.title(f"📅 {selected_day} Availability")

    # Stats Overview
    tanks = len(filtered_df[filtered_df['Role'] == '🛡️ Tank'])
    healers = len(filtered_df[filtered_df['Role'] == '🌿 Healer'])
    dps = len(filtered_df[filtered_df['Role'] == '⚔️ DPS'])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Available", len(filtered_df))
    m2.metric("Tanks", tanks)
    m3.metric("Healers", healers)
    m4.metric("DPS", dps)

    st.divider()

    # 5. Display User Cards
    if not filtered_df.empty:
        # Sort by Role
        filtered_df = filtered_df.sort_values("Role")

        for _, row in filtered_df.iterrows():
            with st.expander(f"{row['Role']} | {row['Username']} ({row.iloc[:, 7]})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Availability Window:**")
                    st.info(row[day_col_name])
                    st.write(f"**Builds:** {row.iloc[:, 4]}")
                with c2:
                    st.write(f"**Discord:** `{row['Discord ID']}`")
                    st.write(f"**UID:** `{row['UID']}`")
                    st.write(f"**Parse/DPS:** {row.iloc[:, 8]}")
    else:
        st.warning(f"No one matches these filters for {selected_day}.")

else:
    st.info("The application is loading... please wait.")