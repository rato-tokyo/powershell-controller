from setuptools import setup, find_packages
import os

# READMEファイルが存在する場合のみ読み込む
if os.path.exists("README.md"):
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "PowerShell 7のセッション管理とコマンド実行を行うPythonライブラリ"

setup(
    name="powershell_controller",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "loguru>=0.7.2",
        "psutil>=5.9.8",
        "tenacity>=8.2.3",
        "pydantic>=2.6.3"
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.2",
            "pytest-mock>=3.12.0",
            "pytest-cov>=4.0.0"
        ]
    },
    python_requires=">=3.8",
    description="PowerShell 7コントローラー",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/powershell_controller",
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