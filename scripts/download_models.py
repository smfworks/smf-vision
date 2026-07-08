#!/usr/bin/env python3
"""download_models.py — fetch the Qwen3.5-0.8B model + mmproj from HuggingFace."""
import sys
from pathlib import Path

REPO = "unsloth/Qwen3.5-0.8B-GGUF"
FILES = ["Qwen3.5-0.8B-UD-Q4_K_XL.gguf", "mmproj-F16.gguf"]


def main() -> None:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        sys.exit("huggingface-hub not installed. Run: pip install huggingface-hub")

    out = Path(__file__).resolve().parent.parent / "models"
    out.mkdir(exist_ok=True)

    for fname in FILES:
        target = out / fname
        if target.exists():
            print(f"exists: {target}")
            continue
        print(f"downloading: {fname}")
        hf_hub_download(repo_id=REPO, filename=fname, local_dir=str(out))
    print(f"done — models in {out}")


if __name__ == "__main__":
    main()