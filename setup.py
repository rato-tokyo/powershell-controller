"""PowerShell 7コントローラーのセットアップスクリプト"""

import os
from setuptools import find_packages, setup

# READMEファイルが存在する場合のみ読み込む
readme = ""
if os.path.exists("README.md"):
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

setup(
    name="powershell_controller",
    version="0.1.0",
    description="PowerShell 7 controller for MCP",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/powershell_controller",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "loguru>=0.7.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "tenacity>=8.0.0",
        "psutil>=5.9.0",
        "result>=0.13.1",
        "rich>=13.0.0",
        "beartype>=0.14.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
    ],
) 