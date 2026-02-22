# Contributing to Legislative Skills

Thank you for your interest in contributing to Legislative Skills! This project aims to make legislative research and civic engagement more accessible through AI-powered tools.

## Ways to Contribute

### 1. Add New Skills

We welcome new skills that help users:
- Research legislation more effectively
- Understand policy impacts
- Track legislative activity
- Engage with their representatives

### 2. Improve Existing Skills

- Enhance prompt instructions for better AI responses
- Add edge case handling
- Improve output formatting
- Fix bugs or unclear instructions

### 3. Improve Documentation

- Add usage examples
- Clarify instructions
- Fix typos
- Add translations

### 4. Report Issues

- Bug reports
- Feature requests
- Documentation gaps

## Skill File Format

Skills are markdown files with YAML frontmatter. Here's the structure:

```markdown
---
name: skill-name
description: Brief description of what the skill does (shown in skill list)
---

# skill-name

Detailed description of the skill's purpose.

## Usage
`/skill-name $ARGUMENTS`

[Explanation of arguments and options]

## What this skill does

You are a [role description] helping the user [accomplish goal].

### Step 1 — [First action]

[Detailed instructions for the AI]

### Step 2 — [Second action]

[More instructions]

### Step 3 — Present results

[Output format specification]

---

## Notes
- [Additional context]
- [Edge cases]
- [Related skills]
```

## Guidelines

### Skill Design Principles

1. **Single Purpose**: Each skill should do one thing well
2. **Clear Instructions**: Write prompts that guide the AI to consistent, helpful outputs
3. **Structured Output**: Define clear output formats (tables, sections, etc.)
4. **Error Handling**: Include instructions for handling missing data or errors
5. **User-Focused**: Design for the end user, not the AI

### Code Style

For Python tools in `tools/`:
- Follow PEP 8
- Add docstrings to functions
- Include type hints where helpful
- Handle errors gracefully
- Cache API responses to reduce quota usage

### Commit Messages

Use clear, descriptive commit messages:
- `Add skill: fiscal-impact` - New skill
- `Improve skill: explain-bill` - Enhancement
- `Fix: handle missing sponsor data` - Bug fix
- `Docs: add usage examples` - Documentation

## Submitting Changes

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b add-fiscal-impact-skill`
3. **Make your changes**
4. **Test your skill** with Claude Code
5. **Commit your changes** with clear messages
6. **Push to your fork**: `git push origin add-fiscal-impact-skill`
7. **Open a Pull Request**

### Pull Request Template

```markdown
## Description
[What does this PR add/change?]

## Type of Change
- [ ] New skill
- [ ] Skill improvement
- [ ] Bug fix
- [ ] Documentation
- [ ] Tool/infrastructure

## Testing
[How did you test this?]

## Checklist
- [ ] Skill follows the standard format
- [ ] Documentation is updated
- [ ] No sensitive data included
```

## Skill Ideas

Looking for something to work on? Here are some ideas:

### Research Skills
- `/fiscal-impact` - Analyze fiscal notes and budget impacts
- `/amendment-tracker` - Track amendments to a bill
- `/hearing-schedule` - Find upcoming committee hearings
- `/bill-history` - Detailed legislative history timeline

### Analysis Skills
- `/stakeholder-analysis` - Identify affected parties and their interests
- `/similar-bills` - Find related legislation across states
- `/partisan-analysis` - Analyze party-line voting patterns
- `/effectiveness-review` - Research similar laws and their outcomes

### Engagement Skills
- `/contact-rep` - Draft constituent communications
- `/testimony-prep` - Prepare for committee testimony
- `/action-alert` - Generate advocacy alerts

### Reporting Skills
- `/weekly-digest` - Weekly summary of tracked legislation
- `/session-summary` - End-of-session legislative recap

## Questions?

Open an issue or reach out if you have questions about contributing.

## Code of Conduct

Be respectful, constructive, and focused on making legislative information more accessible. We welcome contributors of all backgrounds and experience levels.
