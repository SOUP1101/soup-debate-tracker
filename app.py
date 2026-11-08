import streamlit as st
import pandas as pd
from google import genai
import os
import time
import base64

# --- PAGE CONFIG ---
st.set_page_config(page_title="Data tracker for English debate", page_icon="📊", layout="wide")

# =====================================================================
# --- DESIGN: soft painted seasonal corners ---
# Clockwise from the top-left: spring (cherry blossom), summer (green tree),
# autumn (falling leaves), winter (snowy pine branch with pinecones).
# Each picture is placed on a soft lavender backdrop, given the same colour
# mood, kept sharp in its corner, and blurred + faded smoothly towards the centre.
# Pictures are found by name OR by their exact size, so random file names are fine.
# =====================================================================
import io
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PICTURE_TYPES = (".png", ".jpg", ".jpeg", ".webp")

#            season:  (file name,       exact size,   corner,         width share, mirror?)
SEASON_ART = {
    "spring": ("cherry_blossom", (390, 390),  "top-left",     0.98, True),
    "summer": ("green_tree",     (390, 243),  "top-right",    0.94, False),
    "autumn": ("autumn_leaves",  (1000, 561), "bottom-right", 1.00, False),
    "winter": ("winter",         (760, 640),  "bottom-left",  1.00, False),
}


def find_picture(name, size):
    wanted = name.replace("_", "").lower()
    by_size = None
    for folder, _, files in os.walk(APP_DIR):
        for file_name in sorted(files):
            stem, ext = os.path.splitext(file_name)
            if ext.lower() not in PICTURE_TYPES:
                continue
            path = os.path.join(folder, file_name)
            if stem.replace("_", "").replace("-", "").replace(" ", "").lower() == wanted:
                return path
            if by_size is None:
                try:
                    with Image.open(path) as im:
                        if im.size == size:
                            by_size = path
                except Exception:
                    pass
    return by_size


def smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)


