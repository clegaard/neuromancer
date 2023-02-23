Release Notes 1.3.2

# Merged slim and psl into neuromancer

The code in neuromancer was closely tied to psl and slim.
A decision was made to integrate the packages as submodules of neuromancer.
This also solves the issue of the package names "psl" and "slim" already being taken on PyPI.

## How to import?

```python
# before
import psl
import slim

# now
import neuromancer.psl
import neuromancer.slim
```

## Authorship
Added Elliot Skomski as author, since code from slim was merged in. Otherwise, the sequence of authors remains unchanged.

# Dependencies

I ran a scan of the project using `pipreqs` to see which dependencies were actually in use.
The following packages are used by neuromancer itself:

```txt
dill
matplotlib
mlflow
mnist
networkx
numpy
pandas
plum_dispatch
pydot
pyts
scikit_learn
scipy
setuptools
six
torch
torchdiffeq
tqdm
```

The following packages by tests:

```txt
hypothesis
matplotlib
neuromancer
numpy
pytest
scipy
torch
torchdiffeq
```

differences are: `pytest,hypothesis`

The following packages by examples:

```txt
casadi
cvxpy
imageio
matplotlib
neuromancer
numpy
scikit_learn
scipy
torch
```

differences are: `casadi,cvxpy,imageio`

Finally, building the docs `sphinx` and `sphinx-rtd-theme`.
All dependencies that are not required by neuromancer are marked as optional.
Using pip these can be installed as follows:

`python3 -m pip install -e.[docs,tests,examples]`

See the `pyproject.toml` file for reference.

``` toml
[project.optional-dependencies]
tests = ["pytest", "hypothesis"]
examples = ["casadi", "cvxpy", "imageio"]
docs = ["sphinx", "sphinx-rtd-theme"]
```
