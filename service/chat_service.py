from retrieve_service import retrieve
from langgraph.graph import MessagesState

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver

from langchain_community.chat_models.tongyi import ChatTongyi

llm = ChatTongyi(
    model="qwen3-max"
)


def query_or_respond(state: MessagesState):
    system_messages_content = "You can use the tool to retrieve relevant information to help answer the user's question. And don't answer directly using your own knowledge"

    conversation_messages = [
        message
        for message in state['messages']
        if message.type in ("human", "system") or (message.type == 'ai' and not message.tool_calls)
    ][:-20]

    prompt = [SystemMessage(system_messages_content)] + conversation_messages

    llm_with_tool = llm.bind_tools([retrieve])
    response = llm_with_tool.invoke(prompt)
    return {'message': response}


def generate(state: MessagesState):
    recent_tool_messages = []
    for message in reversed(state['messages']):
        if message.type == 'tool':
            recent_tool_messages.append(message)
        else:
            break

    tool_messages = recent_tool_messages[::-1]

    docs_content = '\n\n'.join(doc.contet for doc in tool_messages)
    system_messages_content = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer the question. "
    "If you don't know the answer, just say that you don't know. "
    f"Context: {docs_content}")

    conversation_messages = [
        message
        for message in state['messages']
        if message.type in ("human", "system") or (message.type == 'ai' and not message.tool_calls)
    ][:-20]

    prompt = [SystemMessage(system_messages_content)] + conversation_messages
    response = llm.invoke(prompt)
    return {'message': response}


workflow = StateGraph(MessagesState)

tools = ToolNode([retrieve])

# Define the nodes we will cycle between
workflow.add_node(query_or_respond)
workflow.add_node(tools)
workflow.add_node(generate)

workflow.set_entry_point("query_or_respond")
workflow.add_conditional_edges(
    "query_or_respond",
    tools_condition,
    {END:END, "tools":"tools"}
)

workflow.add_edge('tools', "generate")
workflow.add_edge("generate", END)

checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)



def chat(question, knowledge_base_id, session_id):
    config = {"configurable": {"thread_id": f'{knowledge_base_id}:{session_id}'}}
    for step in graph.stream(
        {'messages': [{"role": "user", "content": question}]},
        stream_mode='values',
        config=config
    ):
        print("---")

    return step['messages'][-1].content




