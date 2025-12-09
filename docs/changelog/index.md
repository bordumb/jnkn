# Changelog

All notable changes to Jnkn.

## Versioning

Jnkn follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — Incompatible API changes
- **MINOR** — New functionality, backwards compatible
- **PATCH** — Bug fixes, backwards compatible

## [Unreleased]

### Added
- Python parser expansion (50+ patterns)
- Click/Typer `envvar=` detection
- django-environ support
- python-dotenv support

### Changed
- Improved confidence calculation
- Better false positive handling

### Fixed
- Multiline env var detection
- Pydantic `env_prefix` handling

---

## [0.4.0] - 2024-01-15

### Added
- Confidence calculation engine
- User suppressions system
- Match explanation command (`jnkn explain`)
- Token filtering and blocklists

### Changed
- Default confidence threshold to 0.5
- Improved stitching performance

---

## [0.3.0] - 2024-01-01

### Added
- Kubernetes manifest parsing
- dbt manifest parsing
- Incremental scanning

### Changed
- Migrated to SQLite storage
- Improved CLI output

---

## [0.2.0] - 2023-12-15

### Added
- Terraform parser
- Cross-domain stitching
- Basic blast radius calculation

---

## [0.1.0] - 2023-12-01

### Added
- Initial release
- Python env var detection
- Basic dependency graph

---

## Links

- [GitHub Releases](https://github.com/jnkn-io/jnkn/releases)
- [Migration Guides](https://github.com/jnkn-io/jnkn/blob/main/MIGRATION.md)
