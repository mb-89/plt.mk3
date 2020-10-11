import setuptools
import json
from jsmin import jsmin
import shutil

with open("README.md", "r") as fh:
    long_description = fh.read()

appinfo = json.loads(jsmin(open("APPINFO.jsonc","r").read()))

setuptools.setup(
    name=appinfo["name"],
    version=appinfo["version"],
    author=appinfo["author"],
    description=appinfo["description"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=appinfo["url"],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=appinfo["py_req"],
)

shutil.rmtree("build")
shutil.rmtree(f"{appinfo['name']}.egg-info")
