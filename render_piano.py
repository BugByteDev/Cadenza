"""Compatibility entry point for Cadenza's cross-platform sampled renderer."""
import json,sys
from pathlib import Path
from render_portable import render
if __name__=='__main__':print(json.dumps(render(json.loads(Path(sys.argv[1]).read_text()),Path(sys.argv[2])),indent=2))
