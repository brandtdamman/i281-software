# i281 Compiler

## Overview

The i281 microprocessor was developed by Alexander Stoytchev and Kyung-Tae Kim for the CPR E 281 class at Iowa State University.  To program the microprocessor, a compiler (or rather a simple parser) was necessary for continued use.  A compiler made by the developers of i281 was written in Java and sucessfully completed the job; however, there was room for improvement.

Developed as a means to complete the Final Project portion of CPR E 281, this repository holds the source code and other related information pertaining to a redeveloped Python i281 compiler.

The project was written in Python 3.7.3.  This version of Python (or above) is required to run the compiler.

## Setting up

To install/compile the compiler source, use PyInstaller.  For development builds, it is advised to use the traditional one-folder compilation.  As for stable builds, use the one-file compilation:

* One Folder: `pyinstaller [i281 source]`
* One File:   `pyinstaller --onefile --windowed [i281 source]`

If 'PyInstaller' is not installed on your machine, you can directly run the compiler by executing the program via Python (i.e. `python3 i281compiler.py [args]`).  Additional information about PyInstaller can be found at [PyInstaller Documentation](https://pyinstaller.readthedocs.io/en/stable/operating-mode.html "PyInstaller Documentation").

## Running

Please refer to the man-page for details.

To open the man-page, run `man ./i281compiler.1` on your preferred operating system (MacOS or Linux).

## Problems

If there are any issues with the compiler, double-check your command line arguments and source code.  If problems still persist please contact the developer(s) with a description of the problem with screenshots and source code (to be compiled).

## License

The license and its details are listed in the LICENSE file, which is included in this repository.
