from app.bundles import resolve_packages


def test_resolve_packages_deduplicates_and_sorts():
    packages = resolve_packages(["python", "cpp"], ["cmake", "jq"])
    assert packages == sorted(packages)
    assert packages.count("cmake") == 1
    assert "python3" in packages
    assert "build-essential" in packages
    assert "jq" in packages
