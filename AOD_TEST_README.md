# Activity-on-Demand — Quick Test Harness

The Activity-on-Demand (AOD) backend and Home View UI panel are already implemented in this branch.

- Backend modules: `src/jarabe/model/aod*.py`
- UI panel: `src/jarabe/desktop/homebox.py` (`_CreateAIActivityPanel`)
- Toolbar entry point: `src/jarabe/desktop/viewtoolbar.py`

## Run the tests

```bash
PYTHONPATH=src python3 -m pytest tests/test_aod*.py -q
```

All 55 AOD tests should pass.

## Generate an activity from the command line

### Local template (no API key)

```bash
python3 aod_test_cli.py \
  --provider local-template \
  --prompt "a drawing activity where I can paint colorful shapes"
```

### Gemini

```bash
GEMINI_API_KEY=YOUR_KEY python3 aod_test_cli.py \
  --provider gemini \
  --model gemini-2.5-flash \
  --prompt "a quiz game about animals for young learners"
```

### OpenAI

```bash
OPENAI_API_KEY=YOUR_KEY python3 aod_test_cli.py \
  --provider openai \
  --model gpt-4.1-mini \
  --prompt "a typing practice activity with word bank"
```

### OpenCode Go (Kimi)

```bash
OPENCODE_API_KEY=YOUR_KEY python3 aod_test_cli.py \
  --provider opencode-go \
  --model kimi-k2.7-code \
  --prompt "a fractions playground where teams build models"
```

### Ollama (local)

```bash
AOD_LLM_PROVIDER=ollama AOD_OLLAMA_MODEL=llama3.1 python3 aod_test_cli.py \
  --provider ollama \
  --prompt "a simple calculator tool for fractions"
```

## Benchmark multiple providers/models

Create a `prompts.txt` file with one prompt per line, then:

```bash
GEMINI_API_KEY=... OPENCODE_API_KEY=... python3 aod_benchmark.py \
  --providers gemini,opencode-go \
  --models gemini-2.5-flash,kimi-k2.7-code \
  --prompts aod_sample_prompts.txt \
  --output /tmp/aod_benchmark
```

Results are written to `benchmark.csv` and `benchmark.json` in the output directory.

## Check provider status

```bash
python3 aod_test_cli.py --status
```

## Test from Python directly

```python
import sys
sys.path.insert(0, 'src')

from jarabe.model.aodspec import ActivitySpec, name_from_prompt
from jarabe.model.aodpipeline import generate_activity
from jarabe.model.aodllm import create_provider

spec = ActivitySpec(
    name=name_from_prompt("a drawing activity where I can paint colorful shapes"),
    prompt="a drawing activity where I can paint colorful shapes",
    category="creation",
    license_id="GPL-3.0-or-later",
)

provider = create_provider('gemini')  # requires GEMINI_API_KEY
result = generate_activity(spec, provider=provider, provider_name='gemini')
print(result.bundle_path)
```

## Notes

- The generated `.xo` bundle is placed under `~/.sugar/default/aod/projects/` by default, or in the directory you pass with `--output`.
- The Home View UI panel can only be fully exercised inside a running Sugar session because it depends on D-Bus, Telepathy, and the full GTK3 desktop stack.
