from app.build_service import generic_manifest_from_request
from app.catalog_service import CatalogService
from app.models import BuildRequestModel


def test_generic_manifest_strips_user_secrets():
    catalog = CatalogService().load_builtin()
    manifest = generic_manifest_from_request(
        catalog,
        BuildRequestModel(profile_id="robotics_starter", addon_bundle_ids=["sqlite"]),
        artifact_name="robotics-certified.img.xz",
    )

    assert manifest.system.hostname == "bbb-template"
    assert manifest.user.username == "student"
    assert manifest.user.password is None
    assert manifest.user.password_locked is True
    assert manifest.user.authorized_keys == []
    assert "sqlite" in manifest.bundles
