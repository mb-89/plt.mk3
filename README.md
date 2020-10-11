# metaproject.mk3
This package provides a base framework for small, Qt based programs. 
To start building a new program based on this framework:
- fork the repo 
- modify APPINFO.jsonc and README.<i></i>md (and possibly LICENSE) to reflect the content of your program
- rename the "app" folder to the name of your program
- add features to the base framework by adding your own plugins to the app/plugins folder.

To distribute your program, create a .whl out of this repo (python setup.<i></i>py sdist bdist_wheel) 
and distribute the .whl file.

To run the program, run the app folder (python <path/to/app/folder>) or install the wheel and then run the installed package (python <name/of/your/package>)