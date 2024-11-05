import time
import openai
from rich.console import Console

console = Console()


def get_openai_recommendation(report_file_path, gpt_model):
    console.log("[cyan]Requesting recommendation from OpenAI...[/cyan]")

    # Initialize OpenAI client (it will automatically use the API key from environment variables)
    client = openai.OpenAI()

    # Step 1: Upload the report file to OpenAI
    with open(report_file_path, "rb") as report_file:
        uploaded_file = client.files.create(file=report_file, purpose="assistants")
    file_id = uploaded_file.id

    if not file_id:
        console.log("[red]Error: Failed to upload the report to OpenAI.[/red]")
        return ""

    # Step 2: Create a new thread
    thread_response = client.beta.threads.create()
    thread_id = thread_response.id

    if not thread_id:
        console.log("[red]Error: Failed to create a new thread in OpenAI.[/red]")
        return ""

    # Step 3: Send a message to the thread
    message_response = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content="Attached is a Kubernetes cluster report. Please analyze it and provide a concise and actionable recommendation to improve the overall health of the cluster. Focus on issues related to deployments, pods, metrics server, and CrashLoopBackOff. Only return the result in HTML to put in a innerHTML format with a good style, without using ``` or any other code block delimiters.",
        attachments=[{"file_id": file_id, "tools": [{"type": "file_search"}]}],
    )
    message_id = message_response.id

    if not message_id:
        console.log("[red]Error: Failed to send a message to OpenAI.[/red]")
        return ""

    # Step 4: Create the assistant using GPT-4o
    assistant_response = client.beta.assistants.create(
        instructions="You are an assistant that provides actionable recommendations based on Kubernetes cluster reports. Consider that Cast.ai is used to analyze resources taints issues that could be normal when using dynamic auto-scaling.",
        name="Kubernetes Health Assistant",
        tools=[{"type": "file_search"}],
        model=gpt_model,
        temperature=0.7,
        top_p=1.0,
    )
    assistant_id = assistant_response.id

    if not assistant_id:
        console.log("[red]Error: Failed to create the assistant in OpenAI.[/red]")
        return ""

    # Step 5: Create a run for the thread with the assistant
    run_response = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=assistant_id
    )
    run_id = run_response.id

    if not run_id:
        console.log("[red]Error: Failed to create a run in OpenAI.[/red]")
        return ""

    # Step 6: Wait for the run to complete
    while True:
        time.sleep(5)  # Wait a few seconds before trying to get the response
        run_status_response = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )
        status = run_status_response.status

        if status == "completed":
            break
        elif status == "failed":
            console.log("[red]Error: The run has failed.[/red]")
            return ""

    # Step 7: Retrieve the final message from the assistant
    messages_response = client.beta.threads.messages.list(thread_id=thread_id)
    messages = messages_response.data

    # Extract the content from the last message
    recommendation = messages[0].content[0].text.value if messages else ""

    return recommendation
