from setuptools import find_packages
from setuptools import setup

setup(
    name="twitter-blast",
    version="1.0.0",
    maintainer="Drizzle",
    description="Twitter Blast",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={"test": ["pytest"]},
)
