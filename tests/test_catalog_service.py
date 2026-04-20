from app.catalog_service import CatalogService


def test_builtin_catalog_loads_certified_profiles():
    catalog = CatalogService().load_builtin()

    assert catalog.catalog_version
    assert len(catalog.profiles) >= 3
    assert all(profile.artifact_id for profile in catalog.profiles)
    assert any(bundle.id == "python" for bundle in catalog.bundles)
