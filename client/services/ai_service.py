import json
import streamlit as st

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_aws import ChatBedrock
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from typing import Optional
from config import MODEL_OPTIONS


def create_llm_model(llm_provider: str, **kwargs):
    """Create a language model based on the selected provider."""
    params = st.session_state.get('params')

    if llm_provider == "OpenAI":
        return ChatOpenAI(
            openai_api_key=params.get("api_key"),
            model=MODEL_OPTIONS['OpenAI'],
            temperature=kwargs.get('temperature', 0.7),
        )
    elif llm_provider == "Antropic":
        return ChatAnthropic(
            anthropic_api_key=params.get("api_key"),
            model=MODEL_OPTIONS['Antropic'],
            temperature=kwargs.get('temperature', 0.7),
        )
    elif llm_provider == "Bedrock":
        import boto3
        # Initialize Bedrock client
        _bedrock = boto3.client(
            'bedrock-runtime',
            region_name=params.get("region_name"),
            aws_access_key_id=params.get("aws_access_key"),
            aws_secret_access_key=params.get("aws_secret_key"),
        )
        return ChatBedrock(
            client=_bedrock,
            model_id=MODEL_OPTIONS['Bedrock'],
            **kwargs
        )

    elif llm_provider == "Google":
        return ChatGoogleGenerativeAI(
            google_api_key=params.get("api_key"),
            model=MODEL_OPTIONS['Google'],
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 4096),
            max_retries=2,
        )
    elif llm_provider == "Groq":
        return ChatGroq(
            api_key=params.get("api_key"),  # groq_api_key expected here
            model=MODEL_OPTIONS['Groq'],
            temperature=kwargs.get("temperature", 0.7),
            streaming=kwargs.get("streaming", False)
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")
    

def get_response(prompt: str, llm_provider: str):
    """Get a response from the LLM using the standard LangChain interface."""
    try:
        # Create the LLM instance dynamically
        llm = create_llm_model(llm_provider)

        # Wrap prompt in a HumanMessage
        message = HumanMessage(content=prompt)

        # Invoke model and return the output content
        response = llm.invoke([message])
        return response.content

    except Exception as e:
        return f"Error during LLM invocation: {str(e)}"

def get_response_stream(
    prompt: str,
    llm_provider: str,
    system: Optional[str] = '',
    temperature: float = 1.0,
    max_tokens: int = 4096,
    **kwargs,
    ):
    """
    Get a streaming response from the selected LLM provider.
    All provider-specific connection/auth should be handled via kwargs.
    """
    try:
        # Add streaming and generation params to kwargs
        kwargs.update({
            "temperature": temperature,
            "max_tokens": max_tokens,
            "streaming": True
        })

        # Create the LLM with streaming enabled
        llm = create_llm_model(llm_provider, **kwargs)

        # Compose messages
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        # Stream the response
        stream_response = llm.stream(messages)
        return stream_response
    except Exception as e:
        st.error(f"[Error during streaming: {str(e)}]")
        st.stop()