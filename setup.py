from setuptools import setup, find_packages

setup(
    name="file_monitor",
    version="1.1.0",
    description="Dynatrace OneAgent Extension 2.0 — File Monitor",
    author="Your Company Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "dt-extensions-sdk>=1.0.0",
    ],
    extras_require={
        # Needed only for local dev mode, where the SDK parses extension/extension.yaml
        "dev": ["pyyaml"],
    },
)
