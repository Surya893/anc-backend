"""
Setup configuration for ANC Platform
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="anc-platform",
    version="1.0.0",
    author="ANC Platform Team",
    author_email="support@anc-platform.com",
    description="Production-grade Active Noise Cancellation Platform with ML Classification and Emergency Detection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Surya893/anc-with-ai",
    project_urls={
        "Bug Tracker": "https://github.com/Surya893/anc-with-ai/issues",
        "Documentation": "https://github.com/Surya893/anc-with-ai#readme",
        "Source Code": "https://github.com/Surya893/anc-with-ai",
        "Changelog": "https://github.com/Surya893/anc-with-ai/blob/main/CHANGELOG.md",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Hardware",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Web Environment",
        "Framework :: Flask",
    ],
    keywords="audio anc noise-cancellation dsp machine-learning real-time embedded iot aws",
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "flake8>=6.0",
            "black>=23.0",
            "mypy>=1.0",
        ],
        "test": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "pytest-asyncio>=0.21",
        ],
        "cloud": [
            "boto3>=1.28.0",
            "awscli>=1.29.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "anc-server=api.server:main",
            "anc-web=web.app:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
