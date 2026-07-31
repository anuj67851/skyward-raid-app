import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Skyward Bond Raid Lead", layout="wide")

SHEET_ID = "1BX70II8RqaoFFby2PnTsf9_Ayu2CxBqCFNSVJNI88Wo"
GID = "169148548"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=300)
def get_live_data():
    try:
        data = pd.read_csv(CSV_URL)
        data.columns = [c.strip() for c in data.columns]
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

# --- REFINED ROLE LOGIC ---
def classify_role(build_text):
    text = str(build_text).strip()
    if "Stonesplit-Might (Tank)" in text:
        return '🛡️ Tank'
    elif "Silkbind-Deluge (Healer)" in text:
        return '🌿 Healer'
    else:
        return '⚔️ DPS'

df = get_live_data()

if not df.empty:
    # 1. Setup Roles
    df['Role'] = df.iloc[:, 4].apply(classify_role)

    # 2. Sidebar Filters
    st.sidebar.title("Search Filters")

    # Day Filter
    day_options = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    selected_day = st.sidebar.selectbox("📅 Select Raid Day", day_options)

    # Identify the correct column for the day
    day_col_name = [c for c in df.columns if selected_day in c][0]

    # Server Filter
    server_col = df.columns[7]
    servers = sorted(df[server_col].dropna().unique())
    server_filter = st.sidebar.multiselect("Server", options=servers, default=servers)

    # Role Filter
    role_filter = st.sidebar.multiselect("Roles", options=['🛡️ Tank', '🌿 Healer', '⚔️ DPS'], default=['🛡️ Tank', '🌿 Healer', '⚔️ DPS'])

    # 3. Time Filter Logic
    # We extract all unique time slots mentioned in that specific day's column
    all_times = df[day_col_name].dropna().str.split(',').explode().str.strip().unique()
    all_times = [t for t in all_times if t] # Remove empty strings

    selected_times = st.sidebar.multiselect("⏰ Specific Time Slots", options=sorted(all_times), default=sorted(all_times))

    # 4. Filtering Engine
    def check_time(row_val):
        if pd.isna(row_val) or row_val == "": return False
        # Check if any of the user's selected time slots exist in this person's row
        row_slots = [s.strip() for s in str(row_val).split(',')]
        return any(slot in selected_times for slot in row_slots)

    filtered_df = df[
        (df[server_col].isin(server_filter)) &
        (df['Role'].isin(role_filter)) &
        (df[day_col_name].apply(check_time))
        ]

    # 5. UI DISPLAY
    st.title(f"🛡️ Skyward Bond: {selected_day} Roster")

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Match", len(filtered_df))
    m2.metric("Tanks", len(filtered_df[filtered_df['Role'] == '🛡️ Tank']))
    m3.metric("Healers", len(filtered_df[filtered_df['Role'] == '🌿 Healer']))
    m4.metric("DPS", len(filtered_df[filtered_df['Role'] == '⚔️ DPS']))

    st.divider()

    if not filtered_df.empty:
        # Sort by Role: Tanks -> Healers -> DPS
        role_order = {'🛡️ Tank': 0, '🌿 Healer': 1, '⚔️ DPS': 2}
        filtered_df['order'] = filtered_df['Role'].map(role_order)
        filtered_df = filtered_df.sort_values('order')

        for _, row in filtered_df.iterrows():
            # FIXED: Used row.iloc[7] instead of row.iloc[:, 7]
            with st.expander(f"{row['Role']} | {row['Username']} ({row.iloc[7]})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Member Availability:**")
                    # Highlight the specific time slots
                    slots = str(row[day_col_name]).split(',')
                    for s in slots:
                        st.info(f"🕒 {s.strip()}")

                    st.write(f"**Builds:** {row.iloc[4]}")
                with c2:
                    st.write(f"**Discord:** `{row['Discord ID']}`")
                    st.write(f"**UID:** `{row['UID']}`")
                    st.write(f"**Best Parse:** {row.iloc[8]}")
    else:
        st.warning("No players found matching those specific filters.")

else:
    st.error("Could not load data. Check if the Google Sheet link is still public.")