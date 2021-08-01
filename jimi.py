import json
from pathlib import Path

with open(str(Path("data/settings.json"))) as f:
	config = json.load(f)

from core import function
from core import helpers

from core import db
from core import settings
from core import cache
# Fix settings cache expiry time
cache.globalCache.updateCacheSettings("settingsCache",cacheExpiry=3600)
from core import logging
from core import api
from core import auth
from core import admin, audit, cluster, debug, flow, model, plugin, scheduler, static, storage, workers, exceptions
from core.models import  action, conduct, trigger, webui

from system import logic, variable, system

from system.models import trigger as systemTrigger
