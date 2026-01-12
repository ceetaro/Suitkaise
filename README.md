# Suitkaise

Making things easier for developers of all skill levels to develop complex applications.

## Installation

```bash
pip install suitkaise
```

## Info

Supported Python versions: 3.11 and above

Currently, `suitkaise` is version `0.3.0`.

All files and code in this repository is licensed under the MIT License.

`suitkaise` contains the following modules:

- cerial: serialization engine

- circuit: flow control

- processing: multiprocessing/subprocesses

- skpath: path utilities

- sktime: timing utilities

## Documentation

All documentation is available for download:

```python
from suitkaise import docs

docs.download("path/where/you/want/them/to/go")

# auto send them to project root
docs.download()
```

To send them outside of your project root, use the `Permission` class:

```python
from suitkaise import docs, Permission

with Permission():
    docs.download("Users/joe/Documents")
```

You can also view more at [suitkaise.info](https://suitkaise.info).

