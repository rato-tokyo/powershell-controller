from setuptools import setup, find_packages
import io

# README.mdをUTF-8で読み込む
with io.open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="powershell_controller",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "loguru>=0.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
        ],
    },
    python_requires=">=3.6",
    author="Your Name",
    author_email="your.email@example.com",
    description="PowerShell 7 controller for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/powershell_controller",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 