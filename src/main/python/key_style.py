# SPDX-License-Identifier: GPL-2.0-or-later
"""How keys are drawn (see docs/theme-flat-keys-spec.md).

FLAT_KEYS = True  : one flat rounded rectangle with an outline, legend centred (this fork's look)
FLAT_KEYS = False : upstream's keycap look (drop shadow + lighter top face)
"""

FLAT_KEYS = True

# corner radius of a flat key, in key coordinates (= pixels at drawing scale 1.0)
CORNER_RADIUS = 10

# outline width of a flat key (and of every other box in the KeRT Light theme), in pixels
OUTLINE_WIDTH = 3
