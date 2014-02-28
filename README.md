metau
=====

Linux port of MetaX, a GUI interface for the AtomicParsley mp4 metadata editor.

Installing/running:

This program was developed using the Ubuntu(c) Quickly API.  Once I realized the limitations this presented I was too far into the development to throw it all out and start over again.  If anyone would care to port this to C that would be fantastic and you have my encouragement.



Make sure to install the "quickly" package.  Then change directories into the "metau" directory and run:

quickly run



NOTE:  This program is still under development and should be considered in alpha stages.  The author is not responsible for any data, financial or personal loss that may be incurred by running the aforementioned software.  Use at your own risk.

I would HIGHLY recommend making a copy of the video/music file that you would like to edit metadata of and do a test run on that file before you commit the changes to your permanent copy.

KNOWN BUGS:
Writing the "Actors", "Director", "Producer", and "Screenwriter" tags to the file is not yet implemented.  Apple(c) uses a form of XML to hold multiple names in these fields and I just haven't had time to properly implement them.

If there is cover art associated with the file, DO NOT WRITE OUT TO THE FILE MORE THAN ONCE!!  I believe this is a bug with AtomicParsley, but it seems as though every time you write out the metadata to a file with coverart, AtomicParsley will add ANOTHER copy of the coverart the the file.  So the file will keep growing in size with extra metadata that you wouldn't expect.

DOCUMENTATION:

This is by far non-inclusive.  Please see the MetaX documentation for more information.  I am pretty pressed for time and haven't written out appropriate documentation.

Fields will not be written out to the file unless the appropriate checkboxs are marked.

If TagChimp is still up and running you should be able to search TagChimp from within the app, download the available tags and pre-load the GUI with them.

Working with chapters and the ratings requires two helper C programs using the libmp4 library.  They are "list_chapters", "write_chapters" and "write_rtng".  Please make sure these are marked executable after you pull from this repo.