@st.cache_data(show_spinner=False)
def painted_corner(path, corner, width_share, mirror, changed_time):
    size = 820
    # 1) Place the picture in its corner on a soft lavender backdrop
    pic = Image.open(path).convert("RGBA")
    box = pic.getchannel("A").getbbox()
    if box:
        pic = pic.crop(box)
    if mirror:
        pic = ImageOps.mirror(pic)
    w = int(size * width_share)
    h = int(pic.height * w / pic.width)
    if h > size:
        w, h = int(w * size / h), size
    pic = pic.resize((w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (203, 195, 220, 255))
    px = 0 if "left" in corner else size - w
    py = 0 if "top" in corner else size - h
    canvas.alpha_composite(pic, (px, py))
    img = canvas.convert("RGB")

    # 2) Same colour mood for every season: softer colours, lavender-tinted shadows, gentle glow
    img = ImageEnhance.Color(img).enhance(0.9)
    img = ImageEnhance.Contrast(img).enhance(0.94)
    rgb = np.asarray(img).astype(np.float32) / 255.0
    lavender = np.array([0.70, 0.66, 0.78], dtype=np.float32)
    lum = rgb.mean(axis=2, keepdims=True)
    rgb = rgb + (lavender - rgb) * (0.22 * (1 - lum) + 0.06)
    glow = np.asarray(img.filter(ImageFilter.GaussianBlur(14))).astype(np.float32) / 255.0
    rgb = 1 - (1 - rgb) * (1 - 0.16 * glow)

    # 3) Distance from the page corner (0 = corner, 1 = inner edge)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / (size - 1)
    u = x if "left" in corner else 1 - x
    v = y if "top" in corner else 1 - y

    # 4) Soft, slightly uneven fade so it melts into the page
    rng = np.random.default_rng(7)
    small = Image.fromarray((rng.random((10, 10)) * 255).astype(np.uint8))
    wobble = (np.asarray(small.resize((size, size), Image.BICUBIC)).astype(np.float32) / 255.0 - 0.5) * 0.16
    u2, v2 = u + wobble, v + wobble
    alpha = (1 - smoothstep(0.42, 1.0, u2)) * (1 - smoothstep(0.42, 1.0, v2))
    alpha *= 1 - smoothstep(0.7, 1.28, np.sqrt(u2 ** 2 + v2 ** 2))

    # 5) Depth: sharp in the corner, dreamy blur where it fades out
    blurred = np.asarray(Image.fromarray((rgb * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))).astype(np.float32) / 255.0
    sharp_amount = np.clip(alpha * 1.7, 0, 1)[..., None]
    rgb = rgb * sharp_amount + blurred * (1 - sharp_amount)

    out = Image.fromarray((np.dstack([rgb, alpha]).clip(0, 1) * 255).astype(np.uint8), "RGBA")
    buffer = io.BytesIO()
    try:
        out.save(buffer, format="WEBP", quality=86, method=4)
        mime = "image/webp"
    except Exception:
        buffer = io.BytesIO()
        out.save(buffer, format="PNG", optimize=True)
        mime = "image/png"
    return f"url('data:{mime};base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}')"


art = {}
missing_photos = []
for season, (name, exact_size, corner, width_share, mirror) in SEASON_ART.items():
    picture = find_picture(name, exact_size)
    if picture:
        art[season] = painted_corner(picture, corner, width_share, mirror, os.path.getmtime(picture))
    else:
        art[season] = "linear-gradient(transparent, transparent)"
        missing_photos.append(name)

# Background layers: spring (top-left), summer (top-right), autumn (bottom-right), winter (bottom-left)
art_layers = ", ".join([art["spring"], art["summer"], art["autumn"], art["winter"]])

st.markdown(f"""
<style>
    /* ---------- Colour palette ---------- */
    :root {{
        --lav-bg: #b2a9c7;
        --lav-light: #ddd7e8;
        --lav-panel: rgba(208, 200, 224, 0.88);
        --lav-tab: #dcd6e6;
        --lav-tab-active: #ece8f3;
        --lav-border: #b6accb;
        --purple-btn: #7a6e9d;
        --purple-btn-hover: #65588a;
        --ink: #1e1d2b;
    }}

    /* ---------- Lavender background with the four seasons in the corners ---------- */
    /* Clockwise from top-left: spring, summer, autumn, winter */
    [data-testid="stAppViewContainer"] {{
        background-color: var(--lav-bg);
        background-image:
            {art_layers},
            radial-gradient(ellipse at 50% 45%, #ece8f3 0%, #d6cfe3 45%, var(--lav-bg) 100%);
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position:
            left 15px top 15px,
            right 15px top 15px,
            right 15px bottom 15px,
            left 15px bottom 15px,
            center;
        background-size:
            var(--art-size) var(--art-size),
            var(--art-size) var(--art-size),
            var(--art-size) var(--art-size),
            var(--art-size) var(--art-size),
            cover;
    }}
    /* Each corner picture grows with the screen but never gets too big */
    :root {{ --art-size: min(42vw, 66vh, 640px); }}
    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
    }}

    /* ---------- White picture-frame border around the whole page ---------- */
    .page-frame {{
        position: fixed;
        inset: 10px;
        border: 5px solid #ffffff;
        border-radius: 6px;
        box-shadow: 0 0 0 1px rgba(0,0,0,0.06), inset 0 0 0 1px rgba(0,0,0,0.04);
        pointer-events: none;
        z-index: 3;
    }}

    /* ---------- Centre column (sits above the artwork) ---------- */
    [data-testid="stMainBlockContainer"] {{
        max-width: 860px !important;
        margin: 0 auto !important;
        padding-top: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        position: relative;
        z-index: 2;
        background: radial-gradient(closest-side, rgba(238, 234, 245, 0.82) 0%, rgba(238, 234, 245, 0.7) 72%, rgba(238, 234, 245, 0) 100%);
    }}

    /* ---------- Title + subtitle ---------- */
    h1 {{
        text-align: center;
        color: var(--ink) !important;
        font-weight: 700 !important;
        font-size: 1.9rem !important;
        padding-bottom: 0 !important;
        margin-bottom: 0 !important;
    }}
    [data-testid="stHeaderActionElements"] {{ display: none; }}
    .subtitle {{
        text-align: center;
        color: #2c2a3a;
        font-size: 1rem;
        margin-top: -0.4rem;
        margin-bottom: 1.6rem;
    }}

    /* ---------- Password card ---------- */
    .st-key-pw_card {{
        background: var(--lav-panel);
        border: 1px solid var(--lav-border);
        border-radius: 6px;
        padding: 0.9rem 1.2rem 1.1rem 1.2rem;
        margin: 0 auto 2.5rem auto;
        max-width: 400px;
        box-shadow: 0 2px 6px rgba(60, 50, 90, 0.10);
    }}

    /* ---------- Tabs panel ---------- */
    /* No box around the workspace: tabs sit directly on the background */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: var(--lav-tab);
        border: 1px solid var(--lav-border);
        border-radius: 4px;
        overflow: hidden;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 42px;
        flex: 1 1 auto;
        justify-content: center;
        white-space: nowrap;
        background-color: var(--lav-tab);
        border-radius: 0;
        border-right: 1px solid var(--lav-border);
        padding: 0 0.8rem;
        font-weight: 500;
        color: var(--ink);
    }}
    .stTabs [data-baseweb="tab"]:last-child {{ border-right: none; }}
    .stTabs [aria-selected="true"] {{
        background-color: var(--lav-tab-active) !important;
        color: var(--ink) !important;
    }}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {{
        display: none;
    }}
    .stTabs [data-baseweb="tab-panel"] {{
        padding: 1.4rem 0.4rem 1.6rem 0.4rem;
    }}

    /* ---------- Text, labels, inputs ---------- */
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3 {{
        color: var(--ink);
    }}
    /* Every box: near-white with a whisper of pink and a soft pink border */
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
    [data-baseweb="base-input"] {{
        background-color: #fffbfc !important;
        border: 1px solid #ecd6de !important;
        border-radius: 6px !important;
    }}
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="base-input"] input,
    [data-baseweb="select"] input, [data-baseweb="select"] div {{
        background-color: #fffbfc !important;
        color: var(--ink) !important;
    }}
    [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within {{
        border-color: #d9a9bb !important;
        box-shadow: 0 0 0 2px rgba(236, 190, 207, 0.35) !important;
    }}
    input::placeholder, textarea::placeholder {{ color: #a59aab !important; }}
    /* Dropdown menus */
    [data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] {{
        background-color: #fffbfc !important;
        color: var(--ink) !important;
    }}
    [data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {{
        background-color: #fbe9ef !important;
    }}
    /* Checkboxes, radio buttons, info/success boxes, table */
    [data-testid="stCheckbox"] label span, [data-baseweb="radio"] div:first-child {{ border-color: #d9a9bb !important; }}
    [data-testid="stAlert"] {{ background-color: rgba(255, 251, 252, 0.85) !important; color: var(--ink) !important; }}
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
        border: 1px solid #ecd6de; border-radius: 6px; overflow: hidden; background: #fffbfc;
    }}

    /* ---------- Buttons ---------- */
    div.stButton > button,
    div.stFormSubmitButton > button,
    div.stDownloadButton > button {{
        border-radius: 4px;
        font-weight: 500;
        background-color: var(--purple-btn);
        color: #ffffff;
        border: none;
        padding: 0.45rem 1.1rem;
        box-shadow: 0 1px 3px rgba(40, 30, 70, 0.25);
    }}
    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover,
    div.stDownloadButton > button:hover {{
        background-color: var(--purple-btn-hover);
        color: #ffffff;
    }}

    /* Forms, expanders, tables blend into the lavender panel */
    [data-testid="stForm"], [data-testid="stExpander"] details {{
        background: rgba(255, 251, 252, 0.6);
        border: 1px solid #ecd6de !important;
        border-radius: 6px;
    }}
    hr {{ border-color: var(--lav-border) !important; }}

</style>

<div class="page-frame"></div>
""", unsafe_allow_html=True)

# Shows which pictures are still missing (disappears once all four are there)
if missing_photos:
    st.caption("🖼️ Pictures not found next to app.py: " + ", ".join(missing_photos))

# --- TITLE ---
st.title("Data tracker for English debate")
st.markdown('<div class="subtitle">Manage team research for upcoming English debates</div>', unsafe_allow_html=True)

# --- PASSWORD SECURITY SETUP ---
if "APP_PASSWORD" in st.secrets:
    with st.container(key="pw_card"):
        password = st.text_input("🔒 Enter Password to Access Data tracker for English debate:", type="password")
    if password != st.secrets["APP_PASSWORD"]:
        st.warning("Please enter the correct password to access this private debate research tracker.")
        st.stop()

CSV_FILE = "research_log.csv"
TODO_FILE = "todo_list.csv"

# --- DATABASE LOADING ---
def load_research():
    expected_columns = ["id", "topic", "source", "summary", "researcher", "printed", "url"]
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            for col in expected_columns:
                if col not in df.columns:
                    if col == "printed":
                        df[col] = False
                    else:
                        df[col] = ""
            return df
        except Exception:
            df = pd.DataFrame(columns=expected_columns)
            df.to_csv(CSV_FILE, index=False)
            return df
    else:
        df = pd.DataFrame(columns=expected_columns)
        df.to_csv(CSV_FILE, index=False)
        return df

def load_todo():
    expected_todo_cols = ["id", "claim", "assignee", "status"]
    if os.path.exists(TODO_FILE):
        try:
            df = pd.read_csv(TODO_FILE)
            for col in expected_todo_cols:
                if col not in df.columns:
                    df[col] = "Open" if col == "status" else ""
            df["assignee"] = df["assignee"].astype(str)
            df["status"] = df["status"].astype(str)
            return df
        except Exception:
            df = pd.DataFrame(columns=expected_todo_cols)
            df["assignee"] = df["assignee"].astype(str)
            df["status"] = df["status"].astype(str)
            df.to_csv(TODO_FILE, index=False)
            return df
    else:
        df = pd.DataFrame(columns=expected_todo_cols)
        df["assignee"] = df["assignee"].astype(str)
        df["status"] = df["status"].astype(str)
        df.to_csv(TODO_FILE, index=False)
        return df

df = load_research()
todo_df = load_todo()

if "printed" in df.columns:
    df["printed"] = df["printed"].astype(bool)

if "prefill_summary" not in st.session_state:
    st.session_state["prefill_summary"] = ""

# --- TAB NAVIGATION ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Query AI",
    "📋 View, Edit & Log",
    "➕ Add New Research",
    "✅ Research To-Do Queue"
])

