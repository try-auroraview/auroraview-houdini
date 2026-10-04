# -*- coding: utf-8 -*-
"""Houdini metadata using the existing shared AuroraView host contract."""

from __future__ import annotations

from auroraview.adapter.hosts import DispatcherBackedHostAdapter, QtHostAdapterMixin


class HoudiniHostAdapter(QtHostAdapterMixin, DispatcherBackedHostAdapter):
    """SideFX Houdini (Qt host). SDK imports remain lazy."""

    dispatcher_spec = "auroraview_houdini.dispatcher:HoudiniDispatcherBackend"
    id = "houdini"
    display_name = "SideFX Houdini"
