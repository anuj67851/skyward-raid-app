import streamlit as st
import pandas as pd
from utils import ROLES_CONFIG, ROLE_PRIORITY, ROLE_COLORS, DAYS, get_roles, get_build_display, clean_times
from database import init_db, save_roster, get_all_rosters, get_roster_details, delete_roster

# Initialize Database
init_db()

# --- 1. APP CONFIG & STYLING ---
st.set_page_config(page_title="Skyward Bond Raid Manager", layout="wide")

def apply_custom_css():
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
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = [c.strip() for c in df.columns]
        
        # Pre-process data
        df['Roles_List'] = df.iloc[:, 4].apply(get_roles)
        # Use get_build_display on the raw column to ensure icons are placed correctly
        df['Display_Build'] = df.iloc[:, 4].apply(get_build_display)
        
        # Region Mapping
        region_map = {
            "East": "NA East",
            "West": "NA West",
            "I am everywhere (GFN)": "GFN"
        }
        df['Region'] = df.iloc[:, 7].map(region_map).fillna(df.iloc[:, 7])
        
        return df
    except Exception as e:
        st.error(f"Sheet Connection Error: {e}")
        return pd.DataFrame()

# --- 3. UI COMPONENTS ---
def render_metrics(filtered_df):
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", len(filtered_df))
    
    roles = ["🛡️ Tank", "🌿 Healer", "🎭 Debuffer", "⚔️ DPS"]
    metrics = [m2, m3, m4, m5]
    
    for metric, role in zip(metrics, roles):
        count = len(filtered_df[filtered_df['Roles_List'].apply(lambda x: role in x)])
        metric.metric(role.split()[1] + "s", count)

def availability_tab(df):
    st.sidebar.header("🕹️ Availability Filters")
    
    sel_day = st.sidebar.selectbox("Select Raid Day", DAYS)
    day_col = [c for c in df.columns if sel_day in c][0]
    tz_view = st.sidebar.radio("Timezone", ["Pacific", "Eastern"])

    # Process daily availability based on selection
    df['Daily_Avail'] = df[day_col].apply(lambda x: clean_times(x, tz_view))
    
    # Filters
    all_times = sorted(list(set([t for sublist in df['Daily_Avail'] for t in sublist])))
    f_times = st.sidebar.multiselect("⏰ Time Slots", all_times, default=all_times)
    
    role_options = list(ROLES_CONFIG.keys())
    f_roles = st.sidebar.multiselect("Roles", role_options, default=role_options)

    # Region filter
    region_options = sorted(df['Region'].unique().tolist())
    f_regions = st.sidebar.multiselect("Region", region_options, default=region_options)

    # Search filter (New feature)
    search_query = st.sidebar.text_input("🔍 Search Player / Discord", "").lower()

    # Apply Filters
    mask = (df['Daily_Avail'].apply(lambda x: any(t in f_times for t in x))) & \
           (df['Roles_List'].apply(lambda x: any(r in f_roles for r in x))) & \
           (df['Region'].isin(f_regions))
    
    if search_query:
        mask &= (df['Username'].str.lower().str.contains(search_query)) | \
                (df['Discord ID'].str.lower().str.contains(search_query))

    f_df = df[mask].copy()

    st.title(f"{sel_day} Availability")
    render_metrics(f_df)
    st.divider()

    if not f_df.empty:
        f_df['Display_Time'] = f_df['Daily_Avail'].apply(lambda x: ", ".join(x))
        
        # Sort by Priority
        f_df['sort_val'] = f_df['Roles_List'].apply(lambda x: min([ROLE_PRIORITY.get(r, 99) for r in x]))
        f_df = f_df.sort_values('sort_val')

        st.dataframe(
            f_df[['Display_Build', 'Username', 'Region', 'Display_Time', 'Discord ID', 'UID']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Display_Build": st.column_config.TextColumn("Build / Class", width="medium"),
                "Display_Time": st.column_config.TextColumn("Available Slots", width="medium"),
            }
        )
    else:
        st.warning("No Availability match these filters.")

def lookup_tab(df):
    st.header("🔍 Player Lookup")
    
    # Enhanced lookup: search by name or discord
    search_options = sorted(df['Username'].unique())
    p_name = st.selectbox("Select Player", search_options)

    if p_name:
        p = df[df['Username'] == p_name].iloc[0]
        
        st.markdown(f"### Player: {p['Username']}")
        
        col1, _ = st.columns([2, 1])
        with col1:
            st.write(f"**Discord:** `{p['Discord ID']}`")
            st.write(f"**UID:** `{p['UID']}`")
            st.write(f"**Server:** {p.iloc[7]}")
            st.write(f"**Builds:** {p['Display_Build']}")

        st.divider()

        st.markdown("### Weekly Availability")
        sched = []
        for d in DAYS:
            c = [col for col in df.columns if d in col][0]
            sched.append({
                "Day": d,
                "Pacific Time": ", ".join(clean_times(p[c], "Pacific")) or "❌",
                "Eastern Time": ", ".join(clean_times(p[c], "Eastern")) or "❌"
            })
        st.table(pd.DataFrame(sched))

