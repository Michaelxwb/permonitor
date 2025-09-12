from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="web-performance-monitor",
    version="1.1.0",
    description="基于pyinstrument的Flask应用性能监控和告警工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Jahan",
    author_email="ambition_xu@163.com",
    url="https://github.com/example/web-performance-monitor",
    packages=find_packages(),
    install_requires=[
        "pyinstrument>=4.0.0",
        "flask>=2.0.0",
        "mattermostdriver>=7.0.0",
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-mock>=3.0.0",
            "pytest-cov>=2.0.0",
            "flask-testing>=0.8.0",
        ]
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Framework :: Flask",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
    ],
)