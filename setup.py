from setuptools import setup, find_packages

setup(
    name="local-code-interpreter-tool",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "python-dotenv",
        "pydantic",
        "aiohttp",
    ],
    python_requires=">=3.9",
)
