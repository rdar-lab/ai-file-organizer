from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-file-organizer",
    version="0.1.0",
    author="rdar",
    author_email="",
    description="AI-powered file organizer that categorizes files using LLMs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rdar-lab/ai-file-organizer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langchain>=0.1.0",
        "langchain-openai>=0.0.2",
        "openai>=1.0.0",
        "python-magic>=0.4.27",
        "PySimpleGUI>=4.60.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "ai-file-organizer=ai_file_organizer.cli:main",
            "ai-file-organizer-gui=ai_file_organizer.gui:main",
        ],
    },
)
