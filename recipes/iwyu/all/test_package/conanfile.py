from conan import ConanFile
from conan.tools.build import can_run

import io
import re


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            output = io.StringIO()
            self.run("include-what-you-use --version", env="conanrun", stdout=output)
            tokens = re.split('[@#]', self.tested_reference_str)
            require_version = tokens[0].split("/", 1)[1]
            stdout = output.getvalue()
            assert require_version in stdout
            self.run("iwyu_tool.py --help", env="conanrun")
