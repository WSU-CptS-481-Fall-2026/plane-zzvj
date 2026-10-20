# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from unittest.mock import patch
from plane.db.models import Module
from plane.api.serializers.module import ModuleUpdateSerializer

@pytest.mark.unit
class TestModuleOrdering:
    """Unit tests for module ordering through the public API."""
    def test_sort_order_is_writable(self):
        serializer = ModuleUpdateSerializer()

        assert "sort_order" in serializer.fields
        assert not serializer.fields["sort_order"].read_only

    @pytest.mark.parametrize("value", [0, 10000, -10000, 1500.5])
    def test_valid_sort_order(self, value):
        field = ModuleUpdateSerializer().fields["sort_order"]

        assert field.run_validation(value) == value

    @pytest.mark.parametrize("value", ["invalid", "abc", ""])
    def test_invalid_sort_order(self, value):
        field = ModuleUpdateSerializer().fields["sort_order"]

        with pytest.raises(Exception):
            field.run_validation(value)

    def test_sort_order_is_saved(self):
        from unittest.mock import patch
        from plane.db.models import Module

        module = Module(sort_order=33333)

        serializer = ModuleUpdateSerializer()

        with patch.object(module, "save") as mock_save:
            serializer.update(module, {"sort_order": 10000})

        assert module.sort_order == 10000
        mock_save.assert_called_once()