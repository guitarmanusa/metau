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

import gettext
from gettext import gettext as _
gettext.textdomain('metau')

from os.path import expanduser

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject # pylint: disable=E0611
from quickly.widgets.text_editor import TextEditor
import logging
logger = logging.getLogger('metau')

import subprocess, re, urllib2, pango, xml.dom.minidom, shlex, sys #for threaded writeout function
from urllib import urlretrieve, quote_plus
from threading import Thread

from metau.MetaData import MetaData #my custom Metadata class
from metau.search_result import search_result #my custom search_result class
from metau_lib import Window
from metau.AboutMetauDialog import AboutMetauDialog
from metau.PreferencesMetauDialog import PreferencesMetauDialog

(TARGET_ENTRY_TEXT, TARGET_ENTRY_PIXBUF) = range(2)

#GLOBALS
# self.liststore_queue
# self.liststore_chapters
# self.current_iter
# self.treeselection
# self.array_of_metadata [str filename]
# self.loaded_image
# self.image_coverart
# self.focus

#METHODS
# add_to_queue_from_button(widget)
# load_draged_files(widget, context, x, y, data, info, time)
# add_filename_to_queue(filename)
# remove_from_queue(widget)
# search_for_data(widget)
# refresh_chapter_all(widget)
# refresh_chapter_durations(widget)
# add_chapter(widget)
# remove_chapter(widget)
# limit_textview_length(widget)
# got_data_cb(widget, context, x, y, data, info, time)
# load_image_from_file(filename)
# entry_focus(widget, event)
# checkbutton_toggled(widget)
# toggle_editable(widget, widget_basename)
# cut_text(widget, data)
# paste_text(widget, data)
# copy_text(widget, data)
# finish_initializing
# cell_edited(self, w, row, new_text, model, column)
# change_selection(widget)
# multi_edit(widget)
# clear_window()
# clear_text(widget, entrytext_widget_basename)
# clear_checkbutton(widget, checkbutton_widget_basename)
# update_entry_widget(basename, text, checkbutton)
# update_window(Metadata_array_key)
# checkbutton_draw(is_locked, widget_name)
# save_chapter_info(widget)
# move_chapter_up(widget)
# move_chapter_down(widget)
# set_progress_bar_percent_as_int(model, row, percent_as_int)
# write_out(command_line, model, row)
# writeout_in_thread(command_line, model, row)
# writeout()
# prefill_notebook(widget)
# show_large_image(widget, event)

