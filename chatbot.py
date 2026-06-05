import os 
import json
import time
import streamlit as st

from langchain_groq import ChatGroq
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory

# Setup
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="Groq AI Assistant", page_icon="💬")

st.title("💬 Groq Chatbot with Memory")

with st.sidebar:
    st.subheader("Controls")
    model_name = st.selectbox(
        "Groq Model",
        ["qwen/qwen3-32b","llama-3.1-8b-instant","openai/gpt-oss-20b"], index = 1
    )

    temperature = st.slider( "Temperature (Creativity)", 0.2,0.9,0.7)

    max_tokens = st.slider("Max Tokens", 10, 300, 150)

    system_prompt = st.text_area(
        "System prompt (rules)",
        value = "You are a helpful, concise teaching assistant. Use short, clear explanation."
    )
    st.caption("Tip: Lower temperature for factual task; raise temperature for brainstorming.")

    if st.button(" Clear Chat"):
        st.session_state.pop("history",None)
        st.rerun()


# api key guard
if not api_key:
    st.error("Missing GROQ_API_KEY. Add it to your .env (deployment secret).")
    st.stop()

#initialize single history
if "history" not in st.session_state:
    st.session_state.history = InMemoryChatMessageHistory()

# LLM  + prompt + chain
# chatgroq reads GROQ_API_KEY from .env
llm = ChatGroq(
    model = model_name,
    temperature=temperature,
    max_tokens=max_tokens
)

# role structured prompt : sytem -> history -> human
prompt = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

chain = prompt | llm | StrOutputParser()

# WRAP WITH MESSAGE HISTORY

chat_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: st.session_state.history,
    input_messages_key="input",
    history_messages_key="history",
)

# render existing conversations
# only show human/ai messages (skip system if present)

for msg in st.session_state.history.messages:
    role = getattr(msg, "type", None) or getattr(msg, "role","")
    content = msg.content
    if role == "human":
        st.chat_message("user").write(content)
    elif role in ("ai","assistant"):
        st.chat_message("assistant").write(content)

# handle user turn

user_input = st.chat_input("Type your message....")

if user_input:
    st.chat_message("user").write(user_input)

    # invoke the chai with history tracking

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            response_text = chat_with_history.invoke(
                {"input": user_input, "system_prompt": system_prompt},
                config = {"configurable": {"session_id": "default"}},
            )
        except Exception as e:
            st.error(f"Model error: {e}")
            response_text = ""

        typed = ""
        for ch in response_text:
            typed += ch
            placeholder.markdown(typed)

# Download chat history

if st.session_state.history.messages:
    export = []
    for m in st.session_state.history.messages:
        role = getattr(m, "type", None) or getattr(m,"role","")
        if role == "human":
            export.append({"role":"user","text": m.content})
        elif role in ("ai","assistant"):
            export.append({"role": "assistant","text": m.content})

    st.download_button(
        "Download chat JSON",
        data = json.dumps(export, ensure_ascii=False, indent=2),
        file_name= "chat_history.json",
        mime = "application/json",
        use_container_width=True,
    )
