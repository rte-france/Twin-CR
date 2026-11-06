# DynawoPy
**DynawoPy** is a high-level python package designed to work with [$\text{Dyna}\omega\text{o}$](https://dynawo.github.io/), RTE's hybrid C++/Modelica open source suite of simulation tools for power systems. It aims to automate common workflows

## Features
DynawoPy uses the following helper objects:

* **Test Case Wrapper**: A `Testcase` object holds relevant filepaths, parses the corresponding XML trees and provides utility functions to read in, save, or search through a test case.
* **Test Case Updater**: The `TestcaseUpdater` is responsible for modifications to the test case. It takes a `Testcase` object as an argument and is equipped with helper methods. While the updater relies on **XPath** to find relevant files on a base level, it **builds** and **caches** **topology graphs**, **element-by-attribute** and **element-by-element maps** to speed up the search process.

The test case updater currently supplies the following features:

* A high level function to **add a lack of voltage relay** to a given substation and line.
    * There are additional methods to **add a number of lack of voltage relays** by via **file definition** or **specifying substation IDs**.

## Contributors
* Sören Lohr (IEE, soeren.lohr@iee.fraunhofer.de)

## License
This project is licensed under the MPL V.2 License - see the [LICENSE](LICENSE) file for details.
