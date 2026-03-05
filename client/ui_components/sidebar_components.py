import streamlit as st
from config import MODEL_OPTIONS
import traceback
import json
from services.mcp_service import connect_to_mcp_servers
from services.chat_service import create_chat, delete_chat
from utils.tool_schema_parser import extract_tool_parameters
from utils.async_helpers import reset_connection_state


def create_history_chat_container():
    history_container = st.sidebar.container(height=200, border=None)
    with history_container:
        chat_history_menu = [
                f"{chat['chat_name']}_::_{chat['chat_id']}"
                for chat in st.session_state["history_chats"]
            ]
        chat_history_menu = chat_history_menu[:50][::-1]
        
        if chat_history_menu:
            current_chat = st.radio(
                label="History Chats",
                format_func=lambda x: x.split("_::_")[0] + '...' if "_::_" in x else x,
                options=chat_history_menu,
                label_visibility="collapsed",
                index=st.session_state["current_chat_index"],
                key="current_chat"
            )
            
            if current_chat:
                st.session_state['current_chat_id'] = current_chat.split("_::_")[1]


def create_sidebar_chat_buttons():
    with st.sidebar:
        c1, c2 = st.columns(2)
        create_chat_button = c1.button(
            "New Chat", use_container_width=True, key="create_chat_button"
        )
        if create_chat_button:
            create_chat()
            st.rerun()

        delete_chat_button = c2.button(
            "Delete Chat", use_container_width=True, key="delete_chat_button"
        )
        if delete_chat_button and st.session_state.get('current_chat_id'):
            delete_chat(st.session_state['current_chat_id'])
            st.rerun()

def create_model_select_widget():
    params = st.session_state["params"]
    params['model_id'] = st.sidebar.selectbox('🔎 Choose model',
                               options=MODEL_OPTIONS.keys(),
                               index=0)
    
def create_provider_select_widget():
    params = st.session_state.setdefault('params', {})
    # Load previously selected provider or default to the first
    default_provider = params.get("model_id", list(MODEL_OPTIONS.keys())[0])
    default_index = list(MODEL_OPTIONS.keys()).index(default_provider)
    # Provider selector with synced state
    selected_provider = st.sidebar.selectbox(
        '🔎 Choose Provider',
        options=list(MODEL_OPTIONS.keys()),
        index=default_index,
        key="provider_selection",
        on_change=reset_connection_state
    )
    # Save new provider and its index
    if selected_provider:
        params['model_id'] = selected_provider
        params['provider_index'] = list(MODEL_OPTIONS.keys()).index(selected_provider)

        # Show default model and allow custom override
        default_model = MODEL_OPTIONS[selected_provider]
        st.sidebar.info(f"Default: {default_model}")

        # Custom model input
        custom_model = st.sidebar.text_input(
            "🎯 Custom Model (optional)",
            value=params.get('custom_model', ''),
            placeholder=default_model,
            help=f"Leave empty to use default: {default_model}",
            key="custom_model_input"
        )

        # Store custom model if provided
        if custom_model:
            params['custom_model'] = custom_model
            st.sidebar.success(f"✅ Using: {custom_model}")
        else:
            params['custom_model'] = None

    # Dynamic input fields based on provider
    with st.sidebar.container():
        if selected_provider == "Bedrock":
            with st.expander("🔐 Bedrock Credentials", expanded=True):
                params['region_name'] = st.text_input("AWS Region", value=params.get('region_name'),key="region_name")
                params['aws_access_key'] = st.text_input("AWS Access Key", value=params.get('aws_access_key'), type="password", key="aws_access_key")
                params['aws_secret_key'] = st.text_input("AWS Secret Key", value=params.get('aws_secret_key'), type="password", key="aws_secret_key")
        else:
            with st.expander("🔐 API Key", expanded=True):
                params['api_key'] = st.text_input(f"{selected_provider} API Key", value=params.get('api_key'), type="password", key="api_key")
    

def create_advanced_configuration_widget():
    params = st.session_state["params"]
    with st.sidebar.expander("⚙️  Basic config", expanded=False):
        params['max_tokens'] = st.number_input("Max tokens",
                                    min_value=1024,
                                    max_value=10240,
                                    value=4096,
                                    step=512,)
        params['temperature'] = st.slider("Temperature", 0.0, 1.0, step=0.05, value=1.0)

