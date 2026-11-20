"""The catalog lists an extension only under categories it knows."""

from __future__ import annotations

import yaml
from support import BUNDLE

# categories.json of the Flow Steward extension catalog
KNOWN_CATEGORIES = {
    "ai",
    "cms",
    "crm",
    "data",
    "developer-tools",
    "documents",
    "ecommerce",
    "email",
    "finance",
    "hr",
    "inventory",
    "it",
    "marketing",
    "media",
    "messaging",
    "operations",
    "other",
    "productivity",
    "sales",
    "support",
}


def test_every_listing_category_is_known_to_the_catalog() -> None:
    manifest = yaml.safe_load((BUNDLE / "extension.yaml").read_text(encoding="utf-8"))
    categories = manifest["listing"]["categories"]
    assert categories, "listing.categories must not be empty"
    assert len(categories) == len(set(categories)), categories
    assert set(categories) <= KNOWN_CATEGORIES, sorted(set(categories) - KNOWN_CATEGORIES)
