# AuroraView Houdini

A pure-Python Houdini host adapter and dispatcher extracted from the public
AuroraView repository with relevant history retained. Version 0.0.0.dev0 is a
local development candidate. This repository has no publication job.

## Ownership and activation

Core owns RFC0019 HostAdapter/HostRegistry/RenderBackend/BackendRegistry,
thread-dispatch contracts, Qt integration, native rendering, SDK and shared
capability policy. This package owns Houdini metadata and hdefereval scheduling.
It depends only on auroraview>=0.5.11,<0.6.0 and supports Python 3.7+.
The Houdini SDK is supplied by Houdini; importing this package never imports
hdefereval, creates widgets or registers candidates.

```python
from auroraview_houdini import HoudiniDispatcherBackend, HoudiniHostAdapter, register
register()
from auroraview import QtWebView
```

register() initializes Core builtins and replaces only known Houdini dispatcher
class/string specifications and the existing houdini host slot. Repeated calls
preserve one slot, original priority and existing cache invalidation; other
plugins and DCCs stay registered. This introduces no registry or permission layer.
Legacy class identity depends on the Core version: the pinned public source and
published 0.5.11 wheel retain bundled implementations; Core compatibility facade
acceptance is a separate gate. Both import orders must remain functional.

HoudiniHostAdapter keeps Core's Qt metadata, capability policy and default
parent_handle() -> None. It does not implement parent discovery or invent a
Houdini version API. See docs/houdini.md and docs/zh/houdini.md for retained
upstream parent, dock and Python Panel examples. These examples require actual
Houdini/Qt verification and are not certified by the unit tests.

## Verification

Use existing interpreters; all tool commands go through vx and recipes through
vx just. Set AURORAVIEW_TEST_PYTHON to an interpreter with development dependencies
and AURORAVIEW_CORE_SOURCE to the pinned public source checkout in PROVENANCE.json.

```sh
vx just check
vx just package-check
```

CI uses Python 3.7, 3.11 and 3.12 on Linux and Windows. Source tests simulate
hdefereval queues to check argument/return/error behavior and both registries.
They do not run a licensed Houdini process. Package gates bind an installed host
wheel to pinned source Core; official published-Core wheel checks are a distinct
local gate with native module hashes and no source injection.

Before publication, verify licensed Houdini owner-thread dispatch, parent/dock,
multiple views, stop/restart and late callbacks; real Qt/WebView results and
standalone same-API behavior remain Core integration gates. Neither mock tests
nor prior private native wheels establish these guarantees for a public release.

## History

PROVENANCE.json binds the exact public main commit/tree, ten filtered commits,
source paths and source hashes. migration/commit-map.txt maps original commits to
rewritten history; zero entries are pruned commits. The filter includes LICENSE,
the old monolithic dispatcher predecessor, the selected backend, shared host
source and Houdini documentation. The current host module is narrowed to Houdini;
shared historical files contain other hosts and are retained for attribution.
Core tags, issue numbers, credentials and private task evidence are not copied.
The extraction script reproduces the path filter from a complete public clone.

Public history, issues and releases remain at
https://github.com/try-auroraview/auroraview.