# ================= TAB 1: QUERY AI =================
with tab1:
    user_question = st.text_input("Enter your research question:", placeholder="Enter your research question:")
    if st.button("Ask AI Assistant"):
        if user_question:
            api_key = None
            try:
                if "GEMINI_API_KEY" in st.secrets:
                    api_key = st.secrets["GEMINI_API_KEY"]
            except Exception:
                pass

            if not api_key:
                api_key = os.environ.get("GEMINI_API_KEY")

            if not api_key or api_key.startswith("your_") or len(api_key) < 10:
                st.error("🔑 **API Key Missing or Invalid!** Please check your Streamlit Cloud Secrets.")
            else:
                with st.spinner("Analyzing research log with AI..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        database_text = df.to_string()

                        prompt = f"""
                        You are a professional research assistant for an English debate team.
                        Here is our team's current research log database (including sources, summaries, researchers, and URLs):
                        {database_text}

                        Answer the following question based ONLY on the database provided, and cite your sources/URLs where applicable:
                        {user_question}
                        """

                        response = None
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                response = client.models.generate_content(
                                    model='gemini-3.5-flash-lite',
                                    contents=prompt
                                )
                                break
                            except Exception as inner_e:
                                if attempt == max_retries - 1:
                                    raise inner_e
                                time.sleep(2)

                        if response:
                            st.success("Analysis Complete!")
                            st.markdown(response.text)

                    except Exception as e:
                        st.error(f"⚠️ Error communicating with Gemini API: {e}")
        else:
            st.warning("Please enter a question first.")

    st.divider()
    st.markdown("Search Results:")

# ================= TAB 2: VIEW, EDIT & LOG =================
with tab2:
    st.subheader("Current Research Database & Evidence")

    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        search_query = st.text_input("🔍 Search logs (keywords in topic, source, summary, or researcher):", "")
    with col_s2:
        sort_option = st.radio("Sort View By:", ["Default (ID Order)", "By Topic", "By Researcher", "By Source"], horizontal=True)

    filtered_df = df.copy()
    if search_query:
        q = search_query.lower()
        mask = (
            filtered_df["topic"].astype(str).str.lower().str.contains(q) |
            filtered_df["source"].astype(str).str.lower().str.contains(q) |
            filtered_df["summary"].astype(str).str.lower().str.contains(q) |
            filtered_df["researcher"].astype(str).str.lower().str.contains(q)
        )
        filtered_df = filtered_df[mask]

    if sort_option == "By Topic" and not filtered_df.empty:
        filtered_df = filtered_df.sort_values(by="topic")
    elif sort_option == "By Researcher" and not filtered_df.empty:
        filtered_df = filtered_df.sort_values(by="researcher")
    elif sort_option == "By Source" and not filtered_df.empty:
        filtered_df = filtered_df.sort_values(by="source")

    st.info("💡 You can edit cells, check/uncheck 'printed' boxes, or delete rows directly in the table below!")

    edited_df = st.data_editor(
        filtered_df,
        num_rows="dynamic",
        key="research_editor",
        use_container_width=True
    )

    if not edited_df.equals(filtered_df):
        for idx, row in edited_df.iterrows():
            match_idx = df[df["id"] == row["id"]].index
            if not match_idx.empty:
                for col in df.columns:
                    if col in edited_df.columns:
                        df.at[match_idx[0], col] = row[col]
        df.to_csv(CSV_FILE, index=False)
        st.success("Database updated successfully!")

    if not df.empty:
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download Clean CSV Export",
            data=csv_data,
            file_name="debate_research_log.csv",
            mime="text/csv",
        )

