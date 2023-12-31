import os

import pytest

from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen import ChatCompletion, config_list_from_json
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

try:
    from qdrant_client import QdrantClient
    from autogen.agentchat.contrib.qdrant_retrieve_user_proxy_agent import (
        create_qdrant_from_dir,
        QdrantRetrieveUserProxyAgent,
        query_qdrant,
    )
    import fastembed

    QDRANT_INSTALLED = True
except ImportError:
    QDRANT_INSTALLED = False

test_dir = os.path.join(os.path.dirname(__file__), "..", "test_files")


@pytest.mark.skipif(not QDRANT_INSTALLED, reason="qdrant_client is not installed")
def test_retrievechat():
    try:
        import openai
    except ImportError:
        return

    conversations = {}
    ChatCompletion.start_logging(conversations)

    config_list = config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": ["gpt-4", "gpt4", "gpt-4-32k", "gpt-4-32k-0314"],
        },
    )

    assistant = RetrieveAssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant.",
        llm_config={
            "request_timeout": 600,
            "seed": 42,
            "config_list": config_list,
        },
    )

    client = QdrantClient(":memory:")
    ragproxyagent = QdrantRetrieveUserProxyAgent(
        name="ragproxyagent",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,
        retrieve_config={
            "client": client,
            "docs_path": "./website/docs",
            "chunk_token_size": 2000,
        },
    )

    assistant.reset()

    code_problem = "How can I use FLAML to perform a classification task, set use_spark=True, train 30 seconds and force cancel jobs if time limit is reached."
    ragproxyagent.initiate_chat(assistant, problem=code_problem, silent=True)
    print(conversations)


@pytest.mark.skipif(not QDRANT_INSTALLED, reason="qdrant_client is not installed")
def test_qdrant_filter():
    client = QdrantClient(":memory:")
    create_qdrant_from_dir(dir_path="./website/docs", client=client, collection_name="autogen-docs")
    results = query_qdrant(
        query_texts=["How can I use AutoGen UserProxyAgent and AssistantAgent to do code generation?"],
        n_results=4,
        client=client,
        collection_name="autogen-docs",
        # Return only documents with "AutoGen" in the string
        search_string="AutoGen",
    )
    assert len(results["ids"][0]) == 4


@pytest.mark.skipif(not QDRANT_INSTALLED, reason="qdrant_client is not installed")
def test_qdrant_search():
    client = QdrantClient(":memory:")
    create_qdrant_from_dir(test_dir, client=client)

    assert client.get_collection("all-my-documents")

    # Perform a semantic search without any filter
    results = query_qdrant(["autogen"], client=client)
    assert isinstance(results, dict) and any("autogen" in res[0].lower() for res in results.get("documents", []))


if __name__ == "__main__":
    test_retrievechat()
    test_qdrant_filter()
    test_qdrant_search()
