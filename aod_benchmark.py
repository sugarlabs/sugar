#!/usr/bin/env python3
"""Benchmark Activity-on-Demand across multiple providers/models.

Example:
    GEMINI_API_KEY=... OPENCODE_API_KEY=... PYTHONPATH=src python3 \
        aod_benchmark.py --providers gemini,opencode-go \
        --models gemini-2.5-flash,kimi-k2.7-code \
        --prompts prompts.txt --output /tmp/aod_benchmark
"""

import argparse
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jarabe.model.aodspec import ActivitySpec
from jarabe.model.aodspec import name_from_prompt
from jarabe.model.aodpipeline import generate_activity
from jarabe.model.aodpipeline import PipelineError
from jarabe.model.aodllm import create_provider
from jarabe.model.aodllm import ProviderError


def _generate_one(prompt, provider_name, model, output_root):
    spec = ActivitySpec(
        name=name_from_prompt(prompt),
        prompt=prompt,
        category='creation',
        license_id='GPL-3.0-or-later',
        template='auto',
        age_band='all',
    )
    errors = spec.validate()
    if errors:
        return {'error': 'spec: %s' % '; '.join(errors)}

    provider = None
    if provider_name != 'local-template':
        try:
            provider = create_provider(provider_name, model=model)
        except ProviderError as error:
            return {'error': 'provider: %s' % error}

    start = time.time()
    try:
        result = generate_activity(
            spec,
            output_root=output_root,
            provider=provider,
            provider_name=provider_name,
            use_rag=True,
        )
    except PipelineError as error:
        return {'error': 'pipeline: %s' % error}
    elapsed = time.time() - start

    return {
        'success': True,
        'elapsed': elapsed,
        'bundle_id': result.bundle_id,
        'project_path': result.project_path,
        'bundle_path': result.bundle_path,
        'provider': result.provider,
        'model': result.model,
        'template': result.plan.get('template'),
        'code_source': result.plan.get('code_source', 'template'),
        'provider_fallback': result.plan.get('provider_fallback_reason', ''),
        'codegen_fallback': result.plan.get('codegen_fallback_reason', ''),
        'codegen_attempts': result.plan.get('codegen_attempts', 0),
    }


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark AOD across providers.',
    )
    parser.add_argument('--providers', default='local-template',
                        help='Comma-separated provider names')
    parser.add_argument('--models', default=None,
                        help='Comma-separated model names (same length as '
                             'providers, or one shared model)')
    parser.add_argument('--prompts', required=True,
                        help='File with one prompt per line')
    parser.add_argument('--output', required=True,
                        help='Output directory for benchmark results')
    parser.add_argument('--csv', default='benchmark.csv',
                        help='CSV output filename')
    parser.add_argument('--json', default='benchmark.json',
                        help='JSON output filename')

    args = parser.parse_args()

    providers = [p.strip() for p in args.providers.split(',') if p.strip()]
    if args.models:
        models = [m.strip() for m in args.models.split(',') if m.strip()]
        if len(models) == 1:
            models = models * len(providers)
        elif len(models) != len(providers):
            print("--models must have one value or same count as --providers")
            return 1
    else:
        models = [''] * len(providers)

    with open(args.prompts, encoding='utf-8') as f:
        prompts = [line.strip() for line in f if line.strip()]

    os.makedirs(args.output, exist_ok=True)
    rows = []
    for provider_name, model in zip(providers, models):
        for index, prompt in enumerate(prompts, 1):
            run_dir = os.path.join(
                args.output,
                '%s_%s_prompt%d' % (provider_name, model or 'default', index),
            )
            os.makedirs(run_dir, exist_ok=True)
            print("[%s / %s] prompt %d: %s" % (
                provider_name, model or 'default', index, prompt[:60]))
            result = _generate_one(prompt, provider_name, model, run_dir)
            rows.append({
                'provider': provider_name,
                'model': model or '',
                'prompt_index': index,
                'prompt': prompt,
                **result,
            })
            status = 'OK' if result.get('success') else 'FAIL'
            print("  -> %s (%.1fs)" % (
                status, result.get('elapsed', 0.0)))

    csv_path = os.path.join(args.output, args.csv)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    json_path = os.path.join(args.output, args.json)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2)

    success = sum(1 for r in rows if r.get('success'))
    print("\nBenchmark complete: %d/%d succeeded" % (success, len(rows)))
    print("CSV: %s" % csv_path)
    print("JSON: %s" % json_path)
    return 0 if success == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
