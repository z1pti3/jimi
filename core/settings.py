import json
from pathlib import Path

with open(str(Path("data/settings.json"))) as f:
  config = json.load(f)

