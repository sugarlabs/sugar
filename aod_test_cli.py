#!/usr/bin/env python3
"""CLI harness to test Activity-on-Demand generation with any provider.

Examples:
    # Local template (no API key)
    PYTHONPATH=src python3 aod_test_cli.py --provider local-template \
        --prompt "a drawing activity where I can paint colorful shapes"

    # Gemini
    GEMINI_API_KEY=... PYTHONPATH=src python3 aod_test_cli.py --provider gemini \
        --prompt "a typing game for kids to practice spelling animals"

    # OpenAI-compatible endpoint
    OPENCODE_API_KEY=... PYTHONPATH=src python3 aod_test_cli.py \
        --provider opencode-go --model kimi-k2.7-code \
        --prompt "a fractions playground where teams build models"
"""

import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jarabe.model.aodspec import ActivitySpec
from jarabe.model.aodspec import name_from_prompt
from jarabe.model.aodpipeline import generate_activity
from jarabe.model.aodpipeline import PipelineError
from jarabe.model.aodllm import create_provider
from jarabe.model.aodllm import get_provider_statuses
from jarabe.model.aodllm import ProviderError


def _clean_error(error_text):
    """Strip redundant pipeline prefixes so testers see the real reasons."""
    text = str(error_text or '').strip()
    for prefix in (
            'Provider could not generate valid activity code: ',
            'Provider generated code did not pass validation: '):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    return text


def _status_table():
    print("Provider status:")
    for status in get_provider_statuses():
        mark = "OK" if status['available'] else "--"
        print("  [%s] %-14s %-22s %s" % (
            mark,
            status['name'],
            status['model'],
            status['reason'],
        ))
    print()


def _run_one(prompt, provider_name, model=None, category='creation',
              template='auto', license_id='GPL-3.0-or-later', age_band='all',
              use_rag=True, output_dir=None):
    spec = ActivitySpec(
        name=name_from_prompt(prompt),
        prompt=prompt,
        category=category,
        license_id=license_id,
        template=template,
        age_band=age_band,
    )
    errors = spec.validate()
    if errors:
        print("Spec errors:", errors)
        return None

    provider = None
    if provider_name not in ('local-template', 'local', 'template'):
        try:
            provider = create_provider(provider_name, model=model)
        except ProviderError as error:
            print("Provider error:", error)
            return None

    output_root = output_dir or tempfile.mkdtemp(prefix="aod_test_")
    print("Generating: %s" % spec.name)
    print("  provider : %s" % provider_name)
    print("  model    : %s" % (model or (provider.model if provider else 'template')))
    print("  template : %s" % template)
    print("  output   : %s" % output_root)
    print()

    captured_draft = ['']

    def _progress_cb(stage, fraction, message, metadata=None):
        print("  [%3d%%] %-12s %s" % (
            int(fraction * 100), stage, message))
        if isinstance(metadata, dict):
            draft = metadata.get('draft_activity_source', '')
            if isinstance(draft, str) and draft:
                captured_draft[0] = draft

    start = time.time()
    try:
        result = generate_activity(
            spec,
            output_root=output_root,
            provider=provider,
            provider_name=provider_name,
            use_rag=use_rag,
            progress_cb=_progress_cb,
        )
    except PipelineError as error:
        print("\nPipeline failed:\n%s" % _clean_error(str(error)))
        draft = captured_draft[0]
        if draft:
            draft_path = os.path.join(output_root, 'draft_activity.py')
            with open(draft_path, 'w', encoding='utf-8') as f:
                f.write(draft)
            print("\nDraft activity.py (failed validation) saved to:")
            print("  %s" % draft_path)
            print("  (%d chars, %d lines)" % (
                len(draft), draft.count('\n') + 1))
        print("\nTry:")
        print("  - A smaller or simpler prompt")
        print("  - A different model (--model kimi-k2.7-code)")
        print("  - A larger output budget "
              "(AOD_OPENROUTER_CODEGEN_MAX_TOKENS=32000)")
        return None

    elapsed = time.time() - start
    print("\nDone in %.1fs" % elapsed)
    print("  bundle_id: %s" % result.bundle_id)
    print("  project  : %s" % result.project_path)
    print("  bundle   : %s" % result.bundle_path)
    print("  provider : %s" % result.provider)
    print("  model    : %s" % result.model)
    print("  template : %s" % result.plan.get('template'))
    print("  code_src : %s" % result.plan.get('code_source', 'template'))
    if result.plan.get('provider_fallback_reason'):
        print("  plan_fallback: %s" % result.plan['provider_fallback_reason'])
    if result.plan.get('codegen_fallback_reason'):
        print("  code_fallback: %s" % result.plan['codegen_fallback_reason'])
    print("  files    : %s" % ', '.join(sorted(result.files.keys())))

    plan_path = os.path.join(result.project_path, 'aod_plan.json')
    if os.path.isfile(plan_path):
        with open(plan_path, encoding='utf-8') as f:
            plan = json.load(f)
        print("\nPlan summary:")
        for key in ('summary', 'learner_goal', 'learner_steps', 'word_bank'):
            print("  %s: %s" % (key, plan.get(key)))
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Test Activity-on-Demand generation.',
    )
    parser.add_argument('--provider', default='local-template',
                        help='Provider name (local-template, gemini, openai, '
                             'deepseek, qwen, moonshot, opencode, '
                             'opencode-go, claude, ollama)')
    parser.add_argument('--model', default=None,
                        help='Override model name')
    parser.add_argument('--prompt', required=True,
                        help='Activity description')
    parser.add_argument('--category', default='creation',
                        help='Activity category')
    parser.add_argument('--template', default='auto',
                        help='Template hint (auto, canvas, quiz, grid, ...)')
    parser.add_argument('--license', default='GPL-3.0-or-later',
                        help='License ID')
    parser.add_argument('--no-rag', action='store_true',
                        help='Disable RAG retrieval')
    parser.add_argument('--output', default=None,
                        help='Output directory (default: temp dir)')
    parser.add_argument('--status', action='store_true',
                        help='Show provider status and exit')

    args = parser.parse_args()

    if args.status:
        _status_table()
        return 0

    _status_table()
    result = _run_one(
        args.prompt,
        args.provider,
        model=args.model,
        category=args.category,
        template=args.template,
        license_id=args.license,
        use_rag=not args.no_rag,
        output_dir=args.output,
    )
    return 0 if result else 1


if __name__ == '__main__':
    sys.exit(main())
