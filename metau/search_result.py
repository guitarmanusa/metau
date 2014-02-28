import gettext
from gettext import gettext as _
gettext.textdomain('metau')

import logging
logger = logging.getLogger('metau')

import xml.dom.minidom, re, htmlentitydefs

#GLOBALS

#METHODS

class search_result():
    def __init__(self, xml_result, source):
        if source == "tagchimp":
            self.properties = {}
            #TODO test if there is an imdbID, save it
            #In metauwindow, in for each search_result loop, check to see if the search_result has an imdbID
            #if any search_results have an imdbID, spawn a fetch of imdb info

            #find the tagChimpID
            #self.properties["tagChimpID"] = int(xml_result.getElementsByTagName('tagChimpID')[0].childNodes[0].nodeValue)
 
            movieTags = xml_result.getElementsByTagName('movieTags')[0]

            #handle <info></info> tag
            if len(movieTags.getElementsByTagName('info')[0].childNodes) > 35:
                info = movieTags.getElementsByTagName('info')
                if len(info[0].childNodes[1].childNodes) > 0:
                    self.properties["stik"] = self.unquotehtml(info[0].childNodes[1].childNodes[0].nodeValue)
                if len(info[0].childNodes[3].childNodes) > 0:
                    self.properties["nam"] = self.unquotehtml(info[0].childNodes[3].childNodes[0].nodeValue)
                self.handle_releaseDate(info[0])
                if len(info[0].childNodes[13].childNodes) > 0:
                    self.properties["gen"] = self.unquotehtml(info[0].childNodes[13].childNodes[0].nodeValue)
                if len(info[0].childNodes[17].childNodes) > 0:
                    self.properties["contentRating"] = self.unquotehtml(info[0].childNodes[17].childNodes[0].nodeValue)
                if len(info[0].childNodes[19].childNodes) > 0:
                    #TODO fix
                    director_string = ""
                    stop_index = len(info[0].childNodes[19].childNodes)
                    index = 1
                    while index < stop_index:
                        if len(info[0].childNodes[19].childNodes[index].childNodes) > 0:
                            director_string += self.unquotehtml(info[0].childNodes[19].childNodes[index].childNodes[0].nodeValue) + ", "
                        index += 2
                    if director_string != "":
                        director_string = re.sub(", $","",director_string)
                        self.properties["directors"] = director_string
                if len(info[0].childNodes[21].childNodes) > 0:
                    producer_string = ""
                    #TODO FIX
                    stop_index = len(info[0].childNodes[21].childNodes)
                    index = 1
                    while index < stop_index:
                        if len(info[0].childNodes[21].childNodes[index].childNodes) > 0:
                            producer_string += self.unquotehtml(info[0].childNodes[21].childNodes[index].childNodes[0].nodeValue) + ", "
                        index += 2
                    if producer_string != "":
                        producer_string = re.sub(", $","",producer_string)
                        self.properties["producers"] = producer_string
                if len(info[0].childNodes[23].childNodes) > 0:
                    screenwriter_string = ""
                    #TODO FIX
                    stop_index = len(info[0].childNodes[23].childNodes)
                    index = 1
                    while index < stop_index:
                        if len(info[0].childNodes[23].childNodes[index].childNodes) > 0:
                            screenwriter_string += self.unquotehtml(info[0].childNodes[23].childNodes[index].childNodes[0].nodeValue) + ", "
                        index += 2
                    if screenwriter_string != "":
                        screenwriter_string = re.sub(", $","",screenwriter_string)
                        self.properties["screenwriters"] = screenwriter_string
                if len(info[0].childNodes[25].childNodes) > 0:
                    actor_string = ""
                    #TODO FIX
                    stop_index = len(info[0].childNodes[25].childNodes)
                    index = 1
                    while index < stop_index:
                        if len(info[0].childNodes[25].childNodes[index].childNodes) > 0:
                            actor_string += self.unquotehtml(info[0].childNodes[25].childNodes[index].childNodes[0].nodeValue) + ", "
                        index += 2
                    if actor_string != "":
                        actor_string = re.sub(", $","",actor_string)
                        self.properties["cast_members"] = actor_string
                if len(info[0].childNodes[27].childNodes) > 0:
                    self.properties["desc"] = self.unquotehtml(info[0].childNodes[27].childNodes[0].nodeValue)
                if len(info[0].childNodes[29].childNodes) > 0:
                    self.properties["ldes"] = self.unquotehtml(info[0].childNodes[29].childNodes[0].nodeValue)
                if len(info[0].childNodes[31].childNodes) > 0:
                    self.properties["rtng"] = self.unquotehtml(info[0].childNodes[31].childNodes[0].nodeValue)
                if len(info[0].childNodes[33].childNodes) > 0:
                    self.properties["cprt"] = self.unquotehtml(info[0].childNodes[33].childNodes[0].nodeValue)
                if len(info[0].childNodes[35].childNodes) > 0:
                    self.properties["cmt"] = self.unquotehtml(info[0].childNodes[35].childNodes[0].nodeValue)
                if len(info[0].childNodes[37].childNodes) > 0:
                    artist_string = ""
                    stop_index = len(info[0].childNodes[37].childNodes)
                    index = 1
                    #TODO FIX
                    while index < stop_index:
                        if len(info[0].childNodes[37].childNodes[index].childNodes) > 0:
                            artist_string += self.unquotehtml(info[0].childNodes[37].childNodes[index].childNodes[0].nodeValue) + ", "
                        index += 2
                    if artist_string != "":
                        self.properties["ART"] = re.sub(", $","",artist_string)

            #handle <television></television> tag
            if len(movieTags.getElementsByTagName('television')[0].childNodes) > 13:
                television = movieTags.getElementsByTagName('television')
                if len(television[0].childNodes[1].childNodes) > 0:
                    self.properties["tvsh"] = self.unquotehtml(television[0].childNodes[1].childNodes[0].nodeValue)
                if len(television[0].childNodes[3].childNodes) > 0:
                    self.properties["tvsn"] = self.unquotehtml(television[0].childNodes[3].childNodes[0].nodeValue)
                if len(television[0].childNodes[7].childNodes) > 0:
                    self.properties["tves"] = self.unquotehtml(television[0].childNodes[7].childNodes[0].nodeValue)
                if len(television[0].childNodes[9].childNodes) > 0:
                    self.properties["tven"] = self.unquotehtml(television[0].childNodes[9].childNodes[0].nodeValue)
                if len(television[0].childNodes[13].childNodes) > 0:
                    self.properties["tvnn"] = self.unquotehtml(television[0].childNodes[13].childNodes[0].nodeValue)

            #handle <sorting></sorting>
            if len(xml_result.getElementsByTagName('sorting')[0].childNodes) > 0:
                sorting = xml_result.getElementsByTagName('sorting')
                if len(sorting[0].childNodes[1].childNodes) > 7:
                    self.properties["sonm"] = self.unquotehtml(sorting[0].childNodes[1].childNodes[0].nodeValue)
                if len(sorting[0].childNodes[3].childNodes) > 0:
                    self.properties["soaa"] = self.unquotehtml(sorting[0].childNodes[3].childNodes[0].nodeValue)
                if len(sorting[0].childNodes[5].childNodes) > 0:
                    self.properties["soal"] = self.unquotehtml(sorting[0].childNodes[5].childNodes[0].nodeValue)
                if len(sorting[0].childNodes[7].childNodes) > 0:
                    self.properties["sosn"] = self.unquotehtml(sorting[0].childNodes[7].childNodes[0].nodeValue)

            #deal with <track></track> tag
            if len(movieTags.getElementsByTagName('track')[0].childNodes) > 3:
                track = movieTags.getElementsByTagName('track')
                if len(track[0].childNodes[1].childNodes) > 0:
                    if len(track[0].childNodes[3].childNodes) > 0:
                        self.properties["trkn"] = self.unquotehtml(track[0].childNodes[1].childNodes[0].nodeValue + " of " + track[0].childNodes[3].childNodes[0].nodeValue)
                    else:
                        self.properties["trkn"] = self.unquotehtml(track[0].childNodes[1].childNodes[0].nodeValue)

            #set coverArt, by default choose the larger coverArt image
            if len(movieTags.getElementsByTagName('coverArtLarge')[0].childNodes) > 0:
                self.properties["coverArt"] = self.unquotehtml(movieTags.getElementsByTagName('coverArtLarge')[0].childNodes[0].nodeValue)
            
                print self.unquotehtml(movieTags.getElementsByTagName('coverArtLarge')[0].childNodes[0].nodeValue)
 
            elif len(movieTags.getElementsByTagName('coverArtSmall')[0].childNodes) > 0:
                self.properties["coverArt"] = self.unquotehtml(movieTags.getElementsByTagName('coverArtSmall')[0].childNodes[0].nodeValue)

                print self.unquotehtml(movieTags.getElementsByTagName('coverArtSmall')[0].childNodes[0].nodeValue)

            if len(xml_result.getElementsByTagName('movieChapters')[0].childNodes) > 0:
                movieChapters = xml_result.getElementsByTagName('movieChapters')
                if len(movieChapters[0].childNodes) > 0:
                    self.properties["total_chapters"] = self.unquotehtml(movieChapters[0].childNodes[1].childNodes[0].nodeValue)
                self.properties["chapter_info"] = []
                if self.properties.has_key("total_chapters"):
                    index = 3
                    stop_index = int(self.properties["total_chapters"])*2+3
                    while index < stop_index:
                        self.properties["chapter_info"].append([self.unquotehtml(movieChapters[0].childNodes[index].childNodes[1].childNodes[0].nodeValue), self.unquotehtml(movieChapters[0].childNodes[index].childNodes[3].childNodes[0].nodeValue), self.unquotehtml(movieChapters[0].childNodes[index].childNodes[5].childNodes[0].nodeValue)])
                        index += 2

            #for key in self.properties:
            #    print key,":",self.properties[key]
            
    def handle_releaseDate(self, info_xml):
        if len(info_xml.childNodes[5].childNodes) > 0:
            self.releaseDate = self.unquotehtml(info_xml.childNodes[5].childNodes[0].nodeValue)
        if len(info_xml.childNodes[7].childNodes) > 0:
            self.releaseYear = self.unquotehtml(info_xml.childNodes[7].childNodes[0].nodeValue)
        if len(info_xml.childNodes[9].childNodes) > 0:
            self.releaseMonth = self.unquotehtml(info_xml.childNodes[9].childNodes[0].nodeValue)
        if len(info_xml.childNodes[11].childNodes) > 0:
            self.releaseDay = self.unquotehtml(info_xml.childNodes[11].childNodes[0].nodeValue)
        if hasattr(self, 'releaseYear') and hasattr(self, 'releaseMonth') and hasattr(self, 'releaseDay'):
            self.properties["day"] = self.releaseYear + "-" + self.releaseMonth + "-" + self.releaseDay
        elif hasattr(self,'releaseDate'):
            self.properties["day"] = self.releaseDate

    #code snippet found at https://groups.google.com/forum/?fromgroups=#!topic/comp.lang.python/f5ZyMoI3b4w
    def convertentity(self, m):
        """Convert a HTML entity into normal string (ISO-8859-1)"""
        if m.group(1)=='#':
            try:
                return chr(int(m.group(2)))
            except ValueError:
                return '&#%s;' % m.group(2)
        try:
            return htmlentitydefs.entitydefs[m.group(2)]
        except KeyError:
            return '&%s;' % m.group(2)

    def unquotehtml(self, s):
        """Convert a HTML quoted string into normal string (ISO-8859-1).
       
        Works with &#XX; and with &nbsp; &gt; etc."""
        return re.sub(r'&(#?)(.+?);',self.convertentity,s)