# ================= TAB 3: ADD NEW RESEARCH =================
with tab3:
    st.subheader("Add New Research Entry")

    # Box that lets you type something new OR pick an answer that was saved before.
    # Saved answers come from the research database, so every answer you save
    # with "Save to Database" shows up as an option next time.
    def remember_box(label, column, key):
        saved_answers = []
        if column in df.columns:
            for value in df[column].dropna():
                text = str(value).strip()
                if text and text.lower() != "nan" and text not in saved_answers:
                    saved_answers.append(text)
        saved_answers.sort(key=str.lower)
        try:
            return st.selectbox(
                label,
                saved_answers,
                index=None,
                placeholder="Type something new, or choose a saved answer",
                accept_new_options=True,
                key=key,
            )
        except TypeError:
            # Older Streamlit versions can't do this, so fall back to a normal box
            return st.text_input(label, key=key)

    with st.form("add_research_form", clear_on_submit=True):
        new_topic = remember_box("Debate Topic", "topic", "pick_topic")
        new_researcher = remember_box("Researcher Name", "researcher", "pick_researcher")
        new_source = remember_box("Source / Citation", "source", "pick_source")

        prefill = st.session_state.get("prefill_summary", "")
        new_summary = st.text_area("Key Summary / Arguments", value=prefill)
        new_url = st.text_input("Source URL / Evidence Link (Optional)")
        new_printed = st.checkbox("Printed out already?")

        submit_button = st.form_submit_button("Save to Database")

        if submit_button:
            if new_topic and new_source and new_summary and new_researcher:
                new_id = int(df["id"].max()) + 1 if not df.empty and "id" in df.columns and pd.notna(df["id"].max()) else 1
                new_row = {
                    "id": new_id,
                    "topic": new_topic,
                    "source": new_source,
                    "summary": new_summary,
                    "researcher": new_researcher,
                    "printed": bool(new_printed),
                    "url": new_url if new_url else ""
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.session_state["prefill_summary"] = ""
                st.success("Successfully added new research entry!")
                st.rerun()
            else:
                st.error("Please fill out Topic, Researcher, Source, and Summary.")

# ================= TAB 4: RESEARCH TO-DO QUEUE =================
with tab4:
    st.subheader("✅ Research To-Do Queue & Workflow")
    st.markdown("Add evidence claims you need for debate cases. Set tasks to 'In Progress' and enter your name so teammates know who is working on it!")

    with st.form("todo_form", clear_on_submit=True):
        todo_claim = st.text_input("Desired Evidence Claim / Argument (e.g., 'Pesticides are harmful to human health')")
        todo_submit = st.form_submit_button("Add to To-Do Queue")

        if todo_submit:
            if todo_claim:
                new_t_id = int(todo_df["id"].max()) + 1 if not todo_df.empty and "id" in todo_df.columns and pd.notna(todo_df["id"].max()) else 1
                new_t_row = {
                    "id": new_t_id,
                    "claim": todo_claim,
                    "assignee": "",
                    "status": "Open"
                }
                todo_df = pd.concat([todo_df, pd.DataFrame([new_t_row])], ignore_index=True)
                todo_df.to_csv(TODO_FILE, index=False)
                st.success("Added claim to To-Do queue!")
                st.rerun()
            else:
                st.error("Please enter a claim.")

    st.markdown("---")
    st.subheader("Current To-Do List")

    if not todo_df.empty:
        for idx, row in todo_df.iterrows():
            cols = st.columns([3, 2, 2])
            with cols[0]:
                st.markdown(f"**Claim:** {row['claim']}")
                current_assignee = row['assignee'] if pd.notna(row['assignee']) and str(row['assignee']).strip() != "" and str(row['assignee']) != "nan" else "None"
                st.markdown(f"*Worked on by:* **{current_assignee}**")
            with cols[1]:
                status_options = ["Open", "In Progress"]
                current_status = row['status'] if row['status'] in status_options else "Open"
                status_val = st.selectbox(f"Status {row['id']}", status_options, index=status_options.index(current_status), key=f"status_{row['id']}")

                if status_val != row['status']:
                    todo_df.at[idx, 'status'] = status_val
                    todo_df.to_csv(TODO_FILE, index=False)
                    st.rerun()

                if status_val == "In Progress":
                    existing_assignee = str(row['assignee']) if pd.notna(row['assignee']) and str(row['assignee']) != "nan" else ""
                    worker_name = st.text_input(f"Your Name (Who is working on ID {row['id']}):", value=existing_assignee, key=f"worker_{row['id']}")
                    if worker_name != existing_assignee:
                        todo_df.at[idx, 'assignee'] = str(worker_name)
                        todo_df.to_csv(TODO_FILE, index=False)
            with cols[2]:
                if st.button(f"🚀 Move to Add & Complete", key=f"move_{row['id']}"):
                    st.session_state["prefill_summary"] = row['claim']
                    todo_df = todo_df.drop(idx).reset_index(drop=True)
                    todo_df.to_csv(TODO_FILE, index=False)
                    st.success("Claim moved! Go to the 'Add New Research' tab to complete citation and details.")
                    st.rerun()
            st.divider()
    else:
        st.info("Your To-Do queue is currently empty. Add a claim above to get started!")
