from dotenv import load_dotenv
import time
load_dotenv()

# State machine
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

# model
from langchain_google_genai import ChatGoogleGenerativeAI

gemini_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

# web search tool
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import Tool

serper_search = GoogleSerperAPIWrapper()

search_tool = Tool(
                  name="Intermediate_Answer", #this name shouldnt have space
                  func=serper_search.run,
                  description="useful for when you need to ask with search",
              )

# memory
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string(":memory:")

# tools
tools = [search_tool]

# bind llm with tools
model_with_tools = gemini_llm.bind_tools(tools)

def llm_node(state: State):
    model_output = [model_with_tools.invoke(state["messages"])]
    time.sleep(4)
    return {"messages": model_output}
  
from langgraph.prebuilt import ToolNode, tools_condition

toolNodes = ToolNode(tools=tools)

graph_builder.add_node("llm_node", llm_node)

graph_builder.add_node("tool_node", toolNodes)

graph_builder.add_conditional_edges(
    "llm_node",
    tools_condition,
    {"tools": "tool_node", "__end__": "__end__"},
)
graph_builder.add_edge("tool_node", "llm_node")

# entry point
graph_builder.set_entry_point("llm_node")

# exit point
# graph_builder.set_finish_point("chatbot with web search")

# compile the graph
graph = graph_builder.compile(
    checkpointer=memory,
    )