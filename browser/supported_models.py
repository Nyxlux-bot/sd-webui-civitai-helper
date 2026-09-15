"""Compatibility export; the catalogue is the single source of model names."""
from .catalog import MODEL_RECORDS

SUPPORTED_MODELS = [model["name"] for model in MODEL_RECORDS if not model["hidden"]]
