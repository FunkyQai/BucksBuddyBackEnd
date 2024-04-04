import time
import yfinance as yf
import json
from openai import OpenAI
client = OpenAI(api_key="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")

ASSISTANT_ID = "asst_MYGwvgfuCnI1ckaTfhLSE1Zs"

def submit_message(assistant_id, thread, user_message):
    client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=user_message
    )
    return client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

def get_response(thread):
    return client.beta.threads.messages.list(thread_id=thread.id, order="asc")

def create_thread_and_run(user_input):
    thread = client.beta.threads.create()
    run = submit_message(ASSISTANT_ID, thread, user_input)
    return thread, run

def pretty_print(messages):
    last_message = messages.data[-1]  # Get the last message
    print(f"{last_message.role}:    {last_message.content[0].text.value}")
    print()

# Waiting in a loop
def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

def handle_run(run, thread, function_dispatch_table):
    while True:
        run = wait_on_run(run, thread)

        if run.status == "completed":
            pretty_print(get_response(thread))
            break

        elif run.status == "requires_action":
            required_actions = run.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []
            for action in required_actions["tool_calls"]:
                func_name = action["function"]["name"]
                arguments = json.loads(action["function"]["arguments"])

                func = function_dispatch_table.get(func_name)
                if func:
                    result = func(**arguments)  # ** unpacks the dictionary into keyword arguments
                    output = json.dumps(result) if not isinstance(result, str) else result
                    tool_outputs.append(
                        {
                            "tool_call_id": action["id"],
                            "output": output,
                        }
                    )
                else:
                    print(f"Function {func_name} not found in dispatch table")

            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
            continue

        else:
            # wait for 1s until run is completed or requires action
            time.sleep(1)
            continue

def get_stock_price(ticker):
    stock = yf.download(ticker)
    price = stock["Adj Close"][-1]
    return price

################################## Retrieval code ###################################################


# # Upload the file
# file = client.files.create(
#     file=open(
#         "data/retrieval_data.txt",
#         "rb",
#     ),
#     purpose="assistants",
# )
# # Update Assistant
# assistant = client.beta.assistants.update(
#     ASSISTANT_ID,
#     tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
#     file_ids=[file.id],
# )


##################################### Variables #################################################

#Define a dispatch table
function_dispatch_table = {
    "get_stock_price": get_stock_price,
}



