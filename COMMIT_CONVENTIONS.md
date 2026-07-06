# Commit Message Conventions

## Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

## Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes
- `build`: Build system changes

## Examples

### Feature Development
```
feat(onboarding): add adaptive intake scoring model
feat(security): add threat-model checklist template
feat(ops): add incident response runbook starter
```

### Bug Fixes
```
fix(protocol): correct phase ordering in execution guide
fix(template): resolve missing placeholder in intake form
fix(security): close permission gap in access review workflow
```

### Technical Debt
```
refactor(workflow): simplify onboarding artifact generation steps
refactor(risk): consolidate risk scoring logic into one section
refactor(docs): normalize naming across all onboarding files
```

### Documentation
```
docs(scope): define greenfield vs brownfield criteria
docs(playbook): add security control mapping guidance
docs(runbook): update recovery and rollback instructions
```

### Infrastructure
```
chore(ci): add onboarding score validation step
chore(policy): enforce output path to /ai-onboarding/output
chore(env): add template variable validation for intake
```

## Good vs Bad Examples

### ✅ Good
```
feat(onboarding): implement adaptive intake with confidence tracking

- Auto-fill intake template from discovered evidence
- Ask only unresolved high-impact questions
- Add assumptions ledger with confidence labels
- Score onboarding completeness before completion

Closes #123
```

### ❌ Bad
```
fixed stuff
updated things
wip
```

## Branch Naming
- `feature/adaptive-intake`
- `fix/protocol-mismatch`
- `refactor/risk-model`
- `docs/security-playbook`

## Pull Request Titles
Follow the same convention as commits:
```
feat(onboarding): implement adaptive intake with confidence tracking
fix(security): resolve access control mapping gap
refactor(workflow): consolidate alignment and planning handoff
```
