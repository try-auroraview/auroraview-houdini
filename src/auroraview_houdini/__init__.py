# -*- coding: utf-8 -*-
"""Opt-in Houdini adapter. Importing this package never registers a backend."""

from __future__ import annotations

from .dispatcher import HoudiniDispatcherBackend
from .host import HoudiniHostAdapter

__all__ = ["HoudiniDispatcherBackend", "HoudiniHostAdapter", "register"]


def register() -> None:
    """Select this implementation in AuroraView's existing registries.

    The bundled implementation remains available through legacy imports.
    Initialize builtins before replacing their Houdini entries; otherwise the
    first discovery call would restore the bundled backend over this one.
    Repeated calls are safe. Other DCC registrations remain intact.
    """
    from auroraview.adapter import AdapterPriority, get_host_registry
    from auroraview.utils.thread_dispatcher import registry
    from auroraview.utils.thread_dispatcher.backends.houdini import (
        HoudiniDispatcherBackend as BundledHoudini,
    )

    registry.list_dispatcher_backends()
    for spec in (
        BundledHoudini,
        "auroraview.utils.thread_dispatcher.backends.houdini:HoudiniDispatcherBackend",
        "auroraview_houdini.dispatcher:HoudiniDispatcherBackend",
    ):
        while registry.unregister_dispatcher_backend(spec):
            pass
    registry.register_dispatcher_backend(
        HoudiniDispatcherBackend, priority=registry.DispatcherPriority.HOUDINI, name="Houdini"
    )
    hosts = get_host_registry()
    hosts.register(HoudiniHostAdapter, priority=AdapterPriority.HOUDINI, name="houdini")
