import json
from pathlib import Path

with open(Path("data/settings.json")) as f:
  config = json.load(f)

