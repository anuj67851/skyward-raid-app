import pandas as pd
import re

# --- CONFIGURATION ---
ROLES_CONFIG = {
    "🛡️ Tank": ["Stonesplit-Might (Tank)"],
    "🌿 Healer": ["Silkbind-Deluge (Healer)"],
    "🎭 Debuffer": ["Bamboocut-Dust (Ropebrella)"],
    "⚔️ DPS": ["Nameless", "Strat", "Heng", "Gauntlets", "Fanbrella"]
}

ROLE_EMOJIS = {
    "Tank": "🛡️",
    "Healer": "🌿",
    "Debuffer": "🎭",
    "DPS": "⚔️"
}

ROLE_PRIORITY = {
    "🛡️ Tank": 0,
    "🌿 Healer": 1,
    "🎭 Debuffer": 2,
    "⚔️ DPS": 3
}

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# --- CORE LOGIC ---
def get_roles(build_text):
    text = str(build_text)
    found_roles = []
    
    # Check for specific support roles
    for role, keywords in ROLES_CONFIG.items():
        if role == "⚔️ DPS": continue
        if any(kw in text for kw in keywords):
            found_roles.append(role)
            
    # Check for DPS keywords or if no support roles found
    dps_keywords = ROLES_CONFIG["⚔️ DPS"]
    rem = text
    for role, keywords in ROLES_CONFIG.items():
        if role == "⚔️ DPS": continue
        for kw in keywords:
            rem = rem.replace(kw, "")
    rem = rem.replace(",", "").strip()
    
    if any(d in text for d in dps_keywords) or not found_roles or rem:
        found_roles.append("⚔️ DPS")
        
    return list(set(found_roles))

def get_build_display(build_text):
    roles = get_roles(build_text)
    # Extract emojis from role names (e.g., "🛡️ Tank" -> "🛡️")
    icons = "".join(sorted([r.split()[0] for r in roles], key=lambda x: [ROLE_EMOJIS[k] for k in ROLE_EMOJIS].index(x) if x in ROLE_EMOJIS.values() else 99))
    # Actually, simpler to just match them
    display_icons = []
    for role in ["🛡️ Tank", "🌿 Healer", "🎭 Debuffer", "⚔️ DPS"]:
        if role in roles:
            display_icons.append(role.split()[0])
    
    return f"{''.join(display_icons)} {build_text}"

def clean_times(raw_str, tz="Pacific"):
    if pd.isna(raw_str) or str(raw_str).strip() == "":
        return []
    
    raw_slots = str(raw_str).split(',')
    cleaned = []
    for slot in raw_slots:
        times = re.findall(r'(\d+[ap]m)', slot)
        if len(times) == 4:
            # Format: [PT_Start, ET_Start, PT_End, ET_End]
            if tz == "Pacific":
                cleaned.append(f"{times[0]}-{times[2]} PT")
            else:
                cleaned.append(f"{times[1]}-{times[3]} ET")
        else:
            cleaned.append(slot.strip())
    return cleaned
