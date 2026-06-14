from __future__ import annotations

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
    stage2_system_prompt: str = ""
    stage2_user_prompt: str = ""
    data_dir: str = "data"


def load_config(path: str = "config.yaml") -> Config:
    p = Path(path)
    if not p.exists():
        return Config()
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    valid = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    return Config(**valid)
