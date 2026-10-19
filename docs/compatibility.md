# Compatibility and release policy

The current public API is v2.0.0.

- The unversioned `/` and `/define/{word}` routes remain compatibility aliases. New integrations should use `/api/v2`.
- Within v2, changes may add routes and optional response fields. Existing fields keep their meaning and types.
- A breaking route, field, or behavior change requires a new `/api/v3` route family. Existing versions remain available for at least one minor release after a deprecation notice, unless an upstream provider makes continued operation impossible.
- Python names exported by `app` (`DictionaryClient`, `VocabularyStore`) and their documented methods follow the same additive-within-2.x rule.
- Configuration variables are documented in the README and `.env.example`. A renamed setting is supported as an alias for one minor release and documented in the changelog.
- Optional local datasets and provider responses are outside the project's data license. Their own redistribution and attribution rules continue to apply.
- Release changes and migration notes are recorded in `CHANGELOG.md`.
