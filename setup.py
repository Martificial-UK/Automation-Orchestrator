from setuptools import setup, find_packages

setup(
    name="automation-orchestrator",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "JohnEngine @ file:///c:/AI Automation/JohnEngine_v1.0_backup"
    ],
    python_requires=">=3.8",
)
