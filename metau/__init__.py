# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2013 <Kyle Francis> <guitarman_usa@yahoo.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import optparse, os
import gettext

from gettext import gettext as _
gettext.textdomain('metau')

from gi.repository import Gtk, Gdk, GObject # pylint: disable=E0611

from metau import MetauWindow

from metau_lib import set_up_logging, get_version

def parse_options():
    """Support for command line options"""
    parser = optparse.OptionParser(version="%%prog %s" % get_version())
    parser.add_option(
        "-v", "--verbose", action="count", dest="verbose",
        help=_("Show debug messages (-vv debugs metau_lib also)"))
    (options, args) = parser.parse_args()

    set_up_logging(options)

def main():
    'constructor for your class instances'
    parse_options()

    #initialize threads
    GObject.threads_init()
    Gdk.threads_init()

    # Run the application.    
    window = MetauWindow.MetauWindow()
    window.show()
    Gdk.threads_enter()
    Gtk.main()
    Gdk.threads_leave()
    # Delete our temporary cover art files extracted from atoms
    for filename in window.temp_coverart:
        print "Removing temporary coverart file: ",window.temp_coverart[filename][0]
        os.remove(window.temp_coverart[filename][0])
