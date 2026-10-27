#!/usr/bin/env python3
"""Read-only HTTP HLS checks for October 27 eight-show dedicated cartoon TEST candidates.
This does not modify production playlist or claim Link3 playback/audio/rights.
"""
from pathlib import Path
import cartoon_stream_probe as probe
ROOT=Path(__file__).resolve().parent
probe.CAT=ROOT/"cartoon_eight_show_candidates.json"
probe.OUT=ROOT/"cartoon_eight_show_health.json"
if __name__=="__main__":
    probe.main()
