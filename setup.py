from setuptools import setup


with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="kick_py", 
    version="0.1",
    packages=["kick_py"],
    package_dir={"kick_py": "."},
    install_requires=requirements,
)