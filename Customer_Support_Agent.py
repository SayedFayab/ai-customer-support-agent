import streamlit as st
import pandas as pd
import pathlib, os, re, json
from openai import OpenAI

# --- OpenAI API Setup ---
# KEY_PATH = pathlib.Path(r"C:\Users\fayab\Desktop\AI\GENAI\API_Keys\OPENAI_API_KEY.txt")
# os.environ["OPENAI_API_KEY"] = KEY_PATH.read_text().strip()

# Load OpenAI API key from Streamlit secrets
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

client = OpenAI()

# --- Orders ---
if "orders_df" not in st.session_state:
    st.session_state.orders_df = pd.DataFrame(
        [
            {"order_id": "ORD-1001", "status": "processing", "total": 49.99},
            {"order_id": "ORD-1002", "status": "shipped", "total": 19.95},
            {"order_id": "ORD-1003", "status": "processing", "total": 5.00},
        ]
    ).set_index("order_id")

# --- Chat history ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a customer support assistant. You can place or cancel orders."},
        {"role": "assistant", "content": "Hello! How can I help you today?"}
    ]

# --- Tool functions ---
def place_order(total: float):
    new_id = f"ORD-{len(st.session_state.orders_df) + 1001}"
    st.session_state.orders_df.loc[new_id] = {"status": "processing", "total": total}
    return f"✅ Order {new_id} placed with total ${total:.2f}."

def cancel_order(order_id: str):
    if order_id in st.session_state.orders_df.index:
        status = st.session_state.orders_df.loc[order_id, "status"]
        if status == "cancelled":
            return f"⚠️ Order {order_id} is already cancelled."
        elif status == "shipped":
            return f"⚠️ Order {order_id} has already been shipped and cannot be cancelled."
        else:
            st.session_state.orders_df.loc[order_id, "status"] = "cancelled"
            return f"🛑 Order {order_id} has been successfully cancelled."
    return f"⚠️ Order {order_id} not found."

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place a new order with a total amount.",
            "parameters": {
                "type": "object",
                "properties": {"total": {"type": "number"}},
                "required": ["total"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel an order by ID if possible.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"]
            }
        }
    }
]

# --- Chat function ---
def chat_with_agent(user_input: str):
    st.session_state.messages.append({"role": "user", "content": user_input})

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0
    )

    msg = resp.choices[0].message

    # If model decided to call a tool
    if msg.tool_calls:
        tool_response_texts = []
        for call in msg.tool_calls:
            fn_name = call.function.name
            args = json.loads(call.function.arguments or "{}")

            if fn_name == "place_order":
                result = place_order(args.get("total", 10.0))
            elif fn_name == "cancel_order":
                result = cancel_order(args.get("order_id", ""))
            else:
                result = "Unknown tool."

            tool_response_texts.append(result)

        # Append the tool execution results as assistant message
        final_reply = "\n".join(tool_response_texts)
    else:
        final_reply = msg.content or "I'm not sure how to respond."

    st.session_state.messages.append({"role": "assistant", "content": final_reply})
    return final_reply

# --- Streamlit UI ---
st.title("🤖 Customer Support Agent")

# Show chat history
for m in st.session_state.messages:
    if m["role"] == "user":
        st.chat_message("user").write(m["content"])
    elif m["role"] == "assistant":
        st.chat_message("assistant").write(m["content"])

# Chat input
if user_input := st.chat_input("Type your message here..."):
    st.chat_message("user").write(user_input)
    reply = chat_with_agent(user_input)
    st.chat_message("assistant").write(reply)

# Orders table
st.write("### Current Orders")
st.dataframe(st.session_state.orders_df)


