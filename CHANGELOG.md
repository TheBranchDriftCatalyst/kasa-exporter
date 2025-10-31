# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2025-10-31

## [0.3.0] - 2025-10-29

### Added
- Comprehensive pytest test suite for TOU calculator with 86 tests
- Ruff integration for code formatting and linting
- Lefthook git hooks for automated code quality checks
- Conventional commits validation
- Release automation pipeline

## [0.1.0] - 2024-10-28

### Added
- Initial release of Kasa Exporter
- Prometheus metrics export for TP-Link Kasa devices
- Time-of-use (TOU) rate calculations for SDG&E TOU-ELEC plan
- FastAPI-based dashboard interface
- Docker Compose setup with Prometheus and Grafana
- Real-time energy monitoring and cost tracking
- Device discovery and registry system
- Grafana dashboard with power and cost visualizations

### Fixed
- Metric staleness by splitting cost and rate metrics
- Timezone support for accurate TOU calculations

[Unreleased]: https://github.com/TheBranchDriftCatalyst/kasa-exporter/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/TheBranchDriftCatalyst/kasa-exporter/releases/tag/v0.1.0
