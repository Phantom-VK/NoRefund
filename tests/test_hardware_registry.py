"""Tests for the self-host hardware registry."""

from norefund.core.hardware_registry import (
    HardwareTarget,
    find_hardware,
    list_hardware,
    list_hardware_by_category,
    load_hardware,
)


def test_load_hardware_returns_dict_of_hardware_target():
    hardware = load_hardware()
    assert len(hardware) > 0
    assert all(isinstance(h, HardwareTarget) for h in hardware.values())


def test_exactly_twenty_eight_entries():
    assert len(list_hardware()) == 28


def test_all_ids_unique():
    ids = [h.id for h in list_hardware()]
    assert len(ids) == len(set(ids))


def test_all_four_categories_non_empty():
    for category in ("datacenter_gpu", "aws", "gcp", "azure", "consumer"):
        assert len(list_hardware_by_category(category)) > 0


def test_aws_p5_48xlarge_is_eight_h100s():
    hw = find_hardware("aws:p5.48xlarge")
    assert hw is not None
    assert hw.device_count == 8
    assert hw.memory_gib_per_device == 80.0


def test_every_apple_entry_is_unified_with_75_percent_fraction():
    for hw in list_hardware():
        if hw.vendor == "Apple":
            assert hw.memory_kind == "unified"
            assert hw.usable_memory_fraction == 0.75


def test_every_non_apple_entry_is_discrete():
    for hw in list_hardware():
        if hw.vendor != "Apple":
            assert hw.memory_kind == "discrete"


def test_every_usable_fraction_in_valid_range():
    for hw in list_hardware():
        assert 0 < hw.usable_memory_fraction <= 1


def test_find_hardware_missing_returns_none():
    assert find_hardware("nope:not-a-gpu") is None


def test_list_hardware_by_category_unknown_returns_empty():
    assert list_hardware_by_category("nope") == []
