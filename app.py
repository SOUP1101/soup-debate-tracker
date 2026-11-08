import streamlit as st
import pandas as pd
from google import genai
import os
import time

# --- PAGE CONFIG & CALMING BACKGROUND DESIGN ---
st.set_page_config(page_title="Data tracker for English debate", page_icon="📊", layout="wide")

st.markdown("""
<style>
    /* Calming background pattern across the entire viewport */
    [data-testid="stAppViewContainer"] {
        background-color: #f4f6f9;
        background-image: radial-gradient(#cbd5e1 1.5px, transparent 1.5px);
        background-size: 28px 28px;
    }
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 8px 8px 0px 0px;
        font-weight: 600;
        color: #2c3e50;
        border: 1px solid #cbd5e1;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2b6cb0 !important;
        color: white !important;
    }
    div.stButton > button {
        border-radius: 6px;
        font-weight: 600;
        background-color: #2b6cb0;
        color: white;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #2c5282;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- PASSWORD SECURITY SETUP ---
if "APP_PASSWORD" in st.secrets:
    password = st.text_input("🔒 Enter Password to Access Data tracker for English debate:", type="password")
    if password != st.secrets["APP_PASSWORD"]:
        st.warning("Please enter the correct password to access this private debate research tracker.")
        st.stop()

st.title("📊 Data tracker for English debate")
st.markdown("Manage team research, track evidence URLs, organize collaborative to-do queues, and query your database with Gemini AI.")

CSV_FILE = "research_log.csv"
TODO_FILE = "todo_list.csv"

# --- GUARANTEED BLANK START (Auto-clears old dummy rows) ---
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
            if not df.empty and ("Mock" in str(df.iloc[0].get("topic", "")) or "Example" in str(df.iloc[0].get("topic", ""))):
                df = pd.DataFrame(columns=expected_columns)
                df.to_csv(CSV_FILE, index=False)
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
            # Ensure text compatibility to prevent type errors
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
    st.subheader("Ask AI about Team Research")
    user_question = st.text_input("Enter your research question:")
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
