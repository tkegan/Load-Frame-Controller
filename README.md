# Load Frame Controller
A graphical user interface for controlling for select Tinius Olsen Load Frames with RS-232 serial interfaces.

## About
The Bucknell Universtity College of Engineering has a number of Tinius Olsen load frames with RS-232 serial interfaces. In order to support research endevours a GUI was desired. This GUI, developed in Python + Gtk3, can be deployed on low cost, small footprint hardware e.g. a Raspberry Pi 4 running Linux.

## Dependencies

- Python 3.3+
	- PyGObject
	- pyserial

## Building
Load Frame Controller is build using the `meson` build system.

```sh
meson . build
cd build
ninja
```

and can be installed as typical for a `meson` project:

```sh
sudo ninja install
```

## Usage

Please note that this software allows you to operate a compatible load frame from a GUI, and while it will attempt to stop the load frame if it is in motion when closing as reasonable default; *NO* guarantee is made or implied that the load frame will be operated safely nor is a guarantee possible as supported load frames lack safety interlocks. Just as injuries can occur when using the controls on the load frame, injuries can happen when using this software. ALWAYS use caution and wear appropriate personal protective equipment when running any loadframe regardless of interface. 

## License
This project is licensed under the Apache 2.0 License - see the LICENSE file for details

## Author
2019 - present Tom Egan tom@tomegan.tech

## To Do

- Add axis to graph
- Add labels to graph
- Catch IO errors that indicate machine has been disconnected and deal with them reasonably
- Provide as a package with appdata.xml, icon and .desktop files
