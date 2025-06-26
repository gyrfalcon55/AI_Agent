import ast # Added for safely evaluating string representations of tool outputs
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import datetime

# Import necessary components for LangGraph
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI # CHANGED: Import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .agent_state import AgentState
from .agent_tools import agent_tools, check_calendar_availability_tool, create_calendar_event_tool

# Load environment variables (for GOOGLE_API_KEY)
from dotenv import load_dotenv
load_dotenv()

# --- LangGraph Agent Setup ---
# Initialize ChatGoogleGenerativeAI
# It will automatically pick up GOOGLE_API_KEY from your .env file
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0) # CHANGED: Using ChatGoogleGenerativeAI with Gemini model
llm_with_tools = llm.bind_tools(agent_tools)

# Define the graph nodes
def call_model(state: AgentState):
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def call_tool(state: AgentState):
    last_message = state['messages'][-1]
    tool_output_list = []
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            tool_result = None
            if tool_name == "check_calendar_availability_tool":
                tool_result = check_calendar_availability_tool.invoke(tool_args)
            elif tool_name == "create_calendar_event_tool":
                tool_result = create_calendar_event_tool.invoke(tool_args)
            else:
                tool_result = f"Error: Unknown tool {tool_name}"

            tool_output_list.append(tool_result)

    # Store tool output as a string representation in the state
    return {"tool_output": str(tool_output_list)}

# Define the graph
workflow = StateGraph(AgentState)

workflow.add_node("call_model", call_model)
workflow.add_node("call_tool", call_tool)

# Add edges
workflow.add_edge("call_model", "call_tool")
workflow.add_edge("call_tool", END)

# Set entry point
workflow.set_entry_point("call_model")

# Compile the graph
memory = MemorySaver()
app_agent = workflow.compile(checkpointer=memory)

# --- FastAPI Application Setup ---
app = FastAPI(title="TailorTalk Calendar Agent")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return {"message": "Welcome to TailorTalk Backend! Connect to Streamlit frontend."}

from pydantic import BaseModel # Ensure this import is here

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session" # Optional with default value

@app.post("/chat")
async def chat_endpoint(chat_request: ChatRequest):
    user_message = chat_request.message
    session_id = chat_request.session_id

    if not user_message:
        return {"response": "Please provide a message."}

    try:
        config = {"configurable": {"thread_id": session_id}}

        input_message = {"messages": [HumanMessage(content=user_message)]}

        final_state = app_agent.invoke(input_message, config=config)

        agent_response_message = final_state['messages'][-1]
        tool_output_raw = final_state.get('tool_output', '[]') # Get raw string output from LangGraph state

        # Start with the agent's primary text response
        agent_text_response = agent_response_message.content

        # --- Enhanced Tool Output Formatting Logic ---
        formatted_tool_output = ""
        try:
            # Safely convert the string representation of the tool output back to a Python object
            tool_data = ast.literal_eval(tool_output_raw)

            if tool_data: # If the tool output list is not empty, process it
                # Case 1: Event Creation Output (expecting a list with one event dict)
                # Check for 'kind' and 'calendar#event' to confirm it's an event object
                if isinstance(tool_data, list) and len(tool_data) > 0 and \
                   isinstance(tool_data[0], dict) and \
                   tool_data[0].get('kind') == 'calendar#event':
                    
                    event = tool_data[0]
                    summary = event.get('summary', 'An event')
                    html_link = event.get('htmlLink', '#')
                    start_time = event.get('start', {}).get('dateTime', 'N/A')
                    end_time = event.get('end', {}).get('dateTime', 'N/A')

                    formatted_tool_output = (
                        f"\n\n**✅ Event Created Successfully!**\n"
                        f"- **Title:** {summary}\n"
                        f"- **Time:** {start_time} to {end_time}\n"
                        f"- **View Event:** [Click here]({html_link})\n"
                        f"*(Please check your Google Calendar for full details and invites.)*"
                    )
                # Case 2: Availability Check Output (expecting a list of busy slots)
                # Check if it's a list and all items are dicts with 'start' and 'end'
                elif isinstance(tool_data, list) and all(isinstance(item, dict) and 'start' in item and 'end' in item for item in tool_data):
                    if tool_data: # If there are actual busy slots found
                        formatted_output_slots = []
                        for slot in tool_data:
                            formatted_output_slots.append(
                                f"  - From `{slot.get('start', 'N/A')}` to `{slot.get('end', 'N/A')}`"
                            )
                        formatted_tool_output = (
                            f"\n\n**🗓️ Calendar Availability:**\n"
                            f"The following slots are busy:\n"
                            + "\n".join(formatted_output_slots) # <--- CHANGE THIS LINE
                        )
                    else: # No busy slots found
                        formatted_tool_output = "\n\n**✅ Calendar Availability:** You appear to be free during that period!"
                # Case 3: Other or unexpected tool output (fallback to raw JSON/string)
                else:
                    formatted_tool_output = f"\n\n**⚙️ Raw Tool Output:**\n```json\n{tool_output_raw}\n```"
            # If tool_data is empty (e.g., '[]'), formatted_tool_output remains an empty string,
            # and nothing will be added, which is the desired behavior for no tool output.

        except (ValueError, SyntaxError) as e:
            # Fallback if ast.literal_eval fails (e.g., malformed string in tool_output_raw)
            print(f"Error parsing tool output string: {tool_output_raw} - {e}")
            formatted_tool_output = f"\n\n**⚠️ Tool Output Parsing Error:**\n```\n{tool_output_raw}\n```"

        # Append the formatted tool output only if it's not empty
        if formatted_tool_output:
            agent_text_response += formatted_tool_output

        return {"response": agent_text_response}

    except Exception as e:
        print(f"Error processing chat message: {e}")
        return {"response": f"Sorry, an internal error occurred: {e}"}

if __name__ == "__main__":
    import uvicorn
    Path("static").mkdir(exist_ok=True) # Ensure static directory exists
    uvicorn.run(app, host="0.0.0.0", port=8000)