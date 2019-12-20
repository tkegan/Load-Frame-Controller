#!/usr/bin/python3

# Import from python stanard library
from random import random
import sys
from threading import Timer

# Import from third party libraries
from serial import Serial
from serial.tools.list_ports import comports

# Import from OS provided libraries e.g. python-gobject
#   on CentOS install with `sudo dnf install python36-gobject`
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk


class Application(Gtk.Application):
    '''
    A GUI application for controlling select Tinius Olsen load frames

    A number of, at this time, older Tinius Olsen load frames include a
    control module with an RS232 port which can be connected to a computer
    which can then control the apparatus. This class implements a GUI for 
    controlling such machines.

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="edu.bucknell.TOControl",
            #flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs)
        self.settings = {
            "log": False,
            "log_file": "tinius_olsen.log"
        }

        # Declare a reference for the name of the serial device over which we
        # will communicate with the load frame controller 
        self.serial_device_name = None

        # Declare a reference to a window and UI elements
        self.window = None
        self.graph_canvas = None
        self.connection_select = None
        self.connect_button = None
        self.panel_switcher = None

        # Declare a reference to the list of serial devices the UI will show
        # in the combo box on the device selection page
        self.serial_connections_list_store = None

        # Declare some place holder data
        self.coords = [(25.5, 38.8), (103.3, 209.9), (235.9, 132.2), (300.1, 200.5)]
        self.sample_interval = 0.5
        self.instrument_control_thread = None

        # Add command line parsing options
        #self.add_main_option("log", ord("l"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Enable logging raw output from Load Frame", None)

    # Gtk.Application overrides
    def do_startup(self):
        '''
        Callback invoked to "run" the application; allows for setup before
        parsing the command line
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
        builder = Gtk.Builder.new_from_file("menu.ui")
        self.set_app_menu(builder.get_object("app-menu"))


    # def do_command_line(self, command_line):
    #     '''
    #     Unpack command line and adjust settings accordingly
    #     '''
    #     # Convert from GVariantDict to native python dict
    #     options = command_line.get_options_dict()
    #     options = options.end().unpack()

    #     if "log" in options:
    #         print("Command line enabled logging")

    #     self.activate
    #     return 0


    def do_activate(self):
        '''
        Callback invoked when the application is asked to become the active
        i.e. launched, switched to by task switcher etc.
        '''
        # We only allow a single window; create it if it does not exist
        if not self.window:
            builder = Gtk.Builder.new_from_file("window.glade")
            self.window = builder.get_object("window")
            self.add_window(self.window)
            self.panel_switcher = builder.get_object("panel_switcher")
            
            renderer = Gtk.CellRendererText()
            self.serial_connections_list_store = builder.get_object("serial_connections_list_store")
            self.connection_select = builder.get_object("connection_select")
            self.connection_select.pack_start(renderer, True)
            self.connection_select.add_attribute(renderer, "text", 0)
            self.connect_button = builder.get_object("connect_button")

            self.graph_canvas = builder.get_object("graph_canvas")
            self.load_field = builder.get_object("load_indicator")
            self.extension_field = builder.get_object("extension_indicator")

            builder.connect_signals(self)

            # Connect draw signal for canvas to our draw method.
            # Does not work from Glade for some reason
            self.graph_canvas.connect("draw", self.plot_data)

        self.ui_update_serial_port_list(None)

        # bring the window to the front
        self.window.present()


    def ui_zero_extension(self, _action):
        '''
        Callback invoked when the zero extension button is clicked
        '''
        print("Asked to zero extension")


    def ui_zero_load(self, _action):
        '''
        Callback invoked when the zero load button is clicked
        '''
        print("Asked to zero load")


    def ui_run_testing_apparatus(self, _action):
        '''
        Callback invoked when the run button is clicked
        '''
        if self.instrument_control_thread:
            self.instrument_control_thread.cancel()
            self.instrument_control_thread = None
        else:
            print("Asked to run tester")
            self.instrument_control_thread = Timer(self.sample_interval, self.poll_instrument)
            self.instrument_control_thread.start()


    def ui_show_about_window(self, _action, _params):
        '''
        Show a standard about window. Requires an appdata.xml file to be present
        '''
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()


    def ui_clear_data(self, _action, _params):
        print("Asked to clear data")


    def ui_export_data(self, _action, _params):
        print("Asked to export data")


    def ui_show_preferences_window(self, _action, _params):
        print("Asked to show preferences window")


    def ui_quit(self, *_args):
        '''
        Callback to exit this application
        '''
        self.quit()


    def ui_update_serial_port_list(self, *_args):
        ports = comports()

        self.serial_connections_list_store.clear()

        if 1 > len(ports):
            print("No ports found")
            self.connect_button.set_sensitive(False)
        else:
            print("{} serial ports found".format(len(ports)))
            for port in ports:
                print("{} ({})".format(port.name, port.device))
                self.serial_connections_list_store.append({port.name, port.device})
            self.connection_select.set_active(0)
            self.connect_button.set_sensitive(True)


    def ui_connect(self, *_args):
        active_iter = self.connection_select.get_active_iter()
        if active_iter:    # None if no active item
            # get all columns... not magic constants but indexes 0 and 1
            # indicating we want the value of columns 0 and 1. Ugly yes,
            # magic no.
            device = self.serial_connections_list_store.get(active_iter, 0, 1)
            self.serial_device_name = device[1]

            # should connect to device and discover device settings...

            self.panel_switcher.set_visible_child_name("control_pane")
        else:
            print("No entry")


    def plot_data(self, _wid, cr):
        '''
        Draw the graph
        '''
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(0.5)

        # connect each point to every other point
        for i in range(0,len(self.coords)-1):
            cr.move_to(self.coords[i][0], self.coords[i][1])
            cr.line_to(self.coords[i+1][0], self.coords[i+1][1]) 
            cr.stroke()


    def poll_instrument(self):
        '''
        Poll the load frame via serial connection for data
        '''
        print("Asked to poll instrument")
        load = random()
        self.load_field.set_text("{0:.4f}".format(load))
        extension = random()
        self.extension_field.set_text("{0:.4f}".format(extension))
        self.instrument_control_thread = Timer(self.sample_interval, self.poll_instrument)
        self.instrument_control_thread.start()



# This is the entry point where the python interpreter starts our application
if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