def create_add_mcp_server_widget():
    """Widget to dynamically add MCP servers"""
    with st.sidebar.expander("➕ Add MCP Server", expanded=False):
        st.markdown("Add a custom MCP server")

        server_name = st.text_input(
            "Server Name",
            placeholder="MyServer",
            help="Unique name for this server",
            key="new_server_name"
        )

        server_url = st.text_input(
            "Server URL",
            placeholder="http://localhost:8002/sse",
            help="Full URL to the MCP server endpoint",
            key="new_server_url"
        )

        transport_type = st.selectbox(
            "Transport Type",
            options=["sse", "http"],
            index=0,
            help="Communication protocol",
            key="new_server_transport"
        )

        timeout = st.number_input(
            "Timeout (seconds)",
            min_value=10,
            max_value=3600,
            value=600,
            step=10,
            key="new_server_timeout"
        )

        sse_timeout = st.number_input(
            "SSE Read Timeout (seconds)",
            min_value=10,
            max_value=3600,
            value=900,
            step=10,
            key="new_server_sse_timeout"
        )

        # Headers input (JSON format)
        headers_json = st.text_area(
            "Headers (JSON, optional)",
            placeholder='{"Authorization": "Bearer token"}',
            help="Optional headers in JSON format",
            key="new_server_headers"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Add Server", use_container_width=True):
                # Validate inputs
                if not server_name or not server_url:
                    st.error("Server name and URL are required!")
                elif server_name in st.session_state.servers:
                    st.error(f"Server '{server_name}' already exists!")
                else:
                    # Parse headers if provided
                    headers = None
                    if headers_json.strip():
                        try:
                            headers = json.loads(headers_json)
                        except json.JSONDecodeError:
                            st.error("Invalid JSON format for headers!")
                            return

                    # Create server config
                    new_server = {
                        "transport": transport_type,
                        "url": server_url,
                        "timeout": timeout,
                        "sse_read_timeout": sse_timeout
                    }

                    if headers:
                        new_server["headers"] = headers

                    # Add to user_added_servers
                    st.session_state.user_added_servers[server_name] = new_server

                    # Update merged servers
                    st.session_state.servers[server_name] = new_server

                    st.success(f"✅ Added server: {server_name}")
                    st.rerun()

        with col2:
            if st.button("Clear Form", use_container_width=True):
                st.rerun()

def create_mcp_connection_widget():
    with st.sidebar:
        st.subheader("Server Management")

        with st.expander(f"MCP Servers ({len(st.session_state.servers)})", expanded=True):
            for name, config in st.session_state.servers.items():
                # Check if server is from config file or user-added
                is_user_added = name in st.session_state.get("user_added_servers", {})
                source_label = "📝 User Added" if is_user_added else "📄 From Config"

                with st.container(border=True):
                    st.markdown(f"**{name}** {source_label}")
                    st.markdown(f"**URL:** {config['url']}")
                    st.markdown(f"**Transport:** {config.get('transport', 'sse')}")

                    # Only allow removal of user-added servers
                    if is_user_added:
                        if st.button(f"🗑️ Remove", key=f"remove_{name}", use_container_width=True):
                            # Remove from user_added_servers
                            del st.session_state.user_added_servers[name]
                            # Remove from merged servers
                            del st.session_state.servers[name]
                            # Disconnect if connected
                            if st.session_state.get("agent"):
                                reset_connection_state()
                            st.rerun()
                    else:
                        st.info("🔒 Config file servers cannot be removed from UI")

        if st.session_state.get("agent"):
            st.success(f"📶 Connected to {len(st.session_state.servers)} MCP servers!"
                       f" Found {len(st.session_state.tools)} tools.")
            if st.button("Disconnect from MCP Servers", use_container_width=True):
                with st.spinner("Disconnecting from MCP servers..."):
                    try:
                        reset_connection_state()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error disconnecting from MCP servers: {str(e)}")
                        st.code(traceback.format_exc(), language="python")
        else:
            # Check if there are any servers to connect to
            if len(st.session_state.servers) == 0:
                st.error("❌ Cannot connect: No MCP servers configured!")
                st.info("💡 Add a server above or configure servers_config.json")
            else:
                st.warning("⚠️ Not connected to MCP servers")
                if st.button("Connect to MCP Servers", use_container_width=True):
                    with st.spinner("Connecting to MCP servers..."):
                        try:
                            connect_to_mcp_servers()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error connecting to MCP servers: {str(e)}")
                            st.code(traceback.format_exc(), language="python")

def create_mcp_tools_widget():
    with st.sidebar:
        if st.session_state.tools:
            st.subheader("🧰 Available Tools")

            selected_tool_name = st.selectbox(
                "Select a Tool",
                options=[tool.name for tool in st.session_state.tools],
                index=0
            )

            if selected_tool_name:
                selected_tool = next(
                    (tool for tool in st.session_state.tools if tool.name == selected_tool_name),
                    None
                )

                if selected_tool:
                    with st.container():
                        st.write("**Description:**")
                        st.write(selected_tool.description)

                        parameters = extract_tool_parameters(selected_tool)

                        if parameters:
                            st.write("**Parameters:**")
                            for param in parameters:
                                st.code(param)