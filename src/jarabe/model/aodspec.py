# Copyright (C) 2026 Sugar Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import asdict
from dataclasses import dataclass
import re


CATEGORIES = (
    'logic_math',
    'science',
    'language',
    'tools_utils',
    'games',
    'creation',
)

CATEGORY_FALLBACK = 'creation'

CODE_SIZES = ('compact', 'standard', 'full')

MAX_PROMPT_LENGTH = 12000

TEMPLATES = (
    'auto',
    'canvas',
    'carrom',
    'chess',
    'grid',
    'narrative',
    'quiz',
    'utility',
)

LICENSE_IDS = (
    'MIT',
    'GPL-3.0-or-later',
    'Apache-2.0',
    'AGPL-3.0-or-later',
    'LGPL-3.0-or-later',
    'MPL-2.0',
    'BSD-3-Clause',
)


@dataclass
class ActivitySpec:
    """A validated, provider-independent activity generation request."""

    name: str
    prompt: str
    category: str
    license_id: str
    template: str = 'auto'
    age_band: str = 'all'
    learner_goal: str = ''
    code_size: str = 'standard'

    def validate(self):
        errors = []

        if not isinstance(self.name, str) or not self.name.strip():
            errors.append('Activity name is required.')
        elif len(self.name.strip()) > 80:
            errors.append('Activity name must be 80 characters or fewer.')

        if not isinstance(self.prompt, str) or not self.prompt.strip():
            errors.append('Activity prompt is required.')
        elif len(self.prompt.strip()) > MAX_PROMPT_LENGTH:
            errors.append(
                'Activity prompt must be %d characters or fewer.'
                % MAX_PROMPT_LENGTH
            )

        if self.category not in CATEGORIES:
            errors.append('Unknown activity category: %s' % self.category)

        if self.template not in TEMPLATES:
            errors.append('Unknown activity template: %s' % self.template)

        if self.license_id not in LICENSE_IDS:
            errors.append('Unknown activity license: %s' % self.license_id)

        if not isinstance(self.age_band, str) or not self.age_band.strip():
            errors.append('Activity age band is required.')

        if self.code_size not in CODE_SIZES:
            errors.append('Unknown code size: %s' % self.code_size)

        return errors

    def normalized(self):
        """Return a copy with whitespace normalized and soft steering
        fields coerced to safe values.

        Category, template, and code size only steer the plan, so an
        unrecognized value (from UI drift or an older saved session)
        falls back to a sensible default instead of failing the whole
        generation.
        """
        name = _normalize_spaces(self.name)
        if isinstance(name, str):
            name = name[:80]
        prompt = self.prompt.strip() if isinstance(self.prompt, str) \
            else self.prompt
        return ActivitySpec(
            name=name,
            prompt=prompt,
            category=self.category if self.category in CATEGORIES
            else CATEGORY_FALLBACK,
            license_id=self.license_id,
            template=self.template if self.template in TEMPLATES
            else 'auto',
            age_band=_normalize_spaces(self.age_band) or 'all',
            learner_goal=_normalize_spaces(self.learner_goal),
            code_size=self.code_size if self.code_size in CODE_SIZES
            else 'standard',
        )

    def to_dict(self):
        return asdict(self)

    def to_prompt(self):
        goal = self.learner_goal or 'Infer a learner goal from the idea.'
        return (
            'Activity name: %s\n'
            'Learner idea: %s\n'
            'Learning category: %s\n'
            'Template preference: %s\n'
            'Age band: %s\n'
            'Learner goal: %s\n'
            'License: %s'
        ) % (
            self.name,
            self.prompt,
            self.category,
            self.template,
            self.age_band,
            goal,
            self.license_id,
        )

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise TypeError('Activity spec data must be a dictionary.')

        return cls(
            name=data.get('name', ''),
            prompt=data.get('prompt', ''),
            category=data.get('category', ''),
            license_id=data.get('license_id', 'MIT'),
            template=data.get('template', 'auto'),
            age_band=data.get('age_band', 'all'),
            learner_goal=data.get('learner_goal', ''),
            code_size=data.get('code_size', 'standard'),
        )


def name_from_prompt(prompt):
    """Build a short editable activity name from a learner prompt."""
    words = re.findall(r"[A-Za-z0-9']+", prompt)
    ignored = {
        'a', 'an', 'and', 'app', 'activity', 'build', 'create', 'for',
        'make', 'me', 'of', 'please', 'the', 'to', 'where', 'with',
    }
    useful = [word for word in words if word.lower() not in ignored]
    selected = useful[:4] or words[:4] or ['Learning', 'Activity']
    return ' '.join(word.capitalize() for word in selected)[:80]


def _normalize_spaces(value):
    if not isinstance(value, str):
        return value
    return ' '.join(value.split())
