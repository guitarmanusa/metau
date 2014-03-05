import gettext
from gettext import gettext as _
gettext.textdomain('metau')

import logging
logger = logging.getLogger('metau')

import subprocess, re, xml.dom.minidom, time

from os.path import expanduser
from gi.repository import Gtk

#GLOBALS
# self.filename (str)
# self.properties [str atom_name, bool editable]
# self.chapter_info [str chap_num, str chap_title, str duration(hh:mm:ss), int duration(secs)]
# self.save_chapters (bool)
# self.total_length (int)
# self.total_chapters_in_file (int)

# self.temp_info []
# self.temp_length
# self.temp_number_chapters

#METHODS
# self.set_metadata(atom_name, atom_content)
# self.load_chapters_from_filename()
# self.array_of_chapters_in_file()

class MetaData():
    def __init__(self, filename):
        self.home = expanduser("~")
        self.filename = filename
        self.save_chapters = False
        self.properties = {}
        # data in the form of [str "text", bool editable]
        # str text is the string that will be written to the atom
        # bool to_write is a boolean flag if the field is to be written

        #NOTE there is no python implementation of switch-case, best alt is to 
        #use dictionaries and lookup, define a dictionary, then for each option
        #in the atompicparsley output, look it up in the dictionary.
        # call atomicparsley, get stdout
        #TODO change this executable from home dir to executable in $PATH
        proc = subprocess.Popen([self.home + "/.metau/AtomicParsley " + self.filename + " -t"], stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        atoms = out.split("Atom ")
        if atoms[0] == '\xef\xbb\xbf':
            del atoms[0]
        if len(atoms) > 0:
            for atom in atoms:
                atom = re.sub("\xc2\xa9","",atom)
                #check if there even are any atoms in the file
                if re.search('"[\-a-zA-Z ]{3,4}"', atom) != None:
                    atom_name = re.sub('"','',re.search('"[\-a-zA-Z ]{3,4}"', atom).group(0))
                    atom_content = atom.split("contains: ")[-1]
                    atom_content = re.sub('\n$','', atom_content)
                    self.set_metadata(atom_name, atom_content)
        self.load_chapters_from_filename()

    def load_chapters_from_filename(self):
        proc = subprocess.Popen([self.home + "/.metau/list_chapters " + self.filename], stdout=subprocess.PIPE, shell=True)
        (out,err) = proc.communicate()
        lines = out.splitlines()
        index = 1;
        self.chapter_info = []
        self.total_length = 0
        try:
            chapter,duration = lines[0].split("\t")
        except ValueError:
            dialog = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "ERROR: Chapter Info Length")
            dialog.format_secondary_text("The number of user generated chapters does not match the number of chapters in the file.  Please refresh all chapter information from file to correct this error.")
            dialog.run()
            print lines
            print "Invalid MP4 file."
            dialog.destroy()
        except IndexError:
            print "Index Error."
        else:
            for line in lines:
                chapter,duration = line.split("\t")
                single_chapter_info = [str(index),chapter,time.strftime("%H:%M:%S",time.gmtime(int(duration)/1000))+"."+duration[-3]+duration[-2]+duration[-1],int(duration)]
                self.total_length += int(duration)
                self.chapter_info.append(single_chapter_info)
                index += 1
            self.total_chapters_in_file = len(self.chapter_info)

    def array_of_chapters_in_file(self):
        proc = subprocess.Popen([self.home + "/.metau/list_chapters " + self.filename], stdout=subprocess.PIPE, shell=True)
        (out,err) = proc.communicate()
        lines = out.splitlines()
        index = 1;
        self.temp_info = []
        self.temp_length = 0
        for line in lines:
            chapter,duration = line.split("\t")
            single_chapter_info = [str(index),chapter,time.strftime("%H:%M:%S",time.gmtime(int(duration)/1000))+"."+duration[-3]+duration[-2]+duration[-1],int(duration)]
            self.temp_length += int(duration)
            self.temp_info.append(single_chapter_info)
            index += 1
        self.temp_number_chapters = len(self.temp_info)

    def set_metadata(self, atom_name, atom_content):
        if atom_name == "----":
            if re.search("^\<\?xml", atom_content):
                atom_content = re.sub("\n","",atom_content)
                atom_content = re.sub("\t","",atom_content)
                keys = xml.dom.minidom.parseString(atom_content).getElementsByTagName('plist')[0].childNodes[0].childNodes
                cast_members = ""
                directors = ""
                producers = ""
                screenwriters = ""
                index = 0
                stop_index = len(keys)
                while index < stop_index:
                    if keys[index].childNodes[0].nodeValue == "cast":
                        index+=1
                        cast_dicts = keys[index].childNodes
                        for cast_member in cast_dicts:
                            cast_members += cast_member.childNodes[1].childNodes[0].nodeValue + ", "
                        cast_members = re.sub(", $","",cast_members)
                        self.properties ["cast_members"]=[cast_members,False]
                    elif keys[index].childNodes[0].nodeValue == "directors":
                        index += 1
                        directors_dict = keys[index].childNodes
                        for director in directors_dict:
                            directors += director.childNodes[1].childNodes[0].nodeValue + ", "
                        directors = re.sub(", $","",directors)
                        self.properties ["directors"]=[directors,False]
                    elif keys[index].childNodes[0].nodeValue == "producers":
                        index += 1
                        producers_dict = keys[index].childNodes
                        for producer in producers_dict:
                            producers += producer.childNodes[1].childNodes[0].nodeValue + ", "
                        producers = re.sub(", $","",producers)
                        self.properties ["producers"]=[producers,False]
                    elif keys[index].childNodes[0].nodeValue == "screenwriters":
                        index += 1
                        screenwriters_dict = keys[index].childNodes
                        for screenwriter in screenwriters_dict:
                            screenwriters += screenwriter.childNodes[1].childNodes[0].nodeValue + ", "
                        screenwriters = re.sub(", $","",screenwriters)
                        self.properties ["screenwriters"]=[screenwriters,False]
                    index += 1
            else:
                atom_content = atom_content.split("|")[1]
                self.properties ["contentRating"]=[atom_content,False]
        elif atom_name == "covr":
            #Coverart is stored in /tmp/ dir and based on input filename
            cover_art_basename = "/tmp/" + re.sub("\..{1,4}$","",self.filename).split("/")[-1]
            proc = subprocess.Popen([self.home + "/.metau/AtomicParsley " + self.filename + " -e " + cover_art_basename], stdout=subprocess.PIPE, shell=True)
            (out, err) = proc.communicate()
            cover_art = out.splitlines()[0].split(": ")[-1]
            self.properties ["coverArt"]=[cover_art,False]
        else:
            self.properties [atom_name]=[atom_content,False]
        #convert hdvd value from string to integer
        if self.properties.has_key("hdvd"):
            self.properties["hdvd"][0] = int(self.properties["hdvd"][0])
