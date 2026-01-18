# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to
Semantic Versioning once published.

## Overview

- changelog is being kept from version 0.3.0 and forward.

Reason: this is the first complete rendition that is ready for release.

All further changes will be changes to 0.3.0 (or the most recent version once 0.3.0 is not the most recent version).

## [Unreleased]

As of version 0.3.0, the project is still unreleased.

## [0.3.0] - 2026-01-16

### Added
- Initial release contents for Suitkaise modules.
- Initial type stub files for IDE autocompletion.
- `suitkaise` CLI entrypoint with version and module info.
- CI workflow for running the full test suite.
- README badges for quick project metadata.
- increased test coverage to 85%
  - WorstPossibleObject causes this number to be lower than it would be otherwise

- increased speed for:
  - FileIO - >2000µs --> 45µs (44x)
  - BufferedReader - >2000µs --> 85µs (23x)
  - BufferedWriter - >2000µs --> 50µs (40x)
  - FrameType - >2500µs --> 12µs (208x)




