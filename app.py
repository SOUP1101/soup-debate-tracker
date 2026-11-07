
import streamlit as st
import pandas as pd
from google import genai
import os

st.title("📚 S.O.U.P. Debate Research Tracker")
st.write("Manage team research, filter by topic, and query your database with Gemini AI!")

CSV_FILE = "research_log.csv"

# Load database safely
def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame(columns=["id", "topic", "source", "summary"])

df = load_data()

# Tab layout for organized UI
tab1, tab2, tab3 = st.tabs(["🔍 Query AI", "📋 View & Export Log", "➕ Add New Research"])

with tab1:
    st.subheader("Ask AI about Team Research")
    user_question = st.text_input("Enter your question:")
    if st.button("Ask AI Assistant"):
        if user_question:
            with st.spinner("Analyzing research log..."):
                api_key = os.environ.get("GEMINI_API_KEY")
                client = genai.Client(api_key=api_key)
                database_text = df.to_string()

                prompt = f"""
                You are a helpful research assistant for a high school debate team.
                Here is our team's current research log database:
                {database_text}

                Answer the following question based ONLY on the database provided:
                {user_question}
                """

                response = client.models.generate_content(
                    model='gemini-3.8-flash',
                    contents=prompt
                )
                st.success("Analysis Complete!")
                st.write(response.text)
        else:
            st.warning("Please enter a question first.")

with tab2:
    st.subheader("Current Research Database & Filters")

    # Topic Filter
    if not df.empty and "topic" in df.columns:
        topics = ["All"] + list(df["topic"].unique())
        selected_topic = st.selectbox("Filter by Topic:", topics)

        if selected_topic != "All":
            filtered_df = df[df["topic"] == selected_topic]
        else:
            filtered_df = df
    else:
        filtered_df = df

    st.dataframe(filtered_df)

    # Download CSV Button
    if not df.empty:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Research Log as CSV",
            data=csv_data,
            file_name="research_log.csv",
            mime="text/csv",
        )

with tab3:
    st.subheader("Add New Research Entry")
    with st.form("add_research_form"):
        new_topic = st.text_input("Debate Topic")
        new_source = st.text_input("Source / Citation")
        new_summary = st.text_area("Key Summary / Arguments")
        submit_button = st.form_submit_button("Save to Database")

        if submit_button:
            if new_topic and new_source and new_summary:
                new_id = len(df) + 1
                new_row = {"id": new_id, "topic": new_topic, "source": new_source, "summary": new_summary}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(CSV_FILE, index=False)
                st.success("Successfully added new research entry!")
                st.rerun()
            else:
                st.error("Please fill out all fields.")
