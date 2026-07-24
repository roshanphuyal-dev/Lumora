"""Prompt templates (docs/PROMPTS.md).

Each template is a named, versioned module (e.g. `teaching_explanation_v1`) exposing a
`render_user_prompt(...)` function and, where applicable, a `SYSTEM_PROMPT` constant.
Never string-concatenate prompts inline in feature code — import a template instead.
"""
