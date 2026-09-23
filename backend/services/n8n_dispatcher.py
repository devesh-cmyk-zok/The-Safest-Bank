import httpx
import os

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/fraud-alert")

async def trigger_n8n_workflow(payload: dict):
    """
    Asynchronously dispatches incident data and agent outputs to the n8n webhook canvas.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(N8N_WEBHOOK_URL, json=payload)
            return response.status_code == 200
    except Exception as e:
        print(f"[n8n Dispatch Warning] Could not connect to n8n webhook: {e}")
        return False