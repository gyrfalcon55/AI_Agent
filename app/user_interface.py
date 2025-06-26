import streamlit as st
import requests
import uuid # For generating a unique session ID

# Base URL of your FastAPI backend
FASTAPI_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="TailorTalk Calendar Agent", layout="centered")
st.title("TailorTalk Calendar Agent")

# Initialize session state for chat history and session_id
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    # Generate a unique session ID for this user/session
    st.session_state.session_id = str(uuid.uuid4())

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask me about your calendar..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare data for FastAPI backend
    data = {
        "message": prompt,
        "session_id": st.session_state.session_id
    }

    try:
        # Make a POST request to your FastAPI backend's /chat endpoint
        with st.spinner("Thinking..."):
            response = requests.post(f"{FASTAPI_BASE_URL}/chat", json=data)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            backend_response = response.json().get("response", "No response from agent.")

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(backend_response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": backend_response})

    except requests.exceptions.ConnectionError:
        st.error(f"Could not connect to FastAPI backend at {FASTAPI_BASE_URL}. Is it running?")
        st.stop()
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred: {e}")
        st.stop()

# Optional: Add a "Clear Chat" button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4()) # Generate new session ID
    st.rerun()

st.info("Remember to keep your FastAPI backend running in a separate terminal!")