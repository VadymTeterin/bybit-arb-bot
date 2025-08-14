# Changelog

## [Step-5.4] - 2025-08-14
### Added
- New script `scripts/export_signals.py` for exporting signals to CSV.
- New test `tests/test_export_signals.py` for CSV export verification.
- Universal Windows batch file `launcher_export.cmd` for scheduled exports.
- Task Scheduler integration guide (UA/EN) in `README.md`.
- Automatic CSV file rotation with `--keep` parameter.

### Changed
- Updated `README.md` with bilingual instructions and usage examples for CSV export.
- Updated `.gitignore` to exclude CSV export files and logs.

### Notes
- Task Scheduler runs `launcher_export.cmd` hourly at HH:05 by default.
- CSV files are saved to `exports/` and logs are written to `logs/export.log`.
