import re
from functools import cmp_to_key

import yaml
from pathlib import Path
from subprocess import run
from argparse import ArgumentParser


# Add versions here which are not the latest
# versions of a package but we want to keep
KEEP_VERSIONS = {
    "qt": ['5.6.3', '5.15.7', '5.15.19'],
    "openssl": ['3.5.6', '3.0.5']
}

class Version:
    def __init__(self, version):
        semver_regex = re.compile(
            r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")
        match = semver_regex.match(version)
        self.version = version
        self.is_semver = match is not None
        if self.is_semver:
            self.major = int(match.group("major"))
            self.minor = int(match.group("minor"))
            self.patch = int(match.group("patch"))

    def __str__(self):
        return self.version

    def __repr__(self):
        return self.version


def compare_versions(v1: Version, v2: Version):
    if not (v1.is_semver and v2.is_semver):
        if str(v1) < str(v2):
            return -1
        elif str(v1) > str(v2):
            return 1
        return 0

    delta = v1.major - v2.major
    if delta != 0:
        return delta

    delta = v1.minor - v2.minor
    if delta != 0:
        return delta

    return v1.patch - v2.patch


def latest_config_version(config_file: Path):
    with open(config_file, "r") as fp:
        data = yaml.safe_load(fp)
        versions = sorted([Version(v) for v in data["versions"].keys()], key=cmp_to_key(compare_versions), reverse=True)
        return versions[0]


def updated_packages():
    packages = load_packages()
    updates = {}
    for recipe, _ in packages.items():
        config_file = Path("recipes") / recipe / "config.yml"
        keep_versions = KEEP_VERSIONS.get(recipe, [])
        versions = [str(latest_config_version(config_file))] + keep_versions
        updates[recipe] = {
            "versions": versions
        }
    return updates


def recipe_config(recipes):
    for recipe, data in recipes.items():
        config_file = Path("recipes") / recipe / "config.yml"
        with open(config_file, "r") as fp:
            config = yaml.safe_load(fp)
            for version in data["versions"]:
                available_versions = config["versions"]
                if version not in available_versions:
                    print(
                        f"::warning ::Version '{version}' for '{recipe}' not in available versions. It may have been removed upstream"
                    )
                    continue
                folder = config["versions"][version]["folder"]
                yield {"recipe": recipe, "version": version, "folder": folder}


def affected_recipes(changeset):
    for change in changeset.split():
        elements = Path(change).parts
        if elements[0] == "recipes":
            yield elements[1]


def load_packages() -> dict:
    with open("entos-packages.yml", "r") as fp:
        return yaml.safe_load(fp)


def main():
    parser = ArgumentParser(description="package tools for the entos conan repository")
    parser.add_argument(
        "--export", help="export all packages to the local cache", action="store_true"
    )
    parser.add_argument(
        "--build", help="build the packages affected by the given change set"
    )
    parser.add_argument(
        "--update", help="update the entos-packages.yml file with the latest versions available", action="store_true"
    )
    args = parser.parse_args()

    if args.update:
        packages = updated_packages()
        with open("entos-packages.yml", "w") as fp:
            yaml.safe_dump(packages, fp, default_style="'")
        return

    configs = list(recipe_config(load_packages()))
    if args.export:
        for config in configs:
            cmd = "conan export recipes/{recipe}/{folder} --version={version}".format(
                **config
            )
            run(cmd.split(), check=True)
        return

    if args.build:
        recipes = set(affected_recipes(args.build))
        if len(recipes) > 1:
            raise RuntimeError("PR contains a change to more than one recipe")
        if len(recipes) == 0:
            print("No changed recipes")
            return

        recipe = recipes.pop()
        recipes_to_build = [config for config in configs if config["recipe"] == recipe]
        if len(recipes_to_build) == 0:
            raise RuntimeError(
                f"updated recipe '{recipe}' is not in the entos package list"
            )

        for recipe_to_build in recipes_to_build:
            # Skip wayland's entos sysroot wrapper; other entos recipes (e.g. glfw) build from source.
            if recipe_to_build["recipe"] == "wayland" and recipe_to_build["folder"] == "entos":
                "Skipping wayland entos recipe"
                continue
            cmd = "conan create recipes/{recipe}/{folder} --version={version} --build=missing".format(
                **recipe_to_build
            )
            cmd += " --profile=default --profile=conan_profile"
            cmd += " -c tools.system.package_manager:mode=install"
            run(cmd.split(), check=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"::error ::{err}")
        exit(1)
