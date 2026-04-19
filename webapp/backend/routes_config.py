import json
import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/config", tags=["config"])

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
MODELS_PATH = os.path.join(PROJECT_ROOT, "src", "llm", "api_models.json")

API_KEY_PROVIDERS = [
    {"env_var": "OPENAI_API_KEY", "provider": "OpenAI"},
    {"env_var": "ANTHROPIC_API_KEY", "provider": "Anthropic"},
    {"env_var": "DEEPSEEK_API_KEY", "provider": "DeepSeek"},
    {"env_var": "GROQ_API_KEY", "provider": "Groq"},
    {"env_var": "GOOGLE_API_KEY", "provider": "Google"},
    {"env_var": "XAI_API_KEY", "provider": "xAI"},
    {"env_var": "OPENROUTER_API_KEY", "provider": "OpenRouter"},
    {"env_var": "GIGACHAT_API_KEY", "provider": "GigaChat"},
]


@router.get("/models")
def get_models():
    with open(MODELS_PATH, "r") as f:
        return json.load(f)


@router.get("/api-keys")
def get_api_keys():
    return [
        {"provider": p["provider"], "env_var": p["env_var"], "is_set": bool(os.environ.get(p["env_var"]))}
        for p in API_KEY_PROVIDERS
    ]


class ApiKeyUpdate(BaseModel):
    keys: dict[str, str]


@router.put("/api-keys")
def update_api_keys(body: ApiKeyUpdate):
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()

    for env_var, value in body.keys.items():
        if not value:
            continue
        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{env_var}="):
                lines[i] = f"{env_var}={value}\n"
                found = True
                break
        if not found:
            lines.append(f"{env_var}={value}\n")
        os.environ[env_var] = value

    with open(ENV_PATH, "w") as f:
        f.writelines(lines)

    return {"status": "ok"}
