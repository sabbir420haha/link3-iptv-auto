#!/usr/bin/env python3
"""Probe third-party dedicated cartoon stream candidates; no DRM bypass or rehosting."""
from pathlib import Path
import cartoon_stream_probe as mod
ROOT=Path(__file__).resolve().parent
mod.CAT=ROOT/"cartoon_dedicated_candidates.json"
mod.OUT=ROOT/"cartoon_dedicated_health.json"
if __name__=="__main__":
    mod.main()
