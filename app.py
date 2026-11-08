import streamlit as st
import pandas as pd
from google import genai
import os
import time
import base64

# --- PAGE CONFIG ---
st.set_page_config(page_title="Data tracker for English debate", page_icon="📊", layout="wide")

# Helper function to convert local images to base64 for reliable web rendering
def img_to_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    return ""

# --- DESIGN: find the artwork files ---
# Looks in the folder where app.py lives (and any subfolders like "images"),
# ignores upper/lower case, and accepts .png, .jpg, .jpeg or .webp.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

def find_art(name):
    wanted = name.lower().replace("_", "").replace("-", "").replace(" ", "")
    for folder, _, files in os.walk(APP_DIR):
        for file_name in files:
            stem, ext = os.path.splitext(file_name)
            clean = stem.lower().replace("_", "").replace("-", "").replace(" ", "")
            if clean == wanted and ext.lower() in IMAGE_TYPES:
                data = img_to_base64(os.path.join(folder, file_name))
                if data:
                    return f"url('data:{IMAGE_TYPES[ext.lower()]};base64,{data}')"
    return None

ART_NAMES = ["snowman", "snow", "autumn_leaves", "cherry_blossom", "green_tree"]
art = {name: find_art(name) for name in ART_NAMES}
missing_art = [name for name, url in art.items() if url is None]

# Each picture becomes a background layer of the page (first = on top).
# Missing pictures are replaced by a transparent layer so the layout stays the same.
EMPTY = "linear-gradient(transparent, transparent)"
art_layers = ", ".join(art[name] or EMPTY for name in ART_NAMES)

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

    /* ---------- Lavender background with soft glowing centre ---------- */
    /* Order of layers: snowman, snow, autumn leaves, cherry blossom, green tree, gradient */
    [data-testid="stAppViewContainer"] {{
        background-color: var(--lav-bg);
        background-image:
            {art_layers},
            radial-gradient(ellipse at 50% 40%, #e6e1ef 0%, #cfc7de 40%, var(--lav-bg) 100%);
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position:
            left 70px bottom 70px,
            left 15px bottom 15px,
            right 15px bottom 15px,
            left 15px top 15px,
            right 15px top 15px,
            center;
        background-size:
            230px auto,
            640px auto,
            560px auto,
            420px auto,
            340px auto,
            cover;
    }}
    /* Smaller screens: shrink the art so it doesn't crowd the content */
    @media (max-width: 1300px) {{
        [data-testid="stAppViewContainer"] {{
            background-position:
                left 40px bottom 45px,
                left 15px bottom 15px,
                right 15px bottom 15px,
                left 15px top 15px,
                right 15px top 15px,
                center;
            background-size:
                150px auto,
                400px auto,
                360px auto,
                270px auto,
                230px auto,
                cover;
        }}
    }}
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
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{
        background-color: #ffffff !important;
        border: 1px solid #c9c1d9 !important;
        border-radius: 4px !important;
    }}
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {{
        background-color: #ffffff !important;
        color: var(--ink) !important;
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
        background: rgba(255, 255, 255, 0.35);
        border: 1px solid var(--lav-border) !important;
        border-radius: 6px;
    }}
    hr {{ border-color: var(--lav-border) !important; }}

</style>

<div class="page-frame"></div>
""", unsafe_allow_html=True)

# Tells you which picture files couldn't be found (disappears once they're all there)
if missing_art:
    st.caption("🖼️ Picture files not found next to app.py: " + ", ".join(missing_art))

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

    with st.expander("🔗 View Source URLs & Evidence Links"):
        if not df.empty:
            for idx, row in df.iterrows():
                url_val = row.get("url", "")
                if pd.notna(url_val) and str(url_val).strip() != "":
                    st.markdown(f"**[ID {row['id']}] {row['topic']}** — *{row['source']}*")
                    st.markdown(f"🔗 [Open Source Link]({url_val})")
                    st.divider()
                else:
                    st.markdown(f"**[ID {row['id']}] {row['topic']}** — *No URL provided*")
        else:
            st.write("No research entries yet.")

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

    with st.form("add_research_form", clear_on_submit=True):
        new_topic = st.text_input("Debate Topic")
        new_researcher = st.text_input("Researcher Name")
        new_source = st.text_input("Source / Citation")

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