def roster_tab(df):
    st.title("🛡️ Roster Management")
    
    menu = st.tabs(["Create Roster", "Saved Rosters"])
    
    with menu[0]:
        st.subheader("Build New Roster")
        
        with st.expander("Roster Info", expanded=True):
            col1, col2 = st.columns(2)
            roster_name = col1.text_input("Roster Name", placeholder="e.g. Floor 10 Normal - Group A")
            raid_date = col2.date_input("Raid Date")
            gen_notes = st.text_area("General Roster Notes")
        
        st.divider()
        
        # Selection Area
        st.markdown("### Select Players (10 Man)")
        player_list = sorted(df['Username'].tolist())
        
        # Use columns for 10 slots
        main_team_data = []
        cols = st.columns(2)
        
        for i in range(10):
            with cols[i % 2]:
                st.markdown(f"**Slot {i+1}**")
                p_name = st.selectbox(f"Player", [""] + player_list, key=f"slot_{i}")
                
                if p_name:
                    p_info = df[df['Username'] == p_name].iloc[0]
                    roles = p_info['Roles_List']
                    p_role = st.selectbox(f"Role", roles, key=f"role_{i}")
                    p_note = st.text_input(f"Notes", key=f"note_{i}")
                    
                    main_team_data.append({
                        'username': p_name,
                        'role': p_role,
                        'notes': p_note
                    })
                st.markdown("---")

        st.markdown("### Reserves / Standby")
        num_reserves = st.number_input("Number of Reserves", min_value=0, max_value=10, value=2)
        reserve_data = []
        
        if num_reserves > 0:
            res_cols = st.columns(2)
            for i in range(num_reserves):
                with res_cols[i % 2]:
                    r_name = st.selectbox(f"Reserve {i+1}", [""] + player_list, key=f"res_{i}")
                    if r_name:
                        r_info = df[df['Username'] == r_name].iloc[0]
                        r_role = st.selectbox(f"Role", r_info['Roles_List'], key=f"res_role_{i}")
                        r_note = st.text_input(f"Notes", key=f"res_note_{i}")
                        reserve_data.append({
                            'username': r_name,
                            'role': r_role,
                            'notes': r_note
                        })

        if st.button("💾 Save Roster", type="primary"):
            if not roster_name:
                st.error("Please provide a roster name.")
            elif len(main_team_data) == 0:
                st.error("Please add at least one player.")
            else:
                try:
                    save_roster(roster_name, str(raid_date), gen_notes, main_team_data, reserve_data)
                    st.success(f"Roster '{roster_name}' saved successfully!")
                except Exception as e:
                    st.error(f"Error saving roster: {e}")

    with menu[1]:
        st.subheader("Manage Saved Rosters")
        saved_df = get_all_rosters()
        
        if saved_df.empty:
            st.info("No saved rosters found.")
        else:
            selected_roster_name = st.selectbox("Select Roster to View", saved_df['name'].tolist())
            
            if selected_roster_name:
                rid = saved_df[saved_df['name'] == selected_roster_name]['id'].iloc[0]
                roster_meta, (m_team, r_team) = get_roster_details(rid)
                
                st.divider()
                st.markdown(f"## {roster_meta['name']}")
                st.caption(f"📅 Date: {roster_meta['raid_date']} | 📝 {roster_meta['general_notes']}")
                
                # Display Color Coded Roster
                st.markdown("### Main Team")
                t1, t2 = st.columns(2)
                
                for idx, row in m_team.reset_index(drop=True).iterrows():
                    target_col = t1 if idx < 5 else t2
                    color = ROLE_COLORS.get(row['role'], "#30363d")
                    
                    target_col.markdown(f"""
                        <div style="background-color: {color}; padding: 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #ffffff33;">
                            <strong>{row['username']}</strong> - {row['role']}<br/>
                            <small><i>{row['player_notes'] or ""}</i></small>
                        </div>
                    """, unsafe_allow_html=True)

                if not r_team.empty:
                    st.markdown("### Reserves")
                    r_cols = st.columns(2)
                    for idx, row in r_team.reset_index(drop=True).iterrows():
                        target_col = r_cols[idx % 2]
                        target_col.markdown(f"""
                            <div style="background-color: #30363d; padding: 10px; border-radius: 5px; margin-bottom: 5px;">
                                <strong>{row['username']}</strong> - {row['role']}<br/>
                                <small><i>{row['player_notes'] or ""}</i></small>
                            </div>
                        """, unsafe_allow_html=True)
                
                st.divider()
                if st.button("🗑️ Delete Roster"):
                    delete_roster(rid)
                    st.warning("Roster deleted.")
                    st.rerun()

# --- MAIN ---
def main():
    apply_custom_css()
    df = load_data()
    
    if not df.empty:
        # Sidebar Navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["📅 Daily Availability", "🔍 Player Lookup", "🛡️ Roster Management"])
        
        if page == "📅 Daily Availability":
            availability_tab(df)
        elif page == "🔍 Player Lookup":
            lookup_tab(df)
        else:
            roster_tab(df)
    else:
        st.error("Could not load data. Check connection to Google Sheet.")

if __name__ == "__main__":
    main()
