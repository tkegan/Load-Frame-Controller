#!/usr/bin/python3

# Import from python stanard library
import sys
from threading import Timer

# Import from python-gobject
#   on CentOS install with `sudo dnf install python36-gobject`
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk


class Application(Gtk.Application):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="edu.bucknell.TOControl", **kwargs)
        # Declare a reference to a window
        self.window = None
        self.graph_canvas = None
        self.coords = [(25.5, 38.8), (103.3, 209.9), (235.9, 132.2), (300.1, 200.5)]
        self.sample_interval = 0.1
        self.instrument_control_thread = None

        # Add command line parsing options
        #self.add_main_option("test", ord("t"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Command line test", None)


    def do_startup(self):
        '''
        Callback invoked to "run" the application; allows for setup before
        arsing the command line
        '''
        Gtk.Application.do_startup(self)

        # declare "actions" handled by application
        # actions are invoked by menus
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.show_about_window)
        self.add_action(action)

        action = Gio.SimpleAction.new("preferences", None)
        action.connect("activate", self.show_preferences_window)
        self.add_action(action)

        action = Gio.SimpleAction.new("clear", None)
        action.connect("activate", self.clear_data)
        self.add_action(action)

        action = Gio.SimpleAction.new("export", None)
        action.connect("activate", self.export_data)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        #Build menus, too late in do_activate
        builder = Gtk.Builder.new_from_file("menu.ui")
        self.set_app_menu(builder.get_object("app-menu"))


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
            self.graph_canvas = builder.get_object("graph_canvas")
            builder.connect_signals(self)

            # Connect draw signal for canvas to our draw method.
            # Does not work from Glade for some reason
            self.graph_canvas.connect("draw", self.plot_data)

        # bring the window to the front
        self.window.present()


    def on_zero_extension(self, _action):
        '''
        Callback invoked when the zero extension button is clicked
        '''
        print("Asked to zero extension")


    def on_zero_load(self, _action):
        '''
        Callback invoked when the zero load button is clicked
        '''
        print("Asked to zero load")


    def on_run_testing_apparatus(self, _action):
        '''
        Callback invoked when the run button is clicked
        '''
        print("Asked to run tester")
        self.instrument_control_thread = Timer(self.sample_interval, self.poll_instrument)


    def show_about_window(self, _action, _params):
        about_dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        about_dialog.present()


    def clear_data(self, _action, _params):
        print("Asked to clear data")


    def export_data(self, _action, _params):
        print("Asked to export data")


    def show_preferences_window(self, _action, _params):
        print("Asked to show preferences window")


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


    def on_quit(self, *args):
        '''
        Callback to exit this application
        '''
        self.quit()


    def poll_instrument(self):
        print("Asked to poll instrument")



# This is the entry point where the python interpreter starts our application
if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
