from setuptools import setup, find_packages

setup(
    name="kasa_prometheus_exporter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "prometheus_client",
        "python-kasa",
        "requests",
        "structlog",
        "fastapi",
        "uvicorn",
    ],
    entry_points={
        "console_scripts": [
            "kasa-exporter=kasa_exporter.exporter:main",
        ],
    },
)
