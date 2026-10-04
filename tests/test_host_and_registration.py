"""Shared contract and opt-in registry checks; Houdini SDK is mocked."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from auroraview.adapter import EmbedMode, Feature, ThreadModel, UiFramework, get_host_registry
from auroraview.adapter.hosts import HoudiniHostAdapter as BundledHost
from auroraview.utils.thread_dispatcher import registry
from auroraview.utils.thread_dispatcher.backends.houdini import (
    HoudiniDispatcherBackend as BundledHoudini,
)
from test_dispatcher import FakeHoudini

from auroraview_houdini import HoudiniDispatcherBackend, HoudiniHostAdapter, register


class HostTests(unittest.TestCase):
    def setUp(self):
        self.sdk = FakeHoudini()
        modules = patch.dict(sys.modules, {"hdefereval": self.sdk.utils})
        modules.start()
        self.addCleanup(modules.stop)
        self.host = HoudiniHostAdapter()

    def test_metadata_matches_existing_core_contract(self):
        self.assertEqual(HoudiniHostAdapter.__name__, BundledHost.__name__)
        self.assertEqual(self.host.id, "houdini")
        self.assertEqual(self.host.display_name, "SideFX Houdini")
        self.assertEqual(self.host.ui_framework, UiFramework.QT)
        self.assertEqual(self.host.thread_model, ThreadModel.HOST_UI_THREAD)
        self.assertEqual(self.host.embed_mode, EmbedMode.NATIVE_CHILD)
        self.assertEqual(self.host.capabilities(), BundledHost().capabilities())
        self.assertTrue(self.host.probe(Feature.MAIN_THREAD_DISPATCH).is_supported)
        self.assertIsNone(self.host.parent_handle())

    def test_detection_and_dispatch_use_owned_backend(self):
        self.assertTrue(self.host.detect())
        self.assertIs(type(self.host._backend()), HoudiniDispatcherBackend)
        self.assertEqual(self.host.dispatcher_backend(), "HoudiniDispatcherBackend")
        events = []
        self.host.run_deferred(events.append, "deferred")
        self.assertEqual(events, [])
        self.sdk.pump()
        self.assertEqual(events, ["deferred"])

    def test_sdk_absence_is_not_a_detected_host(self):
        with patch.dict(sys.modules, {"hdefereval": None}):
            self.assertFalse(HoudiniHostAdapter().detect())
            self.assertIsNone(HoudiniHostAdapter().version())


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.sdk = FakeHoudini()
        modules = patch.dict(sys.modules, {"hdefereval": self.sdk.utils})
        modules.start()
        self.addCleanup(modules.stop)
        environment = patch.dict(os.environ, {"AURORAVIEW_DISPATCHER": "", "AURORAVIEW_HOST": ""})
        environment.start()
        self.addCleanup(environment.stop)
        registry.clear_dispatcher_backends()
        get_host_registry().clear()
        self.addCleanup(registry.clear_dispatcher_backends)
        self.addCleanup(get_host_registry().clear)

    def assert_owned_slot(self):
        houdini = [entry for entry in registry.list_dispatcher_backends() if entry[1] == "Houdini"]
        self.assertEqual(len(houdini), 1)
        self.assertEqual(houdini[0][0], registry.DispatcherPriority.HOUDINI)
        self.assertIs(type(registry.get_dispatcher_backend()), HoudiniDispatcherBackend)
        hosts = get_host_registry()
        self.assertEqual(hosts.names().count("houdini"), 1)
        from auroraview.adapter import AdapterPriority

        host_slot = [entry for entry in hosts.list() if entry[1] == "houdini"]
        self.assertEqual(host_slot[0][0], AdapterPriority.HOUDINI)
        self.assertIs(type(hosts.detect(env_override="houdini").value), HoudiniHostAdapter)

    def test_register_before_discovery_initializes_and_replaces_builtins(self):
        register()
        self.assert_owned_slot()
        self.assertIn("Maya", [entry[1] for entry in registry.list_dispatcher_backends()])
        self.assertIn("maya", get_host_registry().names())

    def test_register_after_cached_legacy_selection_invalidates_cache(self):
        self.assertIs(type(registry.get_dispatcher_backend()), BundledHoudini)
        self.assertIs(type(get_host_registry().detect(env_override="houdini").value), BundledHost)
        register()
        self.assert_owned_slot()

    def test_repeated_registration_has_one_canonical_slot(self):
        register()
        register()
        self.assert_owned_slot()

    def test_string_and_class_legacy_entries_are_both_removed(self):
        registry.list_dispatcher_backends()
        registry.register_dispatcher_backend(
            "auroraview.utils.thread_dispatcher.backends.houdini:HoudiniDispatcherBackend",
            priority=200,
            name="Houdini",
        )
        registry.register_dispatcher_backend(
            "auroraview_houdini.dispatcher:HoudiniDispatcherBackend",
            priority=200,
            name="Houdini",
        )
        register()
        self.assert_owned_slot()

    def test_other_plugin_and_host_slots_are_preserved(self):
        class OtherBackend(HoudiniDispatcherBackend):
            pass

        registry.list_dispatcher_backends()
        registry.register_dispatcher_backend(OtherBackend, priority=10, name="OtherPlugin")
        hosts = get_host_registry()
        hosts.register(BundledHost, priority=10, name="other-plugin")
        register()
        self.assertIn("OtherPlugin", [entry[1] for entry in registry.list_dispatcher_backends()])
        self.assertIn("other-plugin", hosts.names())


class FreshProcessTests(unittest.TestCase):
    def fresh(self, script):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_does_not_load_houdini_sdk_or_register(self):
        self.fresh(
            "import sys\n"
            "from auroraview.adapter import get_host_registry\n"
            "from auroraview.utils.thread_dispatcher import registry\n"
            "hosts = get_host_registry().names()\n"
            "before = registry.list_dispatcher_backends()\n"
            "import auroraview_houdini\n"
            "assert 'hdefereval' not in sys.modules\n"
            "assert get_host_registry().names() == hosts\n"
            "assert registry.list_dispatcher_backends() == before\n"
        )

    def test_registration_without_sdk_keeps_houdini_unavailable_and_falls_back(self):
        self.fresh(
            "import sys\n"
            "sys.modules.update({'houdini': None, 'hdefereval': None})\n"
            "from auroraview_houdini import register\n"
            "register()\n"
            "from auroraview.utils.thread_dispatcher import registry\n"
            "from auroraview.adapter import get_host_registry\n"
            "entries = registry.list_dispatcher_backends()\n"
            "houdini = [item for item in entries if item[1] == 'Houdini']\n"
            "assert len(houdini) == 1 and houdini[0][2] is False\n"
            "selection = get_host_registry().detect(env_override='houdini')\n"
            "assert selection.value.id == 'standalone' and selection.has_warnings\n"
        )

    def test_canonical_first_preserves_legacy_class_and_contract(self):
        self.fresh(
            "from auroraview_houdini import HoudiniHostAdapter as New\n"
            "from auroraview.adapter.hosts import HoudiniHostAdapter as Old\n"
            "from auroraview.adapter import HostAdapter\n"
            "assert issubclass(New, HostAdapter) and issubclass(Old, HostAdapter)\n"
            "assert New.id == Old.id == 'houdini'\n"
        )

    def test_legacy_first_preserves_legacy_class_and_contract(self):
        self.fresh(
            "from auroraview.adapter.hosts import HoudiniHostAdapter as Old\n"
            "from auroraview_houdini import HoudiniHostAdapter as New\n"
            "from auroraview.adapter import HostAdapter\n"
            "assert issubclass(New, HostAdapter) and issubclass(Old, HostAdapter)\n"
            "assert New.id == Old.id == 'houdini'\n"
        )
