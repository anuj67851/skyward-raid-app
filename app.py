import streamlit as st
import pandas as pd
from utils import ROLES_CONFIG, ROLE_PRIORITY, DAYS, get_roles, get_build_display, clean_times

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
                (df['Discord Name'].str.lower().str.contains(search_query))

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
            f_df[['Display_Build', 'Username', 'Region', 'Display_Time', 'Discord Name', 'UID']],
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
            st.write(f"**Discord:** `{p['Discord Name']}`")
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

# --- MAIN ---
def main():
    apply_custom_css()
    df = load_data()
    
    if not df.empty:
        # Header area for Roster Link
        h_col1, h_col2 = st.columns([6, 1])
        with h_col2:
            ROSTER_URL = "https://docs.google.com/spreadsheets/d/1A6xxd8gxHKdBsDbFOC4jOMtW8C4XxNRBsXL6h1Bz68o/"
            st.link_button("📋 Roster Sheet", ROSTER_URL, use_container_width=True)

        # Sidebar Navigation
        st.sidebar.title("Navigation")
        
        page = st.sidebar.radio("Go to", ["📅 Daily Availability", "🔍 Player Lookup"])
        
        if page == "📅 Daily Availability":
            availability_tab(df)
        else:
            lookup_tab(df)
    else:
        st.error("Could not load data. Check connection to Google Sheet.")

if __name__ == "__main__":
    main()
