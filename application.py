#!/usr/bin/python3

#####################################################################
# Copyright 2020 Tom Egan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#####################################################################

# Import from python stanard library
import csv
from random import random
import sys
from threading import Condition, Lock, Thread
from time import monotonic, sleep

# Import from third party libraries
from serial import Serial
from serial.tools.list_ports import comports

# Import from OS provided libraries e.g. python-gobject
#   on CentOS install with `sudo dnf install python36-gobject`
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk

# Import from our bundled instrument control library
from tiniusolsen import TiniusOlsen1000Series, TiniusOlsenH5KSeries


class Application(Gtk.Application):
    '''
    A GUI application for controlling select load frames

    A number of older Tinius Olsen load frames include a control module
    with an RS232 port which can be connected to a computer which can then
    control the apparatus. This class implements a GUI for controlling such
    machines.

    A note on method names... The do_* methods are overrides of methods
    inherited from Gtk.Application, the ui_* methods are ui callbacks set by
    Glade in window.glade or bound to Gio.Action instances in do_startup()
    and invoked by a menu item activation. 
    
    License
    --------
    Apache 2.0 License (See Also LICENSE file)
    
    Author
    --------
    Tom Egan <tegan@bucknell.edu> for Bucknell University 
    '''

    # the minimum time to delay between consecutive polls of instrument
    # ideally 0 would be a safe value but in priciple we need a bit more
    # time to account for processing overhead. This implies a maximum
    # sampling frequency of 1/minimal_delay e.g. 100 Hz => 0.01
    minimal_delay = 0.005

    # Dictionary of supported models. The keys are used in the UI to populate
    # the model selection combobox. The values must be concrete implementations
    # of tiniusolsen.TiniusOlsen
    loadframe_models = {
        "Tinius Olsen H5K Series": TiniusOlsenH5KSeries,
        "Tinius Olsen 1000 Series": TiniusOlsen1000Series
    }


    def __init__(self, *args, **kwargs):
        '''
        Override GTK.Application method used to declare ivars.
        '''
        super().__init__(*args, application_id="edu.bucknell.TOControl",
            #flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs)

        # declare a reference to the apparatus
        self.machine = None
        self.range = 0

        # declare a reference to the thread we will use to poll the machine
        self.instrument_control_thread = None

        # Declare a reference to a window and UI elements
        self.window = None
        self.statusbar = None
        self.graph_canvas = None
        self.connection_select = None
        self.model_select = None
        self.connect_button = None
        self.run_button = None
        self.direction_up_radio_button = None
        self.panel_switcher = None
        self.load_field = None
        self.extension_field = None
        self.run_rate = None

        # Declare a reference to the list of serial devices the UI will show
        # in the combo box on the device selection page
        self.serial_connections_list_store = None

        # Declare some place holder data
        self.coords = [(25.5, 38.8), (103.3, 209.9), (235.9, 132.2), (300.1, 200.5)]

        # Declare a list to hold run data and a lock to control multi threaded access to it
        self.run_data = []
        self.__run_data_lock = Lock()

        # Declare a boolean to track if we should accumulate data
        self.__collecting_data = False

        # Set a sane default: 1 Hz
        self.polling_interval = 1 # sampling frequency = 1 / polling interval
        self.__polling_interval_changed_condition = Condition()

        # Add command line parsing options
        #self.add_main_option("log", ord("l"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Enable logging raw output from Load Frame", None)


    def do_startup(self):
        '''
        Overrides GTK.Application method; Callback invoked to "run" the application;
        allows for setup before parsing the command line
        '''
        Gtk.Application.do_startup(self)

        # declare "actions" handled by application
        # actions are invoked by menus
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.ui_show_about_window)
        self.add_action(action)

        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.ui_show_preferences_window)
        self.add_action(action)

        action = Gio.SimpleAction.new("clear", None)
        action.connect("activate", self.ui_clear_data)
        self.add_action(action)

        action = Gio.SimpleAction.new("export", None)
        action.connect("activate", self.ui_export_data)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.ui_quit)
        self.add_action(action)

        #Build menus, too late in do_activate
        builder = Gtk.Builder.new_from_file("menu.glade")
        self.set_app_menu(builder.get_object("app-menu"))


    def do_command_line(self, command_line):
        '''
        Overrides GTK.Application method; Callback invoked to unpack command
        line arguments and adjust settings accordingly
        '''
        # Convert from GVariantDict to native python dict
        # options = command_line.get_options_dict()
        # options = options.end().unpack()

        # if "log" in options:
        #     print("Command line enabled logging")

        # self.activate
        # return 0
        pass


    def do_activate(self):
        '''
        Overrides GTK.Application method; Callback invoked when the application
        is asked to become "active" i.e. launched, switched to by task switcher etc.
        Instantiates the application window if necessary then shows it. 
        '''
        # We only allow a single window; create it if it does not exist
        if not self.window:
            builder = Gtk.Builder.new_from_file("window.glade")
            self.window = builder.get_object("window")
            self.add_window(self.window)

            # Connect other UI Element references (UIOutlets)
            self.statusbar = builder.get_object("statusbar")
            self.panel_switcher = builder.get_object("panel_switcher")
            self.graph_canvas = builder.get_object("graph_canvas")
            self.load_field = builder.get_object("load_indicator")
            self.extension_field = builder.get_object("extension_indicator")
            self.serial_connections_list_store = builder.get_object("serial_connections_list_store")
            self.connection_select = builder.get_object("connection_select")
            self.models_list_store = builder.get_object("models_list_store")
            self.model_select = builder.get_object("model_select")
            self.connect_button = builder.get_object("connect_button")
            self.run_button = builder.get_object("run_button")
            self.direction_up_radio_button = builder.get_object("direction_up_radio_button")
            
            # Pack a renderer in the connection select combobox
            renderer = Gtk.CellRendererText()
            self.connection_select.pack_start(renderer, True)
            self.connection_select.add_attribute(renderer, "text", 1)

            # Populate the models list store
            self.models_list_store.clear()
            for model_name in self.loadframe_models.keys():
                self.models_list_store.append([model_name])

            # Pack a renderer in the model select combobox
            renderer = Gtk.CellRendererText()
            self.model_select.pack_start(renderer, True)
            self.model_select.add_attribute(renderer, "text", 0)

            # Connect signals (UIActions)
            builder.connect_signals(self)

            # Connect draw signal for canvas to our draw method.
            # Does not work from Glade for some reason
            self.graph_canvas.connect("draw", self.plot_data)

            # Get a list of serial ports and populate the combobox
            self.ui_update_serial_port_list(None)

        # Bring the window to the front
        self.window.present()


    def ui_zero_extension(self, _sender):
        '''
        UI Action method; Callback invoked when the zero extension button is clicked
        '''
        if self.machine:
            self.machine.zero_extension()
        else:
            print("Unable to zero extension; No load frame connected")
            self.statusbar.push(0, "Unable to zero load; No load frame connected")


    def ui_zero_load(self, _sender):
        '''
        Callback invoked when the zero load button is clicked
        '''
        if self.machine:
            self.machine.zero_load()
        else:
            print("Unable to zero load; No load frame connected")
            self.statusbar.push(0, "Unable to zero load; No load frame connected")


    def ui_sample_rate_changed(self, sender):
        try:
            # We set limits in the sampling_rate_adjustment in the window.glade
            # UI definition so hopefully the next line doesn't bomb but it
            # could end in a div by 0 exception so handle before trying to
            # acquire the lock
            interval = 1 / float(sender.get_value())
            with self.__polling_interval_changed_condition:
                self.polling_interval = interval
                self.__polling_interval_changed_condition.notify()
        except Exception as e:
            print(e)
            self.statusbar.push(0, "Unable to set sampling rate; Invalid rate")


    def ui_run_rate_changed(self, sender):
        '''
        UI Action method; invoked when the run rate input value changes
        '''
        if self.machine:
            self.machine.set_run_rate(sender.get_value())
        else:
            print("Unable to set run rate; No load frame connected")
            self.statusbar.push(0, "Unable to set run rate; No load frame connected")


    def ui_collect_data_state_changed(self, _sender, state):
        self.__collecting_data = state


    def ui_run_testing_apparatus(self, _sender):
        '''
        Run or Stop the load frame

        Callback invoked when the run button is clicked. If button is active
        instruct load frame to run otherwise instruct load frame to stop
        '''
        if self.machine:
            if self.run_button.get_active():
                if self.direction_up_radio_button.get_active():
                    self.machine.start_moving_up()
                else:
                    self.machine.start_moving_down()
                self.run_button.set_label("Stop")
            else:
                self.machine.stop_moving()
                self.run_button.set_label("Run")
        else:
            print("Unable to run load frame; No load frame connected")
            self.statusbar.push(0, "Unable to run load frame; No load frame connected")
            self.run_button.set_active(False)


    def ui_show_about_window(self, _action, _params):
        '''
        Show a standard about window. Requires an appdata.xml file to be present
        '''
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()


    def ui_clear_data(self, *_args):
        with self.__run_data_lock:
            self.run_data = []

        # force redraw as data is dirty after releasing lock
        self.graph_canvas.queue_draw()


    def ui_export_data(self, *_args):
        '''
        Run a Save dialog and if the user provides a file name, dump the
        run data into a csv file with the specified file name
        '''
        dialog = Gtk.FileChooserDialog(title = "Export",
                                        parent = self.window,
                                        action = Gtk.FileChooserAction.SAVE)
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        dialog.set_current_name("trial.csv")

        filter_csv = Gtk.FileFilter()
        filter_csv.set_name("CSV files")
        filter_csv.add_pattern("*.csv")
        dialog.add_filter(filter_csv)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            with open(filename, 'w') as csvfile:
                with self.__run_data_lock: # wouldn't do to change data during export
                    spamwriter = csv.writer(csvfile)
                    spamwriter.writerow(("Time", "Load (N)", "Extension (mm)"))
                    for row in self.run_data:
                        spamwriter.writerow(row)
                    print("Exported data to {}".format(filename))
                    self.statusbar.push(0, "Exported data to {}".format(filename))
        # can release locks before disposing of dialog.
        dialog.destroy()


    def ui_show_preferences_window(self, _action, _params):
        print("Asked to show preferences window")


    def ui_quit(self, *_args):
        '''
        Callback to exit this application
        '''
        self.quit()


    def ui_update_serial_port_list(self, _sender):
        ports = comports()

        self.serial_connections_list_store.clear()

        if 1 > len(ports):
            print("No ports found")
            self.connect_button.set_sensitive(False)
        else:
            print("{} serial ports found".format(len(ports)))
            for port in ports:
                print("{} ({})".format(port.name, port.device))
                row = self.serial_connections_list_store.append(None)
                self.serial_connections_list_store.set_value(row, 0, port.device)
                self.serial_connections_list_store.set_value(row, 1, port.name)
            self.connection_select.set_active(0)
            self.connect_button.set_sensitive(True)


    def ui_connect(self, _sender):
        '''
        Connect to the instrument using the selected serial port
        '''
        model_list_store_iter = self.model_select.get_active_iter()
        connection_list_store_iter = self.connection_select.get_active_iter()

        # Do we have a selection?
        if model_list_store_iter is not None and connection_list_store_iter is not None:
            model_list_store = self.model_select.get_model()
            model_name = model_list_store[model_list_store_iter][0]
            if model_name not in self.loadframe_models:
                self.statusbar.push(0, "You must select the loadframe model first")
                return

            serial_device = self.serial_connections_list_store[connection_list_store_iter][:2]
            serial_device_name = serial_device[0]
            print("Connecting to {}".format(serial_device_name))
            self.statusbar.push(0, "Connecting to loadframe on {}".format(serial_device_name))

            # connect to device and discover device settings...
            try:
                self.machine = self.loadframe_models[model_name](serial_device_name)
                self.range = self.machine.get_load_cell_range()

                # show machine controls
                self.statusbar.remove_all(0)
                self.statusbar.push(0, "Connected to loadframe on {} range: {}N".format(serial_device_name, self.range))
                self.panel_switcher.set_visible_child_name("control_pane")

                # start polling instrument
                self.instrument_control_thread = Thread(target=self.__poll_instrument)
                self.instrument_control_thread.daemon = True
                self.instrument_control_thread.start()
            except:
                self.statusbar.push(0, "Unable to establish connection to load frame controller on {}".format(serial_device_name))
        else:
            print("You must select a serial port to connect to.")
            self.statusbar.push(0, "You must select a serial port to connect to.")


    def plot_data(self, canvas, cr):
        '''
        Draw the graph

        Parameters
        --------
            canvas - the GTKDrawingArea into which the cairo contex will will render
            cr - the cairo context to draw with
        '''
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(0.5)
        height = canvas.get_allocated_height() - 20
        width = canvas.get_allocated_width() - 20

        with self.__run_data_lock: # wouldn't do to change data during export
            if 1 < len(self.run_data): # plotting a single point gets weird
                # find max and min values
                initial_point = self.run_data[0]
                time_min = initial_point[0]
                time_max = self.run_data[-1][0]
                load_min = initial_point[1]
                load_max = initial_point[1]
                for row in self.run_data[1:]:
                    # We know time is monotonic so we can just look and first and last
                    # if row[0] < time_min:
                    #     time_min = row[0]
                    # if row[0] > time_max:
                    #     time_max = row[0]
                    if row[1] < load_min:
                        load_min = row[1]
                    if row[1] > load_max:
                        load_max = row[1]
                
                h_scale = width / (time_max - time_min)
                v_scale = height / (load_max - load_min)

                # drawing area is y-inverted
                top = height + 10

                cr.move_to(10, top - (initial_point[1] - load_min) * v_scale)
                for row in self.run_data[1:]:
                    cr.line_to(10 + (row[0] - time_min) * h_scale, top - (row[1] - load_min) * v_scale)
                cr.stroke()
            else:
                # no data, indicate as much
                # connect each point to every other point
                cr.move_to(self.coords[0][0], self.coords[0][1])
                for coordinate in self.coords[1:]:
                    cr.line_to(coordinate[0], coordinate[1]) 
                cr.stroke()


    def __poll_instrument(self):
        '''
        Poll the load frame via serial connection for data

        Intended to be run as a thread
        '''

        with self.__polling_interval_changed_condition:
            while True:
                # poll the machine
                now = monotonic()
                load = self.machine.read_load() * self.range
                extension = self.machine.read_extension()

                # update UI
                self.extension_field.set_text("{}".format(extension))
                self.load_field.set_text("{}".format(load))

                # if collecting data, add to data store
                if self.__collecting_data:
                    with self.__run_data_lock: # this may block, we need will need
                                            # to refresh now before calculating delay
                        self.run_data.append((now, load, extension))
                        self.graph_canvas.queue_draw()
                
                # calculate time to next poll and wait
                next_call = now + self.polling_interval
                delay = next_call - monotonic()
                if delay > self.minimal_delay:
                    self.__polling_interval_changed_condition.wait(delay)
                

# This is the entry point where the python interpreter starts our application
if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
