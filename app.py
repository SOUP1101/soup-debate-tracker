import streamlit as st
import pandas as pd
from google import genai
import os
import time

# --- 5. PASSWORD SECURITY SETUP ---
# To secure your app, make sure you add APP_PASSWORD = "your_chosen_password" 
# in your Streamlit Cloud Secrets dashboard alongside your GEMINI_API_KEY.
if "APP_PASSWORD" in st.secrets:
    password = st.text_input("🔒 Enter Password to Access S.O.U.P.:", type="password")
    if password != st.secrets["APP_PASSWORD"]:
        st.warning("Please enter the correct password to access this private debate research tracker.")
        st.stop() # Stops execution here so unauthorized visitors cannot see the app

st.title("📚 S.O.U.P. Debate Research Tracker")
st.write("Manage team research, filter by topic, track print status, and query your database with Gemini AI!")

CSV_FILE = "research_log.csv"

# --- 1. BLANK LOG INITIALIZATION ---
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        # Starts completely blank with the requested columns
        df = pd.DataFrame(columns=["id", "topic", "source", "summary", "researcher", "printed"])
        df.to_csv(CSV_FILE, index=False)
        return df

df = load_data()

# Ensure 'printed' column is boolean for checkboxes
if "printed" in df.columns:
    df["printed"] = df["printed"].astype(bool)

tab1, tab2, tab3 = st.tabs(["🔍 Query AI", "📋 View, Edit & Delete Log", "➕ Add New Research"])

with tab1:
    st.subheader("Ask AI about Team Research")
    user_question = st.text_input("Enter your question:")
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
                        You are a helpful research assistant for a high school debate team.
                        Here is our team's current research log database:
                        {database_text}

                        Answer the following question based ONLY on the database provided:
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
                            st.write(response.text)

                    except Exception as e:
                        st.error(f"⚠️ Error communicating with Gemini API: {e}")
        else:
            st.warning("Please enter a question first.")

with tab2:
    st.subheader("Current Research Database & Management")
    st.info("💡 You can edit cells directly, check/uncheck 'printed' boxes, or delete rows using the trash icon/sidebar in the table below!")

    # --- 2 & 3. INTERACTIVE DATA EDITOR (Edit, Toggle Print, Delete Rows) ---
    edited_df = st.data_editor(
        df, 
        num_rows="dynamic", 
        key="research_editor",
        use_container_width=True
    )

    # Save changes automatically when the user edits or deletes rows
    if not edited_df.equals(df):
        edited_df.to_csv(CSV_FILE, index=False)
        st.success("Database updated successfully!")

    # Topic Filter for viewing
    if not edited_df.empty and "topic" in edited_df.columns:
        topics = ["All"] + list(edited_df["topic"].dropna().unique())
        selected_topic = st.selectbox("Filter view by Topic:", topics)
        if selected_topic != "All":
            st.dataframe(edited_df[edited_df["topic"] == selected_topic], use_container_width=True)

    # Download CSV Button
    if not edited_df.empty:
        csv_data = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Research Log as CSV",
            data=csv_data,
            file_name="research_log.csv",
            mime="text/css" if False else "text/csv",
        )

with tab3:
    st.subheader("Add New Research Entry")
    # --- 2. NEW INPUT BOXES (Researcher & Printed Checkbox) ---
    with st.form("add_research_form", clear_on_submit=True):
        new_topic = st.text_input("Debate Topic")
        new_source = st.text_input("Source / Citation")
        new_summary = st.text_area("Key Summary / Arguments")
        new_researcher = st.text_input("Researcher Name (Who found this?)")
        new_printed = st.checkbox("Printed out already?")
        
        submit_button = st.form_submit_button("Save to Database")

        if submit_button:
            if new_topic and new_source and new_summary and new_researcher:
                new_id = int(df["id"].max()) + 1 if not df.empty and pd.notna(df["id"].max()) else 1
                new_row = {
                    "id": new_id, 
                    "topic": new_topic, 
                    "source": new_source, 
                    "summary": new_summary,
                    "researcher": new_researcher,
                    "printed": bool(new_printed)
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.success("Successfully added new research entry!")
                st.rerun()
            else:
                st.error("Please fill out all fields (Topic, Source, Summary, and Researcher Name).")
