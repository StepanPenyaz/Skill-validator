# Feature Analyst Skill

A Copilot CLI skill for deep feature analysis and implementation planning in React + .NET + Angular codebases.

## Installation

Copy the `feature-analyst` folder to one of these locations:

### Personal skill (all projects):
```
~/.copilot/skills/feature-analyst/
```

### Project skill (single repo):
```
.github/skills/feature-analyst/
```

## Usage

Once installed, invoke the skill in Copilot CLI:

```
Use the /feature-analyst skill to analyze and plan: {your feature description}
```

Or simply describe a feature and the skill will be auto-invoked based on its description matching your intent.

## What It Does

1. **Decomposes** the feature into capabilities, data, interactions, and integration points
2. **Identifies** affected architectural layers (API, domain, data, React, Angular)
3. **Launches parallel explore agents** (using cheap models) to investigate each layer
4. **Synthesizes** findings into patterns, gaps, risks, and dependencies
5. **Produces** a structured implementation plan with execution order

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Main skill instructions and workflow definition |
| `investigation-patterns.md` | Concrete grep/glob patterns for each tech stack layer |

## Customization

- Edit `SKILL.md` to adjust the workflow phases or output format
- Edit `investigation-patterns.md` to add patterns for your specific libraries (e.g., MediatR, Redux Toolkit, NgRx)
- Add more companion `.md` files for domain-specific investigation patterns
