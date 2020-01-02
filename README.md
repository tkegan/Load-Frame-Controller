# Tinius Olsen Controller
A graphical user interface for controlling for select Tinius Olsen Load Frames with RS-232 serial interfaces.

## About
The Bucknell Universtity College of Engineering has a number of Tinius Olsen load frames with RS-232 serial interfaces. In order to support research endevours a GUI was created circa 2004-2007 using National Instruments' LabView. The version of LabView used is no longer supported and the project files are incompatible with contemporary editions of LabView. Therefore a replacement was desired. This GUI, developed in Python + Gtk3, can be deployed on low cost, small footprint hardware e.g. a Raspberry Pi 4 running Linux.

## Dependencies

- PyGObject
- pyserial

## Usage
This project is not designed to be run in a virtual environment as Gtk3 is difficult if not impossible to use in a virtual environment, also the only dependency other than Gtk is pyserial which is often installed globally anyways. Provided the dependencies are installed running the application should be as simple as:

```sh
python3 application.py
```

Please note that this software allows you to operate a compatible load frame from a GUI, but does not make any safety guarantees. The software will attempt to stop the load frame if it is in motion when closing as reasonable default but just as injuries can occur when using the interface on the load frame, injuries can happen when using this software. ALWAYS use caution and wear appropriate personal protective equipment when running any loadframe regardless of interface. 

## License
This project is licensed under the Apache 2.0 License - see the LICENSE file for details

## Author
2019 - present Tom Egan tegan@bucknell.edu

## To Do

- Accumulate data into a data structure
- Graph accumulated data
- Allow for export of data
- Catch IO errors that indicate machine has been disconnected and deal with them reasonably
- Provide as a package with appdata.xml, icon and .desktop files