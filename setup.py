from setuptools import setup, find_packages

setup(
    name="TelegramNotesBot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pytest",
        "pytest-cov",
        "pyTelegramBotAPI",
        "pytest-mock",
        "psycopg2-binary",
    ],
)
