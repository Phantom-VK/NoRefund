"""WCAG AA contrast-ratio checks for color combos GUI_REVIEW.md flagged as
failing (< 4.5:1 for text): the primary-button label, and every provider
badge's text-on-tint. Uses the same blend() math the app itself uses to
build these colors, so a color-token change that breaks contrast again
fails a test instead of only being caught by eye."""

from __future__ import annotations

from norefund.gui.formatting import _hex_to_rgb, blend
from norefund.gui.theme import COLORS, PROVIDER_COLORS

_AA_TEXT_MIN = 4.5


def _luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)

    def linear(channel: int) -> float:
        c = channel / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    lum_a, lum_b = _luminance(hex_a), _luminance(hex_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def test_primary_button_label_clears_aa_in_both_modes():
    primary = COLORS["primary"]
    primary_fg = COLORS["primary_fg"]
    for light_or_dark in (0, 1):
        ratio = _contrast_ratio(primary[light_or_dark], primary_fg[light_or_dark])
        assert ratio >= _AA_TEXT_MIN, (light_or_dark, ratio)


def test_provider_badges_clear_aa_in_both_modes():
    # Mirrors ProviderBadge's own construction: a light-alpha blend for the
    # background, blended toward black (light mode) / white (dark mode) by
    # the same fraction for the text.
    text_blend = 0.4
    bg_alpha = (0.13, 0.18)
    card = COLORS["card"]

    for provider, accent in PROVIDER_COLORS.items():
        for mode in (0, 1):
            bg = blend(accent, card[mode], bg_alpha[mode])
            text = blend("#000000" if mode == 0 else "#ffffff", accent, text_blend)
            ratio = _contrast_ratio(text, bg)
            assert ratio >= _AA_TEXT_MIN, (provider, mode, ratio)
