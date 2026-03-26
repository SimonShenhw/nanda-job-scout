
from fastapi import FastAPI
import requests

app = FastAPI(title="Module D: LangGraph Workflow")

module_a_url = "http://127.0.0.1:8000/api/v1/search"
payload = {
    "query": "How to evaluate a candidate's teamwork skills",
    "top_k": 3
}
response = requests.post(module_a_url,json=payload)

print(response.status_code)
print(response.json())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
