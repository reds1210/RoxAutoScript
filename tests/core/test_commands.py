from __future__ import annotations

import unittest

import tests._bootstrap  # noqa: F401
from roxauto.core.commands import (
    CommandRouteKind,
    CommandRouter,
    CommandRoutingError,
    InstanceCommand,
    InstanceCommandType,
)


class CommandRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = CommandRouter()

    def test_routes_tap_with_normalized_coordinates(self) -> None:
        command = InstanceCommand(
            command_type=InstanceCommandType.TAP,
            instance_id="mumu-0",
            payload={"x": 120, "y": 240},
        )

        route = self.router.route(command)

        self.assertEqual(route.kind, CommandRouteKind.INTERACTION)
        self.assertEqual(route.payload["point"], (120, 240))

    def test_routes_refresh_as_global_control(self) -> None:
        command = InstanceCommand(command_type=InstanceCommandType.REFRESH)

        route = self.router.route(command)

        self.assertEqual(route.kind, CommandRouteKind.GLOBAL_CONTROL)
        self.assertIsNone(route.instance_id)

    def test_rejects_invalid_swipe_payload(self) -> None:
        command = InstanceCommand(
            command_type=InstanceCommandType.SWIPE,
            instance_id="mumu-0",
            payload={"start": [0, 0]},
        )

        with self.assertRaises(CommandRoutingError):
            self.router.route(command)
