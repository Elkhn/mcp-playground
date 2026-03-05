import streamlit as st
from config import SERVER_CONFIG
import uuid

# Session state initialization
def init_session():
    # Initialize user_added_servers first if not exists
    if "user_added_servers" not in st.session_state:
        st.session_state["user_added_servers"] = {}

    # Merge servers from config file and user-added servers
    merged_servers = {**SERVER_CONFIG['mcpServers'], **st.session_state.get("user_added_servers", {})}

    defaults = {
        "params": {},
        "current_chat_id": None,
        "current_chat_index": 0,
        "history_chats": get_history(),
        "messages": [],
        "client": None,
        "agent": None,
        "tools": [],
        "tool_executions": [],
        "servers": merged_servers,
        "config_file_servers": SERVER_CONFIG['mcpServers']  # Keep track of file-based servers
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Always update servers with latest merge
    st.session_state["servers"] = merged_servers


def get_history():
    if "history_chats" in st.session_state and st.session_state["history_chats"]:
        return st.session_state["history_chats"]
    else:
        chat_id = str(uuid.uuid4())
        new_chat = {'chat_id': chat_id,
                    'chat_name': 'New chat',
                    'messages': []}
        st.session_state["current_chat_index"] = 0
        st.session_state["current_chat_id"] = chat_id
    return [new_chat]

def get_current_chat(chat_id):
    """Get messages for the current chat."""
    for chat in st.session_state["history_chats"]:
        if chat['chat_id'] == chat_id:
            return chat['messages']
    return []

def _append_message_to_session(msg: dict) -> None:
    """
    Append *msg* to the current chat’s message list **and**
    keep history_chats in-sync.
    """
    chat_id = st.session_state["current_chat_id"]
    st.session_state["messages"].append(msg)
    for chat in st.session_state["history_chats"]:
        if chat["chat_id"] == chat_id:
            chat["messages"] = st.session_state["messages"]     # same list
            if chat["chat_name"] == "New chat":                 # rename once
                chat["chat_name"] = " ".join(msg["content"].split()[:5]) or "Empty"
            break

def create_chat():
    """Create a new chat session."""
    chat_id = str(uuid.uuid4())
    new_chat = {'chat_id': chat_id,
                'chat_name': 'New chat',
                'messages': []}
    
    st.session_state["history_chats"].append(new_chat)
    st.session_state["current_chat_index"] = 0
    st.session_state["current_chat_id"] = chat_id
    return new_chat

def delete_chat(chat_id: str):
    """Delete a chat from history."""
    if not chat_id: # protection against accidental call
        return

    # 1) Remove from session_state.history_chats
    st.session_state["history_chats"] = [
        c for c in st.session_state["history_chats"]
        if c["chat_id"] != chat_id
    ]

    # 2) Switch current_chat to another one or create new
    if st.session_state["current_chat_id"] == chat_id:
        if st.session_state["history_chats"]:            # if chats still exist
            first = st.session_state["history_chats"][0]
            st.session_state["current_chat_id"] = first["chat_id"]
            st.session_state["current_chat_index"] = 0
            st.session_state["messages"] = first["messages"]
        else:                                            # if all deleted → new empty
            new_chat = create_chat()
            st.session_state["messages"] = new_chat["messages"]
    return