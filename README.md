# RS232TiniusOlsenUI
A control UI for select Tinius Olsen Load Frames

## About
The Bucknell Universtity College of Engineering has a number of Tinius Olsen load frames with RS-232 serial interfaces. In order to support research endevours a GUI was created circa 2004-2007 using National Instruments LabView. LabView now appears to be nearing end of life so we have decided to replace the GUI with one developed in Python + Gtk3 we can deploy on low cost hardware (Raspberry Pi running Linux).

## Dependencies

- PyGObject
- pyserial

## Usage
This project is not designed to be run in a virtual environment as Gtk3 is difficult if not impossible to use in a virtual environment, also the only dependency other than Gtk is pyserial which is often installed globally anyways. Provided the dependencies are installed running the application should be as simple as:

```sh
python3 application.py
```

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