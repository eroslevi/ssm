from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    nli_threshold: float = 0.85
    top_k_stage1: int = 5
    top_k_stage2: int = 10
    graph_hops: int = 2
    graph_max_articles: int = 50
    azure_endpoint: str = ""
    azure_api_key: str = ""
    azure_model: str = "gpt-4o"
    azure_api_version: str = "2024-02-01"
    stage2_system_prompt: str = ""
    stage2_user_prompt: str = ""
    data_dir: str = "data"


def load_config(path: str = "config.yaml") -> Config:
    p = Path(path)
    data: dict = {}
    if p.exists():
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    valid = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    cfg = Config(**valid)

    # Environment variables take precedence over yaml values
    _env = {
        "AZURE_OPENAI_ENDPOINT":    "azure_endpoint",
        "AZURE_OPENAI_API_KEY":     "azure_api_key",
        "AZURE_OPENAI_DEPLOYMENT":  "azure_model",
        "AZURE_OPENAI_API_VERSION": "azure_api_version",
    }
    for env_var, attr in _env.items():
        val = os.environ.get(env_var)
        if val:
            setattr(cfg, attr, val)

    return cfg