class MetauWindow(Window):
    __gtype_name__ = "MetauWindow"

    #############################################################
    ## Callback function for (+)Add button on main window      ##
    #############################################################
    def add_to_queue_from_button(self, widget):
        dialog = Gtk.FileChooserDialog("Open..", None, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CLOSE, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        filter = Gtk.FileFilter()
        filter.set_name("Movies")
        filter.add_mime_type("video/mp4")
        filter.add_pattern("*.mp4")
        filter.add_pattern("*.m4v")
        filter.add_pattern("*.mov")
        dialog.add_filter(filter)
        filter = Gtk.FileFilter()
        filter.set_name("Music")
        filter.add_mime_type("audio/mpeg")
        filter.add_pattern("*.m4a")
        dialog.add_filter(filter)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filenames = dialog.get_filenames()
            for index in range(len(filenames)):
                self.add_filename_to_queue(filenames[index])
        elif response == Gtk.ResponseType.CLOSE:
            print 'Closed, no files selected'
        dialog.destroy()

    #####################################################################
    ## Callback function to load drag and drop files into the treeview ##
    #####################################################################
    def load_draged_files(self, widget, context, x, y, data, info, time):
        uri_list = data.get_uris()
        for filename in uri_list:
            filename = urllib2.unquote(filename)
            if re.search("^file:///.*mov|mp4|m4v|m4a|m4b$",filename):
                filename = re.sub("^file://","",filename)
                self.add_filename_to_queue(filename)

    #####################################################################
    ## Helper function to add an individual file to the treeview queue ##
    #####################################################################
    def add_filename_to_queue(self, filename):
        # Don't let the same file be added to the queue twice
        if filename in self.array_of_metadata:
            pass
        else:
            self.liststore_queue.append([filename,0])
            temp_iter = self.liststore_queue.get_iter_first()
            while self.liststore_queue.iter_next(temp_iter) != None:
                temp_iter = self.liststore_queue.iter_next(temp_iter)
            if self.current_iter == None:
                self.current_iter = temp_iter
            self.treeselection.unselect_all()
            self.array_of_metadata [filename]=MetaData(self.escape_for_bash(filename))
            if not filename in self.temp_coverart and self.array_of_metadata[filename].properties.has_key("coverArt"):
                self.temp_coverart [filename]=[self.array_of_metadata[filename].properties["coverArt"][0]]
            #Triggers "changed" signal which calls update_window()
            self.treeselection.select_iter(temp_iter)

    ########################################################################
    ## Callback function to remove selected files from the treeview queue ##
    ########################################################################
    def remove_from_queue(self, widget):
        model, rows = self.treeselection.get_selected_rows()
        if len(rows) != 0:
            for path in reversed(rows):
                iter_row_to_delete = self.liststore_queue.get_iter(path)
                filename = self.liststore_queue.get_value(iter_row_to_delete,0)
                if self.array_of_metadata.has_key(filename):
                    del self.array_of_metadata[filename]
                #if iter is not on the topmost row (row 0), or there are two or more items in queue
                if self.liststore_queue.get_value(iter_row_to_delete,0) != self.liststore_queue.get_value(self.liststore_queue.get_iter_first(),0) or self.liststore_queue.iter_next(self.liststore_queue.get_iter_first()) != None:
                    if not self.liststore_queue.remove(iter_row_to_delete):
                        self.current_iter = self.liststore_queue.get_iter_first()
                        while self.liststore_queue.iter_next(self.current_iter) != None:
                            self.current_iter = self.liststore_queue.iter_next(self.current_iter)
                    elif not self.liststore_queue.iter_is_valid(iter_row_to_delete):
                        self.current_iter = self.liststore_queue.get_iter_first()
                    else:
                        self.current_iter = iter_row_to_delete
                    self.loaded_image = None
                    self.treeselection.select_iter(self.current_iter)
                else:
                    self.loaded_image = None
                    self.current_iter = None
                    self.clear_window()
                    self.liststore_queue.remove(iter_row_to_delete)
                
    ########################################################################
    ## Callback function to lookup metadata on the web via the search box ##
    ########################################################################
    def search_for_data(self, widget):
        self.updating_window = True
        #TODO implement imdb lookups
        search_urls = []

        #items from window
        title_entry = ""
        season_entry = ""
        episodenum_entry = ""
        showname_entry = ""
        videoKind = ""

        #items regex'ed from search_text entry
        episode = 0
        season = 0
        show_name = ""
        episode_name = ""

        num_chapters = 0
        base_search_url = "http://www.tagchimp.com/ape/search.php?token=3902000755054510AA3AFA&type=search&limit=20&locked=false"

        #Do some regex on the search text so that "Seinfeld 3x01" or "Seinfeld S2E09 Episode Name" will be useful
        text = self.builder.get_object("entry_searchtext").get_text()

        match = re.search(r"S([0-9]*)E([0-9]*)",text)

        if match:
            season = int(match.groups(1)[0])
            episode = int(match.groups(1)[1])
            keywords = re.split("S[0-9]*E[0-9]*", text)
            if keywords[0]:
                show_name = keywords[0].rstrip()
            if keywords[1]:
                episode_name = keywords[1].lstrip()
        else:
            match = re.search(r"([0-9]*)x([0-9]*)",text)
            if match:
                season = int(match.groups(1)[0])
                episode = int(match.groups(1)[1])
                keywords = re.split("[0-9]*X[0-9]*", text)
                if keywords[0]:
                    show_name = keywords[0].rstrip()
                if keywords[1]:
                    episode_name = keywords[1].lstrip()

        model,rows = self.treeselection.get_selected_rows()

        if len(rows) == 1:
            self.builder.get_object("liststore_searchresults").clear()
            filename = model.get_value(model.get_iter(rows[0]),0)
            metadata_class = self.array_of_metadata[filename]

            if hasattr(metadata_class,"chapter_info") and len(metadata_class.chapter_info) > 1:
                num_chapters = len(metadata_class.chapter_info)

            if metadata_class.properties.has_key("stik") and metadata_class.properties["stik"][0] == "TV Show":
                if metadata_class.properties.has_key("tvsh") and metadata_class.properties["tvsh"][0] != "":
                    showname_entry = metadata_class.properties["tvsh"][0]
                if metadata_class.properties.has_key("tvsn") and metadata_class.properties["tvsn"][0] != "":
                    season_entry = metadata_class.properties["tvsn"][0]
                if metadata_class.properties.has_key("tves") and metadata_class.properties["tves"][0] != "":
                    episodenum_entry = metadata_class.properties["tves"][0]
            elif metadata_class.properties.has_key("stik") and metadata_class.properties["stik"][0] == "Movies":
                videoKind = "Movie"

            #generate search queries
            extended_url = ""
            
            extended_url = base_search_url + "&title=" + text
            if videoKind == "Movie":
                extended_url += "&videoKind=Movie&totalChapters="
                if num_chapters > 0:
                    extended_url += str(num_chapters)
                else:
                    extended_url += "X"
            search_urls.append(quote_plus(extended_url, "/:&?="))

            extended_url = base_search_url + "&title=" + text + "&totalChapters="
            if num_chapters > 0:
                extended_url += str(num_chapters)
            else:
                extended_url += "X"
            search_urls.append(quote_plus(extended_url, "/:&?="))

            extended_url = base_search_url
            if episode_name != "":
                extended_url += "&title=" + episode_name
                if num_chapters > 0:
                    extended_url += "&totalChapters=" + str(num_chapters)
                else:
                    extended_url += "&totalChapters=X"
                search_urls.append(quote_plus(extended_url, "/:&?="))

                extended_url = base_search_url + "&title=" + episode_name + "&season=" + str(season) + "&episode=" + str(episode)
                search_urls.append(quote_plus(extended_url, "/:&?="))

            extended_url = base_search_url
            if show_name != "":
                extended_url += "&show=" + show_name + "&season=" + str(season) + "&episode=" + str(episode)
                search_urls.append(quote_plus(extended_url, "/:&?="))

            extended_url = base_search_url
            if title_entry != "":
                extended_url += "&title=" + title_entry
                if num_chapters > 0:
                    extended_url += "&totalChapters=" + str(num_chapters)
                if videoKind == "Movie":
                    extended_url += "&videoKind=Movie"
                    search_urls.append(quote_plus(extended_url, "/:&?="))
                else:
                    extended_url += "&season=" + season_entry + "&episode=" + episodenum_entry + "&show=" + showname_entry
                    search_urls.append(quote_plus(extended_url, "/:&?="))
            else:
                extended_url += "&season=" + season_entry + "&episode=" + episodenum_entry + "&show=" + showname_entry
                search_urls.append(quote_plus(extended_url, "/:&?="))
                

            extended_url = base_search_url
            if show_name != "" and season != 0:
                extended_url += "&show=" + show_name + "&season=" + str(season)
                search_urls.append(quote_plus(extended_url, "/:&?="))
            extended_url = base_search_url
            if showname_entry != "" and season_entry != "":
                extended_url += "&show=" + showname_entry + "&season=" + season_entry
                search_urls.append(quote_plus(extended_url, "/:&?="))

        #Alert the user they did not enter enough info to conduct a basic search
        if text == "" and title_entry == "":
            if showname_entry == "" and season_entry == "":
                self.builder.get_object("label_status").set_text("No information to search with.")
        
        if len(search_urls) > 0:
            self.array_of_results = []
            results_IDs = []

            for search_url_attempt in search_urls:
                print "Search URL: " + search_url_attempt
                req = urllib2.Request(search_url_attempt)
                req.add_header('Accept', 'application/xml')
                req.add_header('User-Agent', "Magic Browser")
                req.add_header("Content-type", "application/x-www-form-urlencoded")

                try: xml_res = urllib2.urlopen(req)
                except urllib2.HTTPError as error:
                    print "Error: " + error.reason
                    self.builder.get_object("label_status").set_text("Error: " + str(error.reason[1]))
                else:
                    res_string = xml_res.read()
                    res_string = res_string.decode('utf-8', errors='ignore')
                    res_string = res_string.encode('ascii', errors='ignore')
                    results = xml.dom.minidom.parseString(res_string).getElementsByTagName('movie')

                    for result in results:
                        #filter out duplicate results
                        if not result.getElementsByTagName('tagChimpID')[0].childNodes[0].nodeValue in results_IDs:
                            results_IDs.append("tagChimp" + result.getElementsByTagName('tagChimpID')[0].childNodes[0].nodeValue)
                            #print "tagChimp" + result.getElementsByTagName('tagChimpID')[0].childNodes[0].nodeValue
                            self.array_of_results.append([search_result(result, "tagchimp"),"tagchimp"])

                        #TODO check if there's an IMDB ID number
                    #TODO if IMDB ID number in any result, run correspoding IMDB search

            pixbuf_format, width, height = GdkPixbuf.Pixbuf.get_file_info("./data/media/tagChimp_logo.png")
            pixbuf_tagchimp = GdkPixbuf.Pixbuf.new_from_file_at_scale("./data/media/tagChimp_logo.png", 46, 15, True)

            for result in self.array_of_results:
                if result[1] == "tagchimp":
                    if result[0].properties.has_key("nam"):
                        self.builder.get_object("liststore_searchresults").append([result[0].properties["nam"],pixbuf_tagchimp])
                    else:
                        self.builder.get_object("liststore_searchresults").append(["",pixbuf_tagchimp])

        self.updating_window = False

    ########################################################################
    ## Callback function to reload chapter information from file metadata ##
    ########################################################################
    def refresh_chapter_all(self, widget):
        if self.current_iter != None:
            filename = self.liststore_queue.get_value(self.current_iter,0)
            if hasattr(self.array_of_metadata[filename], 'chapter_info'):
                self.liststore_chapters.clear()
                self.array_of_metadata[filename].load_chapters_from_filename()
                for index in range(len(self.array_of_metadata[filename].chapter_info)):
                    self.liststore_chapters.append([self.array_of_metadata[filename].chapter_info[index][0], self.array_of_metadata[filename].chapter_info[index][1], self.array_of_metadata[filename].chapter_info[index][2]])

    ########################################################################
    ## Callback function to reload chapter durations from file metadata   ##
    ########################################################################
    def refresh_chapter_durations(self, widget):
        if self.current_iter != None:
            filename = self.liststore_queue.get_value(self.current_iter,0)
            if hasattr(self.array_of_metadata[filename], 'chapter_info'):
                self.array_of_metadata[filename].array_of_chapters_in_file()
                #if the same number of chapters written into the file as are in the liststore_chapters model
                if self.array_of_metadata[filename].temp_number_chapters == self.liststore_chapters.iter_n_children(None):
                    for row_path_int in range(self.liststore_chapters.iter_n_children(None)):
                        #update the duration column with the duration value in the temp_info array
                        self.liststore_chapters.set_value(self.liststore_chapters.get_iter(str(row_path_int)),2,self.array_of_metadata[filename].temp_info[row_path_int][2])
                else:
                    #Show an error and a solution
                    dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "ERROR: Chapter Info Length")
                    dialog.format_secondary_text("The number of user generated chapters does not match the number of chapters in the file.  Please refresh all chapter information from file to correct this error.")
                    dialog.run()
                    dialog.destroy()
                    print "ERROR dialog closed"

    #####################################################################
    ## Callback function to add a new chapter to the treeview          ##
    #####################################################################
    def add_chapter(self, widget):
        model_chapters, rows_chapters = self.treeview_chapters_selection.get_selected_rows()
        model_queue, rows_queue = self.treeselection.get_selected_rows()
        if len(rows_queue) == 1:# and len(rows_chapters) == 1:
            if len(rows_chapters) == 0:
                self.liststore_chapters.append(None)
                temp_iter = self.liststore_chapters.get_iter_from_string("0")
            else:
                temp_iter = self.liststore_chapters.insert_after(model_chapters.get_iter(rows_chapters[0]))
            self.treeview_chapters_selection.unselect_all()
            self.treeview_chapters_selection.select_iter(temp_iter)
            for row_path_int in range(self.liststore_chapters.iter_n_children(None)):
                temp_iter = self.liststore_chapters.get_iter_from_string(str(row_path_int))
                self.liststore_chapters.set_value(temp_iter,0,str(row_path_int+1))

    #########################################################################
    ## Callback function to remove the selected chapters from the treeview ##
    #########################################################################
    def remove_chapter(self, widget):
        model, rows = self.treeview_chapters_selection.get_selected_rows()
        if len(rows) != 0:
            for path in reversed(rows):
                iter_row_to_delete = self.liststore_chapters.get_iter(path)
                self.liststore_chapters.remove(iter_row_to_delete)
            #FIXED when you delete the first empty row inserted, the selection disappears
            self.treeview_chapters_selection.unselect_all()
            if self.liststore_chapters.iter_is_valid(iter_row_to_delete):
                self.treeview_chapters_selection.select_iter(iter_row_to_delete)
            else:
                num_nodes = self.liststore_chapters.iter_n_children(None) - 1
                if num_nodes != -1:
                    self.treeview_chapters_selection.select_iter(self.liststore_chapters.get_iter_from_string(str(num_nodes)))
            for row_path_int in range(self.liststore_chapters.iter_n_children(None)):
                temp_iter = self.liststore_chapters.get_iter_from_string(str(row_path_int))
                self.liststore_chapters.set_value(temp_iter,0,str(row_path_int+1))

    ####################################################################################
    ## Callback function to limit the numbers of chars in the shortdesc editor to 255 ##
    ####################################################################################
    def limit_textview_length(self, widget):
        length = self.textbuffer.get_char_count()
        charsleft = 255 - length
        if length > 255:
            charsleft = 0
            start = self.textbuffer.get_iter_at_offset(255)
            end = self.textbuffer.get_end_iter()
            self.textbuffer.delete(start, end)
        if charsleft == 255:
            self.label_shortdesc.set_text("Short Description (255 characters max)")
        else:
            self.label_shortdesc.set_text("Short Description (" + str(charsleft) + " characters left)")
        model,rows = self.treeselection.get_selected_rows()
        if len(rows) == 1 and self.focus == widget:
            filename = model.get_value(model.get_iter(rows[0]),0)
            text = self.textbuffer.get_text(self.textbuffer.get_start_iter(),self.textbuffer.get_end_iter(),False)
            #print "Writing out..."
            self.array_of_metadata[filename].properties["desc"]=[text,self.builder.get_object("checkbutton_shortdesc").get_active()]

    #####################################################################
    ## Callback function to load a dropped image into the icon image   ##
    #####################################################################
    def motion_cb(self, widget, context, x, y, time):
        Gdk.drag_status(context, Gdk.DragAction.COPY, time)
        return True

    #####################################################################
    ## Callback function to load a dropped image into the icon image   ##
    #####################################################################
    def drop_cb(self, widget, context, x, y, time):
        print "list targets", 
        for t in context.list_targets():
            print "target: ", str(t)
        print "time: " , time
        print "context: ", context
        print x, y
        Gdk.DragContext.drop_reply(context,True,time)


    #####################################################################
    ## Callback function to load a dropped image into the icon image   ##
    #####################################################################
    def got_data_cb(self, widget, context, x, y, data, info, time):
        #print data.get_pixbuf()
        #pixbuf = data.get_pixbuf()
        #pixbuf_format, width, height = pixbuf.
        #self.image_coverart.set_from_pixbuf(pixbuf)
        #print "Context: ", context
        #print "Data: ", data
        #TODO download link and load it
        #TODO figure out how mozilla sends images dragged from a webpage
        #for targets in context.list_targets():
        #    print "type:", str(targets)
        print "pixbuf? ", data.get_pixbuf()
        uri_list = data.get_uris()
        #print len(uri_list), uri_list
        uri_list[0] = urllib2.unquote(uri_list[0])
        #print uri_list[0], re.search("^file://", uri_list[0])
        if re.search("^file:///", uri_list[0]):
            uri_list[0] = re.sub("^file://","", uri_list[0])
            self.load_image_from_file(uri_list[0])
        elif re.search("^http://", uri_list[0]):
            print "It's a link, let's download it."
        elif re.search(".jpg$", uri_list[0]):
            print uri_list[0]
        #TODO check if multi-edit and save coverart if so
        Gtk.drag_finish(context, False, False, time)
        Gtk.drop_finish(context, True, time)

    ###################################################################################
    ## load_image_from_file(filename) if not locked, load filename into the coverArt ##
    ## widget and save filename info into metadata_class                             ##
    ###################################################################################
    def load_image_from_file(self, filename):
        print "Testing ", filename
        if not self.builder.get_object("checkbutton_coverArt").get_active():
            pixbuf_format, width, height = GdkPixbuf.Pixbuf.get_file_info(filename)
            self.width = width
            self.height = height
            if width > height:
                height = -1
                width = 125
            else:
                width = -1
                height = 125
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filename, width, height, True)
            self.image_coverart.set_from_pixbuf(pixbuf)
            self.label_iconsize.set_text("Icon Size (" + str(self.width) + "x" + str(self.height) + ")")
            self.loaded_image = filename
            model,rows = self.treeselection.get_selected_rows()
            for row in rows:
                if self.prefilling or self.updating_window:
                    self.array_of_metadata[model.get_value(model.get_iter(row),0)].properties["coverArt"]=[filename, self.array_of_metadata[model.get_value(model.get_iter(row),0)].properties["coverArt"][1]]
                else:
                    self.array_of_metadata[model.get_value(model.get_iter(row),0)].properties["coverArt"]=[filename,self.builder.get_object("checkbutton_coverArt").get_active()]

    ##################################################################################
    ## Create a function that keeps track of which Entry/Editor has the focus       ##
    ##################################################################################
    def entry_focus(self, widget, event):
        self.focus = widget
        if widget.get_name() == "quickly+widgets+text_editor+TextEditor":
            self.focus = self.focus.get_buffer()
        elif self.builder.get_name(widget) == "entry_title":
            self.builder.get_object("entry_searchtext").set_text(widget.get_text())

    #########################################################################################
    ## A function that will make the widget(s) corresponding to a checkbutton not editable ##
    #########################################################################################
    def checkbutton_toggled(self, widget):
        checkbutton = self.builder.get_name(widget)
        print checkbutton
        basename = checkbutton.split("_")[1]
        #Set not editable the special cases
        # (done)trackinfo, (done)diskinfo, (done)shortdesc, (done)longdesc
        # coverArt is handled in load_image_from_file
        # advisory, ispodcast, gapless, compilation, stik, HD, contentRating handled in multi_edit 
        if basename == "shortdesc":
            if widget.get_active():
                self.editor_shortdesc.set_editable(False)
            else:
                self.editor_shortdesc.set_editable(True)
        elif basename == "longdesc":
            if widget.get_active():
                self.editor_longdesc.set_editable(False)
            else:
                self.editor_longdesc.set_editable(True)
        elif basename == "trackinfo":
            self.toggle_editable(widget, "tracknum")
            self.toggle_editable(widget, "trackdenom")
        elif basename == "diskinfo":
            self.toggle_editable(widget, "disknum")
            self.toggle_editable(widget, "diskdenom")
        #Comboboxtext widgets freeze functionality handled in self.multi_edit, not saved if checkbutton active
        #coverArt image widget not editable if checkbutton is selected (in self.load_image_from_file)
        elif basename == "coverArt" or self.comboboxes.has_key(basename):
            pass
        else:
            self.toggle_editable(widget, basename)
        if not self.updating_window:
            model, rows = self.treeselection.get_selected_rows()
            for row in rows:
                filename = model.get_value(model.get_iter(row),0)
                try:
                    metadata_class = self.array_of_metadata[filename]
                except KeyError:
                    pass
                else:
                    if self.reverse_entry_windows.has_key(basename):
                        #If TV show, save to tvsh atom, not ART atom
                        if basename == "artistshow" and metadata_class.properties.has_key("stik") and metadata_class.properties["stik"][0] == "TV Show":
                            metadata_class.properties["tvsh"]=[self.builder.get_object("entry_artistshow").get_text(),widget.get_active()]
                            self.builder.get_object("entry_show").set_text(self.builder.get_object("entry_artistshow").get_text())
                            if metadata_class.properties.has_key("ART"):
                                del(metadata_class.properties["ART"])
                        else:
                            metadata_class.properties[self.reverse_entry_windows[basename]]=[self.builder.get_object("entry_"+basename).get_text(),widget.get_active()]
                    elif self.comboboxes.has_key(basename) and self.builder.get_object("comboboxtext_"+basename).get_active() != -1:
                        if basename == "HD":
                            #don't change the hdvd atom from 0,1 or 2 to Non-HD, 720p, 1080p, it causes a shitstorm of errors
                            metadata_class.properties[self.comboboxes[basename]]=[self.builder.get_object("comboboxtext_"+basename).get_active(),self.builder.get_object("checkbutton_"+basename).get_active()]
                        else:
                            metadata_class.properties[self.comboboxes[basename]]=[self.builder.get_object("comboboxtext_"+basename).get_active_text(),self.builder.get_object("checkbutton_"+basename).get_active()]
                    elif basename == "shortdesc" and len(rows) == 1:
                        metadata_class.properties["desc"]=[self.textbuffer.get_text(self.textbuffer.get_start_iter(),self.textbuffer.get_end_iter(),False),self.builder.get_object("checkbutton_shortdesc").get_active()]
                    elif basename == "longdesc" and len(rows) == 1:
                        metadata_class.properties["ldes"]=[self.editor_longdesc.get_buffer().get_text(self.editor_longdesc.get_buffer().get_start_iter(),self.editor_longdesc.get_buffer().get_end_iter(),False),self.builder.get_object("checkbutton_longdesc").get_active()]
                    elif basename == "trackinfo":
                        metadata_class.properties["trkn"]=[self.builder.get_object("entry_tracknum").get_text()+" of "+ self.builder.get_object("entry_trackdenom").get_text(),self.builder.get_object("checkbutton_trackinfo").get_active()]
                    elif basename == "diskinfo":
                        metadata_class.properties["disk"]=[self.builder.get_object("entry_disknum").get_text()+" of "+ self.builder.get_object("entry_diskdenom").get_text(),self.builder.get_object("checkbutton_diskinfo").get_active()]
                    elif basename == "coverArt":
                        if metadata_class.properties.has_key("coverArt"):
                            print "diagnose 1"
                            metadata_class.properties["coverArt"]=[metadata_class.properties["coverArt"][0],self.builder.get_object("checkbutton_coverArt").get_active()]
                        else:
                            print "diagnose 2"
                            metadata_class.properties["coverArt"]=[self.loaded_image, self.builder.get_object("checkbutton_coverArt").get_active()]
                    
    ######################################################################
    ##  Helper function to checkbutton_toggled, toggles the checkbutton ##
    ######################################################################
    def toggle_editable(self, widget, basename):
        if widget.get_active():
            self.builder.get_object("entry_"+basename).set_editable(False)
        else:
            self.builder.get_object("entry_"+basename).set_editable(True)

    ######################################################
    ## Define the callback functions for the TextEditor ##
    ######################################################
    #TODO implement undo/redo stack

    ## Cut ##
    def cut_text(self, widget, data=None):
        if self.focus != self.editor_longdesc and self.focus != self.editor_shortdesc:
            bounds = self.focus.get_selection_bounds()
            if bounds:
                chars = self.focus.get_chars(*bounds)
                self.clipboard.set_text(chars,-1)
                self.focus.delete_text(bounds[0], bounds[1])
        else:
            if self.focus == self.editor_longdesc:
               self.editor_longdesc.cut()
            elif self.focus == self.editor_shortdesc:
               self.editor_shortdesc.cut()

    ## Paste ##
    def paste_text(self, widget, data=None):
        if self.focus != self.editor_longdesc and self.focus != self.editor_shortdesc:
            text = self.clipboard.wait_for_text()
            if text != None:
                bounds = self.focus.get_selection_bounds()
                if bounds:
                    self.focus.delete_text(bounds[0],bounds[1])
                    self.focus.insert_text(text, bounds[0])
                else:
                    pos = self.focus.get_position()
                    self.focus.insert_text(text,pos)
        else:
            if self.focus == self.editor_longdesc:
               self.editor_longdesc.paste()
            elif self.focus == self.editor_shortdesc:
               self.editor_shortdesc.paste()
        #TODO future version, allow paste from clipboard to image_coverart

    ## Cut ##
    def copy_text(self,widget):
        if self.focus != self.editor_longdesc and self.focus != self.editor_shortdesc:
            bounds = self.focus.get_selection_bounds()
            if bounds:
                chars = self.focus.get_chars(*bounds)
                self.clipboard.set_text(chars,-1)
        else:
            if self.focus == self.editor_longdesc:
               self.editor_longdesc.copy()
            elif self.focus == self.editor_shortdesc:
               self.editor_shortdesc.copy()

    ###########################################################################
    ## Quickly pre-generated function to finish initializing the main window ##
    ###########################################################################
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(MetauWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutMetauDialog
        self.PreferencesDialog = PreferencesMetauDialog

        # Code for other initialization actions should be added here.
        self.home = expanduser("~")

        # Grab all the UI elements that we'll need to use.
        self.toolbutton_queueadd = self.builder.get_object("toolbutton_queueadd")
        self.toolbutton_queueremove = self.builder.get_object("toolbutton_queueremove")
        self.button_search = self.builder.get_object("button_search")
        self.liststore_queue = self.builder.get_object("liststore_queue")
        self.treeview_queue = self.builder.get_object("treeview_queue")
        self.treeselection = self.treeview_queue.get_selection()
        self.treeselection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeselection.connect("changed", self.change_selection)
        self.liststore_chapters = self.builder.get_object("liststore_chapters")
        self.treeview_chapters = self.builder.get_object("treeview_chapters")
        self.treeview_chapters_selection = self.treeview_chapters.get_selection()
        self.treeview_chapters_selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.cellrenderer_filename = self.builder.get_object("cellrenderer_filename")
        self.cellrenderer_filename.set_property("ellipsize-set", True)
        self.cellrenderer_filename.set_property("ellipsize", pango.ELLIPSIZE_MIDDLE)
        self.builder.get_object("cellrenderer_title").set_property("ellipsize-set", True)
        self.builder.get_object("cellrenderer_title").set_property("ellipsize", pango.ELLIPSIZE_MIDDLE)
        self.label_shortdesc = self.builder.get_object("label_shortdesc")
        self.label_iconsize = self.builder.get_object("label_iconsize")
        self.image_coverart = self.builder.get_object("image_coverart")
        self.scrolledwindow2 = self.builder.get_object("scrolledwindow2")
        self.scrolledwindow1 = self.builder.get_object("scrolledwindow1")

        ## Setup drag and drop area for coverart. ##
        #Gtk.TargetEntry.new('text/uri-list', Gtk.TargetFlags.OTHER_APP, 5),
        self.image_coverart.drag_dest_set(0, [], 0)
        #self.image_coverart.drag_dest_set(Gtk.DestDefaults.ALL,[],Gdk.DragAction.COPY)
        #self.image_coverart.drag_dest_add_uri_targets()
        #self.image_coverart.drag_dest_add_image_targets()
        self.image_coverart.connect('drag-motion', self.motion_cb)
        self.image_coverart.connect('drag-drop', self.drop_cb)
        self.image_coverart.connect('drag-data-received', self.got_data_cb)

        ## Setup drag and drop for filenames in treeview queue
        self.treeview_queue.drag_dest_set(Gtk.DestDefaults.ALL,[],Gdk.DragAction.COPY)
        self.treeview_queue.drag_dest_add_uri_targets()
        self.treeview_queue.connect('drag-data-received', self.load_draged_files)

        ## Setup the Quickly Widget text editor Long Desc ##
        self.editor_longdesc = TextEditor()
        self.editor_longdesc.show()
        self.editor_longdesc.set_wrap_mode(Gtk.WrapMode.WORD)
        self.editor_longdesc.connect('cut-clipboard', self.cut_text)
        self.editor_longdesc.connect('paste-clipboard', self.paste_text)
        self.editor_longdesc.connect('copy-clipboard', self.copy_text)
        self.editor_longdesc.connect('focus-in-event', self.entry_focus)
        self.editor_longdesc.get_buffer().connect("changed", self.multi_edit)
        self.scrolledwindow2.add(self.editor_longdesc)

        ## Setup the Quickly Widget text editor Short Desc ##
        self.editor_shortdesc = TextEditor()
        self.editor_shortdesc.show()
        self.editor_shortdesc.set_wrap_mode(Gtk.WrapMode.WORD)
        self.editor_shortdesc.connect('cut-clipboard', self.cut_text)
        self.editor_shortdesc.connect('paste-clipboard', self.paste_text)
        self.editor_shortdesc.connect('copy-clipboard', self.copy_text)
        self.editor_shortdesc.connect('focus-in-event', self.entry_focus)
        self.textbuffer = self.editor_shortdesc.get_buffer()
        self.textbuffer.connect("changed", self.limit_textview_length)
        self.scrolledwindow1.add(self.editor_shortdesc)

        ## Make chapter info (title, duration) editable
        self.builder.get_object("cellrenderer_chapter").connect("edited", self.cell_edited, self.liststore_chapters,1)
        self.builder.get_object("cellrenderer_duration").connect("edited", self.cell_edited,self.liststore_chapters,2)        

        #TODO allow drag and drop of chapter information

        ## Create Clipboard for the app to use ##
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        ###############
        #   GLOBALS   #
        ###############
        self.prefilling = False # tell self.clear_window() not to clobber the search results treeselection
        self.clearing_window = False #tell prefill_notebook not to run if window is being cleared due to file removed from queue
        self.updating_window = False
        ## Create our dictionary of MetaData classes ##
        # key = filename: value = MetaData class
        self.array_of_metadata = {}
        self.temp_coverart = {} # A dictionary of temporary coverart images to clean up on exit
        # A dictionary to map HD markings to combotextbox numbers
        self.HD_atom_map = {"Non-HD":0, "720p":1, "1080p":2}
        # A dictionary of all the atom -> textentry objects in the main window
        self.entry_windows = {"ART":"artistshow","alb":"album","gnre":"genre","tves":"episode","cmt":"comment","cprt":"copyright","grp":"grouping","aART":"albumartist","tvnn":"TVnetwork","nam":"title","tvsn":"season","catg":"category","keyw":"keyword","too":"encodingtool","tven":"episodeID","sonm":"sortname","soar":"sortartist","soaa":"sortalbumartist","soal":"sortalbum","sosn":"sortshow","cnID":"catalogID","cast_members":"actors","directors":"director","producers":"producer","screenwriters":"screenwriter","tvsh":"show","purl":"feedURL","egid":"episodeURL","purd":"purchasedate","day":"date"}
        # A dictionary of all the textentry -> atom objects in the main window
        self.reverse_entry_windows = {"artistshow":"ART","album":"alb","genre":"gnre","episode":"tves","comment":"cmt","date":"day","copyright":"cprt","grouping":"grp","albumartist":"aART","TVnetwork":"tvnn","title":"nam","season":"tvsn","category":"catg","keyword":"keyw","encodingtool":"too","episodeID":"tven","sortname":"sonm","sortartist":"soar","sortalbumartist":"soaa","sortalbum":"soal","sortshow":"sosn","catalogID":"cnID","actors":"cast_members","director":"directors","producer":"producers","screenwriter":"screenwriters","show":"tvsh","feedURL":"purl","episodeURL":"egid","purchasedate":"purd"}
        self.current_iter = None # Keep track of the iter for the currently selected item in the queue
        self.loaded_image = None
        self.torf = {True:1,False:0}
        #self.ratings = {0:"mpaa|G|100|",1:"mpaa|PG|200|",2:"mpaa|PG-13|300|",3:"mpaa|R|400|",4:"mpaa|Unrated|600|",5:"mpaa|NC-17|500|",6:"us-tv|TV-Y7|100|",7:"us-tv|TV-Y|200|",8:"us-tv|TV-G|300|",9:"us-tv|TV-PG|400|",10:"us-tv|TV-14|400|",11:"us-tv|TV-MA|400|"}
        self.frozen_group_edit = ["title","date","purchasedate","episodeID","episode","catalogID","episodeURL","sortname"]
        self.multi_edit_entry = ["artistshow","show","feedURL","genre","album","albumartist","actors","director","producer","screenwriter","season","TVnetwork","category","keyword","copyright","grouping","encodingtool","comment","sortartist","sortalbumartist","sortalbum","sortshow"]
        self.comboboxes = {"advisory":"rtng","ispodcast":"pcst","gapless":"pgap","compilation":"cpil","stik":"stik","HD":"hdvd","contentRating":"contentRating"}

    #################################################################################
    ## When cellrenderer text changes, update the model with the user-edited text. ##
    #################################################################################
    def cell_edited(self, w, row, new_text, model, column):
        model.set_value(model.get_iter(row),column,new_text)

    #########################################################################################
    ## When treeview selection changes, update the window with the metadata for that file. ##
    #########################################################################################
    def change_selection(self, widget):
        model,treepathlist = widget.get_selected_rows()
        #TODO if multiple filenames in queue are selected, check to see if all are TV Show, Movies or a mix thereof
        #There shouldn't be a different types in the selection
        if len(treepathlist) == 1:
            self.update_window(self.liststore_queue.get_value(model.get_iter(treepathlist[0]),0))
            self.current_iter = model.get_iter(treepathlist[0])
            #Enable every option for editing during single edit mode, unless user has locked it
            for index in range(len(self.frozen_group_edit)):
                if not self.builder.get_object("checkbutton_"+self.frozen_group_edit[index]).get_active():
                    self.builder.get_object("entry_"+self.frozen_group_edit[index]).set_editable(True)
            #shortdesc, longdesc, tracknum, trackdenom
            if not self.builder.get_object("checkbutton_trackinfo").get_active():
                self.builder.get_object("entry_tracknum").set_editable(True)
            if not self.builder.get_object("checkbutton_diskinfo").get_active():
                self.builder.get_object("entry_disknum").set_editable(True)
            if not self.builder.get_object("checkbutton_shortdesc").get_active():
                self.editor_shortdesc.set_editable(True)
            if not self.builder.get_object("checkbutton_longdesc").get_active():
                self.editor_longdesc.set_editable(True)
        else:
            #Disable editing of certain options for group edits
            for index in range(len(self.frozen_group_edit)):
                self.builder.get_object("entry_"+self.frozen_group_edit[index]).set_editable(False)
            #shortdesc, longdesc
            self.editor_shortdesc.set_editable(False)
            self.editor_longdesc.set_editable(False)
        self.previous_queue_selection_treepathlist = treepathlist

    ####################################################################################
    ## Checks entries that are available for group edit to see if a group is selected ##
    ## and if so to save that entry's metadata to the class                           ##
    ####################################################################################
    def multi_edit(self,widget):
        if self.builder.get_name(widget) == None:
            widget_prefix = "editor"
            widget_name = "longdesc"
        else:
            widget_prefix = self.builder.get_name(widget).split("_")[0]
            widget_name = self.builder.get_name(widget).split("_")[-1]

        if self.focus == widget: #if you don't check this, every other file in queue will be blanked
            #Don't save a block if it's been marked as "locked"
            model,rows = self.treeselection.get_selected_rows()
            filenames = []
            print "Writing out..."

            for row in rows:
                filenames.append(model.get_value(model.get_iter(row),0))

            for filename in filenames:
                metadata_class = self.array_of_metadata[filename]
                # artistshow, genre, album, albumartist, actors, director, producer, screenwriter, season, TVnetwork, category, keyword, copyright, grouping, encodingtool, comment, sortartist, sortalbumartist, sortalbum, sortshow, trackdenom, diskdenom, stik, contentRating, HD, feedURL, ispodcast, gapless, compilation, advisory
                # coverArt is handled in load_image_from_file
                # single edits come later
                multi_combobox = {"advisory":"rtng","compilation":"cpil","ispodcast":"pcst","gapless":"pgap"}

                if widget_name in self.multi_edit_entry:
                    if not metadata_class.properties.has_key(self.reverse_entry_windows[widget_name]) or not metadata_class.properties[self.reverse_entry_windows[widget_name]][1]:
                        metadata_class.properties[self.reverse_entry_windows[widget_name]]=[self.builder.get_object("entry_"+widget_name).get_text(),self.builder.get_object("checkbutton_"+widget_name).get_active()]
                        #print "Was actually save to metadata_class"

                elif multi_combobox.has_key(widget_name):
                    if metadata_class.properties.has_key(multi_combobox[widget_name]) and not metadata_class.properties[multi_combobox[widget_name]][1]:
                        metadata_class.properties[multi_combobox[widget_name]]=[self.builder.get_object("comboboxtext_"+widget_name).get_active_text(),self.builder.get_object("checkbutton_"+widget_name).get_active()]
                    elif not metadata_class.properties.has_key(multi_combobox[widget_name]):
                        metadata_class.properties[multi_combobox[widget_name]]=[self.builder.get_object("comboboxtext_"+widget_name).get_active_text(),self.builder.get_object("checkbutton_"+widget_name).get_active()]

                elif widget_name == "HD":
                    if metadata_class.properties.has_key("hdvd") and not metadata_class.properties["hdvd"][1] or not metadata_class.properties.has_key("hdvd"):
                        #Non-HD will be stored as 0, 720p as 1, 1080p as 2, saved as int's
                        metadata_class.properties["hdvd"]=[self.builder.get_object("comboboxtext_HD").get_active(), self.builder.get_object("checkbutton_HD").get_active()]

                elif widget_name == "trackdenom":
                    if metadata_class.properties.has_key("trkn") and not metadata_class.properties["trkn"][1]:
                        track,value = metadata_class.properties["trkn"]
                        tracknum = track.split(" ")[0]
                    elif not metadata_class.properties.has_key("trkn"):
                        tracknum = ""
                    if not metadata_class.properties.has_key("trkn") or not metadata_class.properties["trkn"][1]:
                        metadata_class.properties["trkn"]=[tracknum+" of "+self.builder.get_object("entry_trackdenom").get_text(),self.builder.get_object("checkbutton_trackinfo").get_active()]

                elif widget_name == "diskdenom":
                    if metadata_class.properties.has_key("disk") and not metadata_class.properties["disk"][1]:
                        disk,value = metadata_class.properties["disk"]
                        disknum = disk.split(" ")[0]
                    elif not metadata_class.properties.has_key("disk"):
                        disknum = ""
                    if not metadata_class.properties.has_key("disk") or not metadata_class.properties["disk"][1]:
                        metadata_class.properties["disk"]=[disknum+" of "+self.builder.get_object("entry_diskdenom").get_text(),self.builder.get_object("checkbutton_diskinfo").get_active()]

                elif widget_name == "contentRating":
                    metadata_class.properties["contentRating"]=[self.builder.get_object("comboboxtext_contentRating").get_active_text(),self.builder.get_object("checkbutton_contentRating").get_active()]

                elif widget_name == "stik":
                    if self.builder.get_object("comboboxtext_stik").get_active_text() == "TV Show":
                        self.entry_show_buffer = self.builder.get_object("entry_show").get_buffer()
                        #Merge buffer
                        self.builder.get_object("entry_show").set_buffer(self.builder.get_object("entry_artistshow").get_buffer())
                    elif self.builder.get_object("comboboxtext_stik").get_active_text() == "Movie":
                        if hasattr(self,"entry_show_buffer"):
                            self.builder.get_object("entry_show").set_buffer(self.entry_show_buffer)
                            #Unmerge buffer
                            self.builder.get_object("entry_show").set_text(self.builder.get_object("entry_artistshow").get_text())
                    metadata_class.properties["stik"]=[self.builder.get_object("comboboxtext_stik").get_active_text(),self.builder.get_object("checkbutton_stik").get_active()]
                # Handle single-edit only here.

                if len(filenames) == 1:
                    # shortdesc has been handled in limit_textview_length
                    # longdesc, tracknum, disknum
                    # title, date, episode, episodeID, catalogID, episodeURL 
                    single_edits = ["title","date","episode","episodeID","catalogID","episodeURL","purchasedate"]
                    if widget_name == "longdesc":
                        if not metadata_class.properties.has_key("ldes") or not metadata_class.properties["ldes"][1]:
                            metadata_class.properties["ldes"]=[self.editor_longdesc.get_buffer().get_text(self.editor_longdesc.get_buffer().get_start_iter(),self.editor_longdesc.get_buffer().get_end_iter(),False),self.builder.get_object("checkbutton_longdesc").get_active()]
                    elif widget_name in single_edits:
                        if not metadata_class.properties.has_key(self.reverse_entry_windows[widget_name]) or not metadata_class.properties[self.reverse_entry_windows[widget_name]][1]:
                            metadata_class.properties[self.reverse_entry_windows[widget_name]]=[self.builder.get_object("entry_"+widget_name).get_text(),self.builder.get_object("checkbutton_"+widget_name).get_active()]
                    elif widget_name == "tracknum":
                        if self.builder.get_object("entry_trackdenom").get_text() != "":
                            metadata_class.properties["trkn"]=[self.builder.get_object("entry_tracknum").get_text()+" of "+self.builder.get_object("entry_trackdenom").get_text(),self.builder.get_object("checkbutton_trackinfo").get_active()]
                        else:
                            metadata_class.properties["trkn"]=[self.builder.get_object("entry_tracknum").get_text(),self.builder.get_object("checkbutton_trackinfo").get_active()]
                    elif widget_name == "disknum":
                        if self.builder.get_object("entry_trackdenom").get_text() != "":
                            metadata_class.properties["disk"]=[self.builder.get_object("entry_disknum").get_text()+" of "+self.builder.get_object("entry_diskdenom").get_text(),self.builder.get_object("checkbutton_diskinfo").get_active()]
                        else:
                            metadata_class.properties["disk"]=[self.builder.get_object("entry_disknum").get_text(),self.builder.get_object("checkbutton_diskinfo").get_active()]


    ##################################################################################
    ## Resets the main window to all blank TextEntries, CheckButtons and ComboBox's ##
    ## and resets the chapter information                                           ##
    ##################################################################################
    def clear_window(self):
        #tell prefill notebook not to run when search results selection is wiped when file removed from queue
        self.clearing_window = True

        self.focus = self.builder.get_object("entry_searchtext")
        if not self.prefilling:
            self.builder.get_object("liststore_searchresults").clear()
        self.liststore_chapters.clear()
        if hasattr(self,"entry_show_buffer"):
            self.builder.get_object("entry_show").set_buffer(self.entry_show_buffer)
        widgets = ["searchtext", "title", "artistshow", "date", "genre", "album", "albumartist", "purchasedate", "actors", "director", "producer", "screenwriter", "show", "episodeID", "season", "episode", "TVnetwork", "catalogID", "feedURL", "episodeURL", "category", "keyword", "copyright", "grouping", "encodingtool", "comment", "tracknum", "trackdenom", "disknum", "diskdenom", "tagname", "tagartist", "tagalbumartist", "tagalbum", "tagshow", "sortname", "sortartist", "sortalbumartist", "sortalbum", "sortshow"]
        for item in widgets:
            self.clear_text(item)
        widgets = ["title", "artistshow", "date", "genre", "album", "albumartist", "purchasedate", "actors", "director", "producer", "screenwriter", "show", "episodeID", "season", "episode", "TVnetwork", "catalogID", "feedURL", "episodeURL", "category", "keyword", "copyright", "grouping", "encodingtool", "comment", "trackinfo", "diskinfo", "sortname", "sortartist", "sortalbumartist", "sortalbum", "sortshow", "advisory", "ispodcast", "gapless", "compilation", "stik", "HD", "contentRating", "coverArt", "chapters"]
        for item in widgets:
            self.clear_checkbutton(item)
        widgets = ["contentRating","stik","HD","advisory","ispodcast","gapless","compilation"]
        for item in widgets:
            self.builder.get_object("comboboxtext_" + item).set_active(-1)
        self.editor_shortdesc.get_buffer().set_text("")
        self.editor_longdesc.get_buffer().set_text("")
        #Default, Loads the cow image
        self.image_coverart.set_from_file("./data/media/metau.png")
        self.builder.get_object("label_iconsize").set_label("Icon Size")
        self.loaded_image = None

        self.clearing_window = False

    def clear_coverArt(self, widget):
        model,rows = self.treeselection.get_selected_rows()
        #reset the value in the metadata_class
        for row in rows:
            try:
                del self.array_of_metadata[self.liststore_queue.get_value(model.get_iter(row),0)].properties["coverArt"]
            except KeyError:
                pass
        #Default, Loads the cow image
        self.image_coverart.set_from_file("./data/media/metau.png")
        self.builder.get_object("checkbutton_coverArt").set_active(False)
        self.builder.get_object("label_iconsize").set_label("Icon Size")
        self.loaded_image = None

    #############################################################
    ## Helper function to clear_window, clears TextEntry boxes ##
    #############################################################
    def clear_text(self, object_basename):
        self.builder.get_object("entry_" + object_basename).set_text("")

    ###############################################################
    ## Helper function to clear_window, clears CheckButton boxes ##
    ###############################################################
    def clear_checkbutton(self, object_basename):
        self.builder.get_object("checkbutton_" + object_basename).set_active(False)

    #####################################################################################
    ## Helper function to update_window, sets entry to "text" and sets the checkbutton ##
    #####################################################################################
    def update_entry_widget(self,basename,text,checkbutton):
        self.builder.get_object("entry_"+basename).set_text(text)
        self.checkbutton_draw(checkbutton,"checkbutton_"+basename)

    ##################################################################################
    ## Grabs the formatted_properties text string from a metadata class and updates ##
    ## the main window to fill in the metadata                                      ##
    ##################################################################################
    def update_window(self, MetaDataKey):
        self.updating_window = True
        self.clear_window()
        metadata_class = self.array_of_metadata[MetaDataKey]

        if metadata_class.properties.has_key("coverArt"):
            print "pre update_window",metadata_class.properties["coverArt"]

        if hasattr(metadata_class,'chapter_info'):
            for index in range(len(metadata_class.chapter_info)):
                self.liststore_chapters.append([metadata_class.chapter_info[index][0], metadata_class.chapter_info[index][1], metadata_class.chapter_info[index][2]])

        if metadata_class.save_chapters:
            self.builder.get_object("checkbutton_chapters").set_active(True)

        if metadata_class.properties.has_key('stik') and metadata_class.properties["stik"][0] == "TV Show":
            #merge buffers
            self.entry_show_buffer = self.builder.get_object("entry_show").get_buffer()
            self.builder.get_object("entry_show").set_buffer(self.builder.get_object("entry_artistshow").get_buffer())
        elif hasattr(self,"entry_show_buffer"):
            #unmerge buffers
            self.builder.get_object("entry_show").set_buffer(self.entry_show_buffer)
            self.builder.get_object("entry_show").set_text(self.builder.get_object("entry_artistshow").get_text())

        #set the search text to either the value of the "(c)nam" atom or if it doesn't exist, the root filename
        if metadata_class.properties.has_key("nam"):
            self.builder.get_object("entry_searchtext").set_text(metadata_class.properties["nam"][0])
        else:
            search_text = re.sub("\\\\","",metadata_class.filename)
            self.builder.get_object("entry_searchtext").set_text(re.sub("\..*$","",search_text).split("/")[-1])

        for atom_name in metadata_class.properties:
            #print atom
            atom = metadata_class.properties[atom_name]
            #update window widgets as appropriate
            if atom_name in self.entry_windows:
                self.update_entry_widget(self.entry_windows[atom_name],atom[0],atom[1])
                
            if atom_name == "day": #strip the T16:00:00Z off the end if it exists
                self.update_entry_widget("date",re.sub("T[0-9]+:[0-9]+:[0-9]+[A-Z]","",atom[0]),atom[1])
            if atom_name == "purd":
                self.update_entry_widget("purchasedate",re.sub("T[0-9]+:[0-9]+:[0-9]+[A-Z]","",atom[0]),atom[1])
            elif atom_name == "contentRating": # Movie/TV MPAA Rating (i.e. PG, TV-Y)
                possible_ratings = {"G":0,"PG":1,"PG-13":2,"R":3,"NC-17":4,"Unrated":5,"TV-Y7":6,"TV-Y":7,"TV-G":8,"TV-PG":9,"TV-14":10,"TV-MA":11}
                self.builder.get_object("comboboxtext_contentRating").set_active(possible_ratings[atom[0]])
                self.checkbutton_draw(atom[1],"checkbutton_contentRating")
            elif atom_name == "trkn": #tracknum
                track_array = atom[0].split(' ')
                self.builder.get_object("entry_tracknum").set_text(track_array[0])
                if len(track_array) > 2:
                    self.builder.get_object("entry_trackdenom").set_text(track_array[2])
                self.checkbutton_draw(atom[1],"checkbutton_trackinfo")
            elif atom_name == "disk": #disk num and denom
                disk_array = atom[0].split(' ')
                self.builder.get_object("entry_disknum").set_text(disk_array[0])
                if len(disk_array) > 2:
                    self.builder.get_object("entry_diskdenom").set_text(disk_array[2])
                self.checkbutton_draw(atom[1],"checkbutton_diskinfo")
            elif atom_name == "tvsh":  #title / artist(show) | actors / artist(show)
                self.builder.get_object("entry_artistshow").set_text(atom[0])
                self.checkbutton_draw(atom[1],"checkbutton_artistshow")
                self.builder.get_object("entry_show").set_text(atom[0])
                self.checkbutton_draw(atom[1],"checkbutton_show")
            elif atom_name == "desc": #shortdesc
                self.editor_shortdesc.get_buffer().set_text(atom[0])
                self.checkbutton_draw(atom[1],"checkbutton_shortdesc")
            elif atom_name == "ldes": #longdesc
                self.editor_longdesc.get_buffer().set_text(atom[0])
                self.checkbutton_draw(atom[1],"checkbutton_longdesc")
            elif atom_name == "pgap": #gapless
                if atom[0] == "false":
                    self.builder.get_object("comboboxtext_gapless").set_active(0)
                elif atom[0] == "true":
                    self.builder.get_object("comboboxtext_gapless").set_active(1)
                self.checkbutton_draw(atom[1],"checkbutton_gapless")
            elif atom_name == "cpil": #compilation
                if atom[0] == "false":
                    self.builder.get_object("comboboxtext_compilation").set_active(0)
                elif atom[0] == "true":
                    self.builder.get_object("comboboxtext_compilation").set_active(1)
                self.checkbutton_draw(atom[1],"checkbutton_compilation")
            elif atom_name == "hdvd":
                print "HDVD atom: " + str(atom[0])
                self.builder.get_object("comboboxtext_HD").set_active(atom[0])
                self.checkbutton_draw(atom[1],"checkbutton_HD")
            elif atom_name == "stik":
                stik = atom[0]
                if stik == "Short Film" or stik == "Movie":
                    self.builder.get_object("comboboxtext_stik").set_active(1)
                elif stik == "TV Show":
                    self.builder.get_object("comboboxtext_stik").set_active(0)
                self.checkbutton_draw(atom[1],"checkbutton_stik")
            elif atom_name == "rtng": #rating/Advisory
                if atom[0] == "Inoffensive":
                    self.builder.get_object("comboboxtext_advisory").set_active(0)
                elif atom[0] == "Clean Content":
                    self.builder.get_object("comboboxtext_advisory").set_active(1)
                elif atom[0] == "Explicit Content":
                    self.builder.get_object("comboboxtext_advisory").set_active(2)
                self.checkbutton_draw(atom[1],"checkbutton_advisory")
            elif atom_name == "pcst":
                if atom[0] == "true":
                    self.builder.get_object("comboboxtext_ispodcast").set_active(1)
                elif atom[0] == "false":
                    self.builder.get_object("comboboxtext_ispodcast").set_active(0)
            elif atom_name == "purd":
                pass
            elif atom_name == "tagname":
                pass
            elif atom_name == "tagartist":
                pass
            elif atom_name == "tagalbumartist":
                pass
            elif atom_name == "tagalbum":
                pass
            elif atom_name == "tagshow":
                pass
            elif atom_name == "soco": #sort composer
                pass
            elif atom_name == "coverArt":
                print "test", atom[0], atom[1]
                self.load_image_from_file(atom[0])
                self.checkbutton_draw(atom[1],"checkbutton_coverArt")
            #TODO implement adding lyrics to a song
            #elif atom_name == "lyr":
            #    pass
            #elif atom_name == lyricFile:
            #elif atom_name == "wrt":  #composer
            #    pass
            #elif atom_name == "tmpo":
            #    pass
        if metadata_class.properties.has_key("coverArt"):
            print "post update_window",metadata_class.properties["coverArt"]
        self.updating_window = False

    #################################################################################
    ## Helper function to update_window, sets the CheckButton either active or not ##
    ## and freezes/unfreezes the corresponding widgets                             ##
    #################################################################################
    def checkbutton_draw(self, locked_bool, object_name):
        name_prefix = object_name.split("_")[0]
        name_suffix = object_name.split("_")[1]
        if self.reverse_entry_windows.has_key(name_suffix):
            if name_suffix == "trackinfo":
                if locked_bool:
                    self.builder.get_object("entry_tracknum").set_editable(False)
                    self.builder.get_object("entry_trackdenom").set_editable(False)
                else:
                    self.builder.get_object("entry_tracknum").set_editable(True)
                    self.builder.get_object("entry_trackdenom").set_editable(True)
            elif name_suffix == "diskinfo":
                if locked_bool:
                    self.builder.get_object("entry_disknum").set_editable(False)
                    self.builder.get_object("entry_diskdenom").set_editable(False)
                else:
                    self.builder.get_object("entry_disknum").set_editable(True)
                    self.builder.get_object("entry_diskdenom").set_editable(True)
            else:
                if locked_bool:
                    self.builder.get_object("entry_"+name_suffix).set_editable(False)
                else:
                    self.builder.get_object("entry_"+name_suffix).set_editable(True)
        #TODO Freeze/unfreeze comboboxtext's
            #somewhat implemented you can change the comboboxtext but it won't save it
            #coverArt will not load if the checkbutton is active
        if locked_bool:
            self.builder.get_object(object_name).set_active(True)
            print "here",object_name
        else:
            self.builder.get_object(object_name).set_active(False)

    ############################################################################################
    ## save_chapter_info when liststore_chapters changes, save chapter info to metadata class ##
    ############################################################################################
    def save_chapter_info(self, treemodel=None, path=None, iterator=None):
        if not self.updating_window and not self.prefilling:
            #Chapters
            model,rows = self.treeselection.get_selected_rows()
            if len(rows) == 1:
                filename = model.get_value(model.get_iter(rows[0]),0)
                if self.array_of_metadata.has_key(filename):
                    metadata_class = self.array_of_metadata[filename]
                    del metadata_class.chapter_info[:]
                    if self.builder.get_object("checkbutton_chapters").get_active():
                        metadata_class.save_chapters = True
                    else:
                        metadata_class.save_chapters = False
                    if self.liststore_chapters.iter_n_children(None) != 0:
                        for index in range(self.liststore_chapters.iter_n_children(None)):
                            chap_len_msec = 0
                            try:
                                chap_len_msec = self.hhmmssmmm(self.liststore_chapters.get_value(self.liststore_chapters.get_iter(index),2))
                            except ValueError:
                                dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Chapter Duration Format")
                                dialog.format_secondary_text("The proper format for chapter durations are HH:MM:SS.mmm, hours, minutes, seconds, and milliseconds.  Duration will be defaulted to 0 until corrected.")
                                dialog.run()
                                dialog.destroy()
                                metadata_class.chapter_info.append([self.liststore_chapters.get_value(self.liststore_chapters.get_iter(index),0), self.liststore_chapters.get_value(self.liststore_chapters.get_iter(index),1), self.liststore_chapters.get_value(self.liststore_chapters.get_iter(index),2), 0])
                                print "Error, invalid chapter duration", self.liststore_chapters.get_value(self.liststore_chapters.get_iter(index),2) ,", proper format HH:MM:SS.mmm"
                            else:
                                metadata_class.chapter_info.append([self.liststore_chapters.get_value(self.liststore_chapters.get_iter(index),0), self.liststore_chapters.get_value(self.liststore_chapters.get_iter(index),1), self.liststore_chapters.get_value(self.liststore_chapters.get_iter(index),2), chap_len_msec])
                        metadata_class.total_chapters_in_file = len(metadata_class.chapter_info)
                    else:
                        pass

    def hhmmssmmm(self, timestamp):
        if len(re.findall("[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{3}",timestamp)) == 0:
            raise ValueError
        else:
            hr = re.findall("[0-9]{2}",timestamp)[0]
            mn = re.findall("[0-9]{2}",timestamp)[1]
            ss = re.findall("[0-9]{2}",timestamp)[2]
            msec = re.findall("[0-9]{3}",timestamp)[0]
            return int(msec) + int(ss)*1000 + int(mn)*60000 + int(hr)*3600000 

    ########################################################################################
    ## move_chapter_up move selected chapter up one space in the queue ##
    ########################################################################################
    def move_chapter_up(self, widget):
        model,rows = self.treeview_chapters_selection.get_selected_rows()
        if len(rows) == 1:
            row_moving_up = model.get_iter(rows[0]) #pointer to row_moving_up
            path = int(model.get_string_from_iter(row_moving_up))    #find path of row_moving_up
            if path != 0:
                sibling = model.get_iter_from_string(str(path-1)) #find row above "sibling" if not in the first row
                moved_row = self.liststore_chapters.insert_before(sibling, [model.get_value(row_moving_up,0), model.get_value(row_moving_up,1), model.get_value(row_moving_up,2)])
                self.liststore_chapters.remove(row_moving_up) #remove the old row when done
                self.treeview_chapters_selection.unselect_all()
                self.treeview_chapters_selection.select_iter(moved_row) #make row_moving_up the current selection
                for row_path_int in range(self.liststore_chapters.iter_n_children(None)):
                    temp_iter = self.liststore_chapters.get_iter_from_string(str(row_path_int))
                    self.liststore_chapters.set_value(temp_iter,0,str(row_path_int+1))
            
    ########################################################################################
    ## move_chapter_down move selected chapter down one space in the queue ##
    ########################################################################################
    def move_chapter_down(self, widget):
        model,rows = self.treeview_chapters_selection.get_selected_rows()
        if len(rows) == 1:
            row_moving_down = model.get_iter(rows[0]) #pointer to row_moving_down
            path = int(model.get_string_from_iter(row_moving_down))    #find path of row_moving_down
            if path != self.liststore_chapters.iter_n_children(None)-1: #if not last item in the view
                sibling = model.get_iter_from_string(str(path+1)) #find row below, "sibling"
                moved_row = self.liststore_chapters.insert_after(sibling, [model.get_value(row_moving_down,0), model.get_value(row_moving_down,1), model.get_value(row_moving_down,2)])
                self.liststore_chapters.remove(row_moving_down) #remove the old row_when_done
                self.treeview_chapters_selection.unselect_all()
                self.treeview_chapters_selection.select_iter(moved_row) #make row_moving_up the current selection
                for row_path_int in range(self.liststore_chapters.iter_n_children(None)):
                    temp_iter = self.liststore_chapters.get_iter_from_string(str(row_path_int))
                    self.liststore_chapters.set_value(temp_iter,0,str(row_path_int+1))    

    #######################################################################################
    ##  Threading functions
    #######################################################################################
    def set_progress_bar_percent_as_int(self, model, row, percent_as_int):
        self.liststore_queue.set_value(model.get_iter(row), 1, percent_as_int)

    def write_out(self, command_line, model, row):
        child = subprocess.Popen(shlex.split(command_line), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        previous_char_is_int = False
        percent_as_int = 0

        while True:
            out = child.stdout.read(1)
            if out == '' and child.poll() != None:
                break
            if out != '':
                try:
                    int(out)
                except ValueError:
                    if previous_char_is_int:
                        Gdk.threads_enter()
                        GObject.idle_add(self.set_progress_bar_percent_as_int, model, row, percent_as_int)
                        if percent_as_int == 100:
                            self.builder.get_object("label_status").set_text("Successfully wrote " + model.get_value(model.get_iter(row),0) + " to file.")
                        Gdk.threads_leave()

                        #sys.stdout.write(str(percent_as_int) + "\n")
                        #sys.stdout.flush()

                        previous_char_is_int = False
                    else:
                        pass
                else:
                    if previous_char_is_int:
                        percent_as_int = int(str(percent_as_int) + out)
                    else:
                        percent_as_int = int(out)
                    previous_char_is_int = True

    def writeout_in_thread(self, command_line, model, row):
        Thread(target=self.write_out, args=(command_line,model,row)).start()


    ########################################################################################
    ## writeout() The whole meat and potatoes, take the properties and write them to file ##
    ########################################################################################
    def writeout(self, widget):
        #Make a dictionary mapping property values to AtomicParsley command line arguments
        #For each item selected in queue call an AtomicParsley process with all the command line arguments
        #For each item selected in queue call a ./write_chapters process to write chapterinfo to file
        #TODO Update queue model with process from both HandBrakeCLI and AP processes
            #TODO reuse code from mythtv project to expand the progress line
        #TODO rainy day, think about deleting atoms from file if block is empty and value is "locked"
            #currently they are just blanked out, which is essentially the same thing
        write_dict_strings = { "alb":"--album", "aART":"--albumArtist", "ART":"--artist", "catg":"--category", "cmt":"--comment", "wrt":"--composer", "cprt":"--copyright", "desc":"--description", "enc":"--encodedBy", "too":"--encodingTool", "gnre":"--genre", "grp":"--grouping", "keyw":"--keyword", "ldes":"--longdesc", "nam":"--title", "tves":"--TVEpisodeNum", "tvnn":"--TVNetwork", "tvsh":"--TVShowName" }
        write_dict_ints = { "cnID":["--cnID","catalog ID"], "tven":["--TVEpisode","Episode"], "tvsn":["--TVSeasonNum","Season"] }
        write_dict_bools = { "cpil":"--compilation", "hdvd":"--hdvideo", "pcst":"--podcastFlag", "pgap":"--gapless" }
        write_dict_urls = { "egid":"--podcastGUID", "purl":"--podcastURL" } 
        write_dict_num_denom = {"disk":"--disk", "trkn":"--tracknum" }

        model,rows = self.treeselection.get_selected_rows()

        if len(rows) != 0:
            #filenames = []
            command_line = self.home + "/.metau/AtomicParsley "

            for row in rows:
                filename = model.get_value(model.get_iter(row),0)
                #filenames.append(model.get_value(model.get_iter(row),0))
            #for filename in filenames:

                command_line += self.escape_for_bash(filename) + " --overWrite"

                metadata_class = self.array_of_metadata[filename]


                #TODO
                #write_dict_bools

                for key in write_dict_strings:
                    #if the key exists and the item was checked in the GUI
                    if metadata_class.properties.has_key(key) and metadata_class.properties[key][1]:
                        #passing string to bash, so make sure to escape any double quotes
                        command_line += " " + write_dict_strings[key] + ' "' + str(metadata_class.properties[key][0]).replace('"','\\"') + '"'
                for key in write_dict_ints:
                    if metadata_class.properties.has_key(key) and metadata_class.properties[key][1]:
                        try:
                            int(metadata_class.properties[key][0])
                        except ValueError:
                            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "Interger Input Error")
                            dialog.format_secondary_text("The entry for " + write_dict_ints[key][1] + " of " + filename + " is not a valid integer.  Writing Aborted...")
                            dialog.run()
                            print "Invalid integer for" + write_dict_ints[key][1] + " in " + filename
                            dialog.destroy()
                            return
                        command_line += " " + write_dict_ints[key][0] + " " + str(metadata_class.properties[key][0])

                #write_dict_urls
                for key in write_dict_urls:
                    if metadata_class.properties.has_key(key) and metadata_class.properties[key][1]:
                        command_line += " " + write_dict_urls[key] + " \"" + metadata_class.properties[key][0] + "\""

                #write_dict_num_denom
                if metadata_class.properties.has_key("trkn") and metadata_class.properties["trkn"][1]:
                    command_line += " --tracknum " + re.sub(" of ", "/", metadata_class.properties["trkn"][0])
                if metadata_class.properties.has_key("disk") and metadata_class.properties["disk"][1]:
                    command_line += " --disk " + re.sub(" of ", "/", metadata_class.properties["disk"][0])        

                #write UTC's
                # if date is in the form 2012-02-03 add "T16:00:00Z"
                if metadata_class.properties.has_key("day") and metadata_class.properties["day"][1]:
                    #check if the entry is just XXXX-XX-XX, then add "T16:00:00Z"
                    if re.match("^[0-9]{4}-[0-9]+-[0-9]+$", metadata_class.properties["day"][0]) != None:
                        metadata_class.properties["day"][0] = metadata_class.properties["day"][0] + "T16:00:00Z"
                    command_line += " --year " + metadata_class.properties["day"][0]
                if metadata_class.properties.has_key("purd") and metadata_class.properties["purd"][1]:
                    #check if the entry is just XXXX-XX-XX, then add "T16:00:00Z"
                    if re.match("^[0-9]{4}-[0-9]+-[0-9]+$", metadata_class.properties["purd"][0]) != None:
                        metadata_class.properties["purd"][0] = metadata_class.properties["purd"][0] + "T16:00:00Z"
                    command_line += " --purchaseDate " + metadata_class.properties["purd"][0]

                if metadata_class.properties.has_key("stik") and metadata_class.properties["stik"][1]:
                    #stik values given by combobox, no sanitation req'd
                    command_line += " --stik \"" + str(metadata_class.properties["stik"][0]) + "\""

                if metadata_class.properties.has_key("contentRating") and metadata_class.properties["contentRating"][1]:
                    #contentRating given by combobox, no sanitation req'd
                    command_line += " --contentRating " + str(metadata_class.properties["contentRating"][0])

                if metadata_class.properties.has_key("coverArt") and metadata_class.properties["coverArt"][1] and metadata_class.properties["coverArt"][0] != "":
                    command_line += " --artwork " + self.escape_for_bash(metadata_class.properties["coverArt"][0])
                #TODO special cases
                #"rtng" -> "advisory"
                #"soaa":"sortalbumartist","--sortOrder"
                #"soal":"sortalbum",
                #"soar":"sortartist",
                #"sonm":"sortname",
                #"sosn":"sortshow",
                #"cast_members":"actors",  XML-ish format
                #"directors":"director",   XML-ish format
                #"producers":"producer",   XML-ish format
                #"screenwriters":"screenwriter",  XML-ish format

                #future implementation
                #"lyr":"--lyrics" or "--lyricsFile"
                #"tmpo":"--bpm"

                #"chapter_info"
                if metadata_class.save_chapters and hasattr(metadata_class, "chapter_info") and len(metadata_class.chapter_info) != 0:
                    chapter_info_command = self.home + "/.metau/write_chapters " + self.escape_for_bash(filename) + " -n " + str(metadata_class.total_chapters_in_file) 
                    for index in range(len(metadata_class.chapter_info)):
                        if metadata_class.chapter_info[index][3] == 0:
                            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Invalid Chapter Length")
                            dialog.format_secondary_text("Chapter " + str(metadata_class.chapter_info[index][0]) + " of " + filename + " has an invalid length of 0.  Writing Aborted...")
                            dialog.run()
                            print "Invalid integer for" + write_dict_ints[key][1] + " in " + filename
                            dialog.destroy()
                            return
                        chapter_info_command += " -t \"" + metadata_class.chapter_info[index][1].replace('"','\\"') + "\" -d " + str(metadata_class.chapter_info[index][3])
                    print chapter_info_command
                    proc = subprocess.Popen([chapter_info_command], stdout=subprocess.PIPE, shell=True)
                    (out,err) = proc.communicate()
                    lines = out.splitlines()

                    #writing chapter info goes first because the main thread doesn't wait on AtomicParsley to finish
                    #so we don't want to clobber a file write in progress or update the wrong copy
                    #If the chapter info is the only task, then give the user feedback that this task has completed
                    self.builder.get_object("label_status").set_text("Successfully wrote chapter info to " + filename)
                    self.liststore_queue.set_value(model.get_iter(row), 1, 100)

                print command_line

                #no use spawning a thread if no data is selected to write
                if command_line != self.home + "/.metau/AtomicParsley " + self.escape_for_bash(filename) + " --overWrite":
                    #print "Writing " + filename + "..."
                    self.builder.get_object("label_status").set_text("Writing " + filename + "...")

                    self.writeout_in_thread(command_line, model, row)
                else:
                    #print "No data selected to write out, no use spawning a thread."
                    self.builder.get_object("label_status").set_text("WARNING: No data selected to write out to file.")

                command_line = self.home + "/.metau/AtomicParsley "

        else:
            self.builder.get_object("label_status").set_text("WARNING: No files selected to write out.")

    ########################################################################################
    ## prefill_notebook(widget) Fill in notebook with selected searchresult info if the   ##
    ##      hasn't been filled in by metadata in the file or inputted by user.            ##
    ########################################################################################
    def prefill_notebook(self, widget):
        if not self.updating_window and not self.clearing_window:
            #get the filenames selected in the queue
            model_queue,rows_queue = self.treeselection.get_selected_rows()
            filename = model_queue.get_value(model_queue.get_iter(rows_queue[0]),0)
            self.treeselection.select_iter(model_queue.get_iter(rows_queue[0]))

            #find the path of the selected searchresult, it will tell me which index of self.array_of_results i need to call
            model,row_iter = self.builder.get_object("treeselection_searchresults").get_selected()
            result_path_int = int(self.builder.get_object("liststore_searchresults").get_string_from_iter(row_iter))

            self.prefilling = True
            self.update_window(filename)

            #put the searchresult title/name in the entry_searchtext widget
            if self.array_of_results[result_path_int][0].properties.has_key("nam"):
                self.builder.get_object("entry_searchtext").set_text(self.array_of_results[result_path_int][0].properties["nam"])

            if len(rows_queue) == 1:    #fill in items that are only single edits
                        # tracknum, disknum
                        # shortdesc, longdesc, title, date, episode, episodeID, catalogID, episodeURL, sortname
                single_edits = {"desc":"shortdesc", "ldes":"longdesc", "trkn":"entry_tracknum", "disk":"entry_disknum", "chapter_info":"chapter_info", "nam":"entry_title", "day":"entry_date", "tves":"entry_episode", "tven":"entry_episodeID", "cnID":"entry_catalogID", "egID":"entry_episodeURL", "sonm":"entry_sortname"}
                #for each file selected in queue, see if the properties dict has the keys available in array_of_results
                for atom in single_edits:
                    #if the atom was even in the search results
                    if self.array_of_results[result_path_int][0].properties.has_key(atom):
                        #if the atom doesn't exist in the metadata class, or it's an empty string AND it's not "locked"
                        #fill in the window widget, NOT the metadata class property value
                        if not self.array_of_metadata[filename].properties.has_key(atom) or (self.array_of_metadata[filename].properties[atom][0] == "" and not self.array_of_metadata[filename].properties[atom][1]):
                            if self.array_of_results[result_path_int][0].properties.has_key(atom):
                                if atom == "trkn" or atom == "disk":    #slightly special case
                                    self.builder.get_object(single_edits[atom]).set_text(self.array_of_results[result_path_int][0].properties[atom].split(" ")[0])
                                elif atom == "desc":
                                    self.editor_shortdesc.get_buffer().set_text(self.array_of_results[result_path_int][0].properties[atom])
                                elif atom == "ldes":
                                    self.editor_longdesc.get_buffer().set_text(self.array_of_results[result_path_int][0].properties[atom])
                                elif atom == "chapter_info": #Definitely a special case
                                    if len(self.array_of_results[result_path_int][0].properties[atom]) == self.builder.get_object("liststore_chapters").iter_n_children(None):
                                        for index in range(len(self.array_of_results[result_path_int][0].properties[atom])):
                                            #print self.array_of_results[result_path_int][0].properties[atom][index][1], self.builder.get_object("liststore_chapters").get_value(self.builder.get_object("liststore_chapters").iter_nth_child(None, index),1)
                                            if self.array_of_results[result_path_int][0].properties[atom][index][2] != self.builder.get_object("liststore_chapters").get_value(self.builder.get_object("liststore_chapters").iter_nth_child(None, index),1):
                                                self.builder.get_object("liststore_chapters").set_value(self.builder.get_object("liststore_chapters").iter_nth_child(None, index),1,self.array_of_results[result_path_int][0].properties[atom][index][1])
                                    else:
                                        # See if the total length of the chapters result is equal
                                        # to or longer than the duration of the file, that way we can
                                        # add more chapters to a file that only has 1 main chapter, and
                                        # can also make sure that the chapters from the internet don't 
                                        # corrupt the file
                                        total_result_duration = 0
                                        for index in range(len(self.array_of_results[result_path_int][0].properties[atom])):
                                            result_duration = self.array_of_results[result_path_int][0].properties[atom][index][2]
                                            temp = re.findall("[0-9]{2}", result_duration)
                                            if len(temp) == 3:
                                                total_result_duration += int(temp[0]*3600000) + int(temp[1]*60000) + int(temp[2]*1000)
                                            temp = re.findall("[0-9]{3}$",result_duration)
                                            if len(temp) == 1:
                                                total_result_duration += int(temp[0])
                                        if total_result_duration <= self.array_of_metadata[filename].total_length:
                                            self.builder.get_object("liststore_chapters").clear()
                                            for index in range(len(self.array_of_results[result_path_int][0].properties[atom])):
                                                self.builder.get_object("liststore_chapters").append([self.array_of_results[result_path_int][0].properties[atom][index][0], self.array_of_results[result_path_int][0].properties[atom][index][1], self.array_of_results[result_path_int][0].properties[atom][index][2]])
                                        if total_result_duration == 0:
                                            #Show an error and a solution
                                            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "Chapter Info Length Mismatch")
                                            dialog.format_secondary_text("The internet results retrieved do not appear to have any length information associated with them.  Please make sure to edit this information yourself.")
                                            dialog.run()
                                            print "Chapter Info Length not available."
                                            dialog.destroy()
                                else:
                                    self.builder.get_object(single_edits[atom]).set_text(self.array_of_results[result_path_int][0].properties[atom])

            #fill in the multi-edits
            # stik, ART, tvsh, egID, gen, alb, aART, tvsn, tvnn, catg, keyw, cprt, grp, too, cmt, soar, soal, soaa, cast_members, directors, producers, screenwriters
            #trackdenom, diskdenom are somewhat special cases
            #rtng is a somewhat special case, regex for similarities
            #coverArt is definitely a special case
                #download to /tmp then load the image from the file
            # hdvd, purd, pcst, cnID, purl, egID, cpil, pgap, enc, too are not available from tagchimp but may be available from other sources
            multi_edits = {"stik":"comboboxtext_stik", "rtng":"comboboxtext_advisory", "contentRating":"comboboxtext_contentRating", "ART":"entry_artistshow", "tvsh":"entry_show", "purl":"entry_feedURL", "gnre":"entry_genre", "alb":"entry_album", "aART":"entry_albumartist", "tvsn":"entry_season", "tvnn":"entry_TVnetwork", "catg":"entry_category", "keywd":"entry_keyword", "cprt":"entry_copyright", "grp":"entry_grouping", "too":"entry_encodingtool", "cmt":"entry_comment", "soar":"entry_sortartist", "soal":"entry_sortalbum", "soaa":"entry_sortalbumartist", "cast_members":"entry_actors", "directors":"entry_director", "producers":"entry_producer", "screenwriters":"entry_screenwriter", "trkn":"entry_trackdenom", "disk":"entry_disndenom", "coverArt":"image_coverArt"}

            for atom in multi_edits:
                if not self.array_of_metadata[filename].properties.has_key(atom) or (self.array_of_metadata[filename].properties[atom][0] == "" and not self.array_of_metadata[filename].properties[atom][1]):
                    if self.array_of_results[result_path_int][0].properties.has_key(atom):
                        if atom == "trkn" or atom == "disk":    #slightly special case
                            if self.array_of_results[result_path_int][0].properties[atom].split(" ")[-1] != None:
                                self.builder.get_object(multi_edits[atom]).set_text(self.array_of_results[result_path_int][0].properties[atom].split(" ")[-1])
                        elif atom == "rtng":
                            if re.search("[Ii][Nn][Oo][Ff]{2}[Ee][Nn][Ss][iI][Vv][Ee]",self.array_of_results[result_path_int][0].properties[atom]):
                                self.builder.get_object(multi_edits[atom]).set_active(0) #"Inoffensive"
                            elif re.search("[Cc][Ll][Ee][Aa][Nn]", self.array_of_results[result_path_int][0].properties[atom]):
                                self.builder.get_object(multi_edits[atom]).set_active(1) #"Clean Content"
                            elif re.search("[Ee][Xx][Pp][Ll][iI][Cc][Ii][Tt]",self.array_of_results[result_path_int][0].properties[atom]):
                                self.builder.get_object(multi_edits[atom]).set_active(2) #"Explicit Content"
                        elif atom == "contentRating":
                            ratings = {"G":0,"PG":1,"PG-13":2,"R":3,"Unrated":4,"NC-17":5,"TV-Y7":6,"TV-Y":7,"TV-G":8,"TV-PG":9,"TV-14":10,"TV-MA":11}
                            try:
                                self.builder.get_object(multi_edits[atom]).set_active(ratings[self.array_of_results[result_path_int][0].properties[atom]])
                            except KeyError:
                                print "Non-US Rating, skipping..."
                        elif atom == "stik":
                            if self.array_of_results[result_path_int][0].properties[atom] == "TV Show":
                                self.builder.get_object(multi_edits[atom]).set_active(0) #TV Show
                            elif self.array_of_results[result_path_int][0].properties[atom] == "Movie":
                                self.builder.get_object(multi_edits[atom]).set_active(1) #Movie
                        elif atom == "coverArt":
                            temp_coverArt_filename = "/tmp/" + self.array_of_results[result_path_int][0].properties[atom].split('/')[-1]
                            print "temp_coverArt_filename", temp_coverArt_filename, "result_path_int", result_path_int
                            if not self.builder.get_object("checkbutton_coverArt").get_active():
                                print "Test coverart"
                                if not temp_coverArt_filename in self.temp_coverart:
                                    try:
                                        # urlretrieve wasn't working anymore
                                        # curl --user-agent "Mozilla/4.0" 
                                        proc = subprocess.Popen(["curl --user-agent \"Mozilla/4.0\" " + self.array_of_results[result_path_int][0].properties[atom] + " > " + temp_coverArt_filename], stdout=subprocess.PIPE, shell=True)
                                        (out,err) = proc.communicate()
                                        lines = out.splitlines()
                                        #urlretrieve(self.array_of_results[result_path_int][0].properties[atom], temp_coverArt_filename)
                                    except IOError:
                                        print "IOError, bad filename in retrieved URL."
                                        break
                                    else:
                                        self.temp_coverart [temp_coverArt_filename]=[temp_coverArt_filename]
                                pixbuf_format, width, height = GdkPixbuf.Pixbuf.get_file_info(temp_coverArt_filename)
                                self.width = width
                                self.height = height
                                if width > height:
                                    height = -1
                                    width = 125
                                else:
                                    width = -1
                                    height = 125
                                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(temp_coverArt_filename, width, height, True)
                                self.image_coverart.set_from_pixbuf(pixbuf)
                                self.label_iconsize.set_text("Icon Size (" + str(self.width) + "x" + str(self.height) + ")")
                                self.loaded_image = temp_coverArt_filename
                        elif atom == "tvsn":
                            self.builder.get_object(multi_edits[atom]).set_text(self.array_of_results[result_path_int][0].properties[atom])
                            if self.array_of_results[result_path_int][0].properties.has_key("nam") and self.array_of_results[result_path_int][0].properties["nam"] != "" and self.builder.get_object("comboboxtext_stik").get_active() == 1:
                                self.builder.get_object("entry_album").set_text(self.array_of_results[result_path_int][0].properties["nam"] + ", Season " + self.array_of_results[result_path_int][0].properties["tvsn"])
                        else:
                            self.builder.get_object(multi_edits[atom]).set_text(self.array_of_results[result_path_int][0].properties[atom])
            self.prefilling = False

    #########################################################################################
    ## show_large_image(widget, event) show a new window with the coverArt image at large  ##
    ##      scale with scroll and zooming capabilities implemented in gtkimageviewer       ##
    #########################################################################################
    def show_large_image(self, widget, event):
        #if there's a picture to enlarge, left click, and a double click
        if self.loaded_image != None and event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            large_image_window = Gtk.Window()

            screen_width = Gdk.Screen.get_width(Gdk.Screen.get_default()) - 20
            screen_height = Gdk.Screen.get_height(Gdk.Screen.get_default()) - 30
            pixbuf_format, width, height = GdkPixbuf.Pixbuf.get_file_info(self.loaded_image)

            #if it's taller than the screen window, set max height to screen window height
            if height > screen_height:
                height = screen_height
            #if it's wider than the screen window, set max width to screen windown width
            if width > screen_width:
                width = screen_width
            #if both the height and width were larger than the screen, pick the larger
            if width == screen_width and height == screen_height:
                if width > height:
                    height = -1
                else:
                    width = -1
            #if the width was less than the screen width, but the height was larger, auto adjust width
            elif height == screen_height:
                width = -1
            #if the height was less than the screen height, but the width was larger, auto adjust height            
            elif width == screen_width:
                height = -1
            
            
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.loaded_image,width,height,True)
            image_widget = Gtk.Image.new_from_pixbuf(pixbuf)

            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_size_request(width,height)
            scrolled_window.add_with_viewport(image_widget)

            large_image_window.add(scrolled_window)
            large_image_window.show_all()

    def escape_for_bash(self, filename):
        filename = filename.replace("\\","\\\\")
        dictionary = [[" ","\ "], ["(","\("], [")","\)"], ["'","\\\'"], ["!","\!"], ["$","\$"], ["%","\%"], ["^","\^"], ["&","\&"], ["*","\*"], ["=","\="], ["[","\["], ["{","\{"], ["]","\]"], ["}","\}"], ["|","\|"], [";","\;"], [",","\,"], ['"','\\"'], ["<","\<"], [">","\>"], ["?","\?"], ["`","\`"]]
        for swap in dictionary:
            filename = filename.replace(swap[0], swap[1])
        print filename
        return filename


#TODO how do I check the duration column to make sure it's a valid entry?
#TODO rainy day feature, scroll to zoom and or panning on popup images?
#TODO delete all artwork from atoms before writing out
