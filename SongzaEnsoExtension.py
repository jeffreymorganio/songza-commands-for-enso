# ----------------------------------------------------------------------------
#
#   SongzaEnsoExtension.py
#
#   by Jeffrey Morgan (based on Humanized.com's SampleEnsoExtension.py)
#   http://usabilityetc.com/

#   Python Version - 2.4
#
# ----------------------------------------------------------------------------

"""
    This script implements the Songza Enso Extension for use with
    the Enso Developer Prototype Beta Product. This code is based on
    SampleEnsoExtension.py.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from SimpleXMLRPCServer import SimpleXMLRPCServer
import xmlrpclib
import socket
import time
import threading


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

# The full URL for the XML-RPC endpoint of the Enso Developer
# Prototype, which we need to connect to in order to access Enso
# services.  For the time being, this is hard-coded, but in the future
# we may use some sort of name service to look it up.
XMLRPC_ENDPOINT_URL = "http://127.0.0.1:11374"

# The TCP port that our Enso Extension's XML-RPC endpoint will be
# located on.
EXTENSION_ENDPOINT_PORT = 8620

# The IP address that our Enso Extension's XML-RPC endpoint be located
# on.
EXTENSION_ENDPOINT_ADDRESS = "127.0.0.1"

# The full URL for our Enso Extension's XML-RPC endpoint.
EXTENSION_ENDPOINT_URL = "http://%s:%d" % ( EXTENSION_ENDPOINT_ADDRESS,
                                            EXTENSION_ENDPOINT_PORT )


# ----------------------------------------------------------------------------
# Server Thread
# ----------------------------------------------------------------------------

class ServerThread(threading.Thread):
    """
    Simple thread that encapsulates the running of the server that
    hosts our Enso Extension's XML-RPC endpoint.
    """

    def __init__( self, address ):
        threading.Thread.__init__( self )
        self._rpcServer = None
        self._stop = False
        self._address = address

    def run( self ):
        self._rpcServer = SimpleXMLRPCServer( self._address )

        # We want to set the timeout so that we can CTRL-C out of the
        # server on Windows machines.  Windows won't let keyboard
        # interrupts kick a process out of a socket system call, so we
        # have to listen for incoming connections in 1-second
        # "chunks".
        self._rpcServer.socket.settimeout( 1.0 )

        self._rpcServer.register_instance( EnsoExtensionMethods() )
        while not self._stop:
            self._rpcServer.handle_request()

    def stop( self ):
        self._stop = True

class EnsoExtensionMethods( object ):
    """
    Methods for our Enso Extension's XML-RPC endpoint, which implement
    the Enso Extension API.  Every public method here (i.e., every
    method that doesn't start with an underscore character) is a
    required method that must be implemented by all Enso Extensions,
    which Enso will call into when an Extension's services are
    required.
    """

    def __init__( self ):
        self.enso = xmlrpclib.ServerProxy( XMLRPC_ENDPOINT_URL )

    def callCommand( self, commandName, postfix ):
        """
        Extension API method that is called whenever an Enso user has
        executed a command that our Extension implements.

        This method must complete as soon as possible, because it is
        currently executed synchronously by Enso.

        'commandName' is the full name of the command that is to be
        run.

        'postfix' is the postfix (i.e., argument) that the user has
        specified for the command.  For instance, in the 'order
        {food}' command, this will be a string representing the type
        of food the end-user wants to order.  If a postfix is not
        specified or not applicable to a command, this will be an
        empty string.
        """

        if commandName == "songza list {song list}":
            self.__songzaList( postfix )
        elif commandName == "songza playlist":
            self.__songzaPlaylist()
        else:
            raise AssertionError( "Unknown command name: %s" % \
                                  commandName )

        # The Enso Developer Prototype doesn't look at this return
        # value, but we can't return None because it's not part of the
        # XML-RPC specification, so we'll return True instead.
        return True


    class AbstractSongzaCommand( threading.Thread ):

        def __init__( self, ensoEndpoint, commandPostfix="" ):

            # initialise this class by calling its parent's constructor
            threading.Thread.__init__( self )

            # store a reference to the XML-RPC endpoint of the Enso Developer
            self.ensoEndpoint = ensoEndpoint;

            # store the command postfix
            self.commandPostfix = commandPostfix


        def getXMLSongList( self, URL, tagName ):
            "Download and parse the XML feed found at URL."

            import urllib

            try:

                # retrieve the song list marked up in XML
                xmlFeed = urllib.urlopen( URL ).read()

            except IOError:

                # can't do anything without the XML feed
                xmlSongList = None

            else:
        
                from xml.dom import minidom

                from xml.parsers.expat import ExpatError

                try:
        
                    # parse the XML feed into an XML document
                    xmlSongList = minidom.parseString( xmlFeed )

                except ExpatError:

                    # can't do anything without an error-free XML feed
                    xmlSongList = None

                else:

                    try:

                        # Ensure that the feed at URL is the feed we asked for.
                        # Check that the main element of the parsed XML feed
                        # document is the same as tagName. For example, if we ask
                        # for the Songza.com public feed with the following URL:
                        # 
                        #     URL = "http://api.songza.com/1.0/public_feed/top.xml"
                        # 
                        # the main element of the parsed XML document should be
                        # <public_feed>.
                        assert xmlSongList.documentElement.tagName == tagName

                    except AssertionError:

                        # can't do anything without the correct XML feed
                        xmlSongList = None

            # return the parsed XML song list (or None if we failed)
            return xmlSongList


        def buildXHTMLSongList( self, songNodeList ):
            "Build an unordered list of links to the songs at Songza.com marked up in XHTML"

            if songNodeList == []:

                # can't mark up an empty song list so exit
                return ""
    
            # the list of XHTML links to the songs on the song list
            songLinksList = []
    
            # loop through each song node in the list of song nodes
            for songNode in songNodeList:
    
                # get the title of the song
                title = songNode.getElementsByTagName( "title" )[0].firstChild.data
    
                # get the link to the song at Songza.com
                link = songNode.getElementsByTagName( "link" )[0].firstChild.data
    
                # build an XHTML link to the song at Songza.com
                songLink = '<li><a href="%s" title="Listen to &quot;%s&quot; ' \
                    'at Songza.com">%s</a></li>' % (link, title, title)
    
                # add the XHTML link to the list of XHTML links
                songLinksList.append(songLink)
    
            # build an unordered list of song links marked up in XHTML
            xhtmlSongList = "<ul>\n" + "\n".join( songLinksList ) + "\n</ul>"
    
            # return the list of song links marked up in XHTML
            return xhtmlSongList


    def __songzaList( self, commandPostfix ):
        """
        Implementation of the 'songza list {song list}' command:

            songza list top
                returns the most played songs at Songza.com

            songza list featured
                returns the featured songs at Songza.com

        Both commands insert an unordered list of links to the songs at
        Songza.com marked up in XHTML.

        For more information about the 'songza list {song list}' command, visit
            http://www.ensowiki.com/wiki/index.php?title=Songza
        """

        class SongzaListCommand( EnsoExtensionMethods.AbstractSongzaCommand ):

            def __init__( self, ensoEndpoint, commandPostfix ):

                # initialise this class by calling its parent's constructor
                EnsoExtensionMethods.AbstractSongzaCommand.__init__( \
                    self, ensoEndpoint, commandPostfix )


            def run( self ):
                "Execute the 'songza list {song list}' command on a separate thread"

                if self.commandPostfix == '':

                    # display 'no song list' message
                    self.ensoEndpoint.enso.displayMessage( "<p>No song list!</p>" )

                    # can't do anything without the postfix so exit
                    return

                # display 'fetching' message
                self.ensoEndpoint.enso.displayMessage( \
                    "<p>Fetching song list...</p><caption>from Songza.com</caption>" )

                # URL of the Songza.com XML public feed
                URL = "http://api.songza.com/1.0/public_feed/%s.xml" % self.commandPostfix

                # download and parse the XML feed
                xmlSongList = self.getXMLSongList( URL, "public_feed" )

                if xmlSongList == None:

                    # display 'problem downloading playlist' message
                    self.ensoEndpoint.enso.displayMessage( \
                        "<p>Couldn't download song list</p>" \
                        "<caption>from Songza.com</caption>" )

                    # can't do anything without the XML song list so exit
                    return

                # get the name of the song list from the XML document
                # (the name of the song list is stored in the <name> tag)
                songListName = xmlSongList.getElementsByTagName( "name" )[0].firstChild.data

                # get a list of song DOM nodes from the XML document
                # (each song is stored in a <song> tag)
                songNodeList = xmlSongList.getElementsByTagName( "song" )

                # build the XHTML song list
                xhtmlSongList = self.buildXHTMLSongList( songNodeList )

                # insert the XHTML song list
                self.ensoEndpoint.enso.insertUnicodeAtCursor( \
                    xhtmlSongList, "songza list {song list}" )

                # tell the user which song list was retrieved
                self.ensoEndpoint.enso.displayMessage( \
                    "<p>%s</p><caption>at Songza.com</caption>" % songListName )

                # release the memory used by the XML document
                xmlSongList.unlink()


        # create the 'songza list {song list}' command as a separate thread
        command = SongzaListCommand( self, commandPostfix )

        # execute the command
        command.start()


    def __songzaPlaylist( self ):
        """
        Implementation of the 'songza playlist' command:

        Insert an unordered list of links to the songs on the selected
        Songza user's playlist marked up in XHTML.

        For more information about the 'songza playlist' command, visit
            http://www.ensowiki.com/wiki/index.php?title=Songza
        """

        class SongzaPlaylistCommand( EnsoExtensionMethods.AbstractSongzaCommand ):

            def __init__( self, ensoEndpoint ):

                # initialise this class by calling its parent's constructor
                EnsoExtensionMethods.AbstractSongzaCommand.__init__( \
                    self, ensoEndpoint )


            def isValidSongzaUsername( self, songzaUsername ):
                """
                Check if songzaUsername is a syntactically valid username.
                Valid usernames have between 3 and 16 alphanumeric characters.
                (This method does not check if username exists.)
                """

                import re

                # validation pattern that matches between 3 and 16 alphanumeric
                # characters (ignoring leading and trailing spaces)
                pattern = "^\s*\w{3,16}\s*$"

                # test the username against the validation pattern
                isValid = re.search( pattern, songzaUsername ) != None

                return isValid


            def run( self ):
                "Execute the 'songza playlist' command on a separate thread"

                # get the Songza user's username from the current selection
                songzaUsername = self.ensoEndpoint.enso.getUnicodeSelection()
        
                if len( songzaUsername ) == 0:
        
                    # display 'no Songza username selected' message
                    self.ensoEndpoint.enso.displayMessage( \
                        "<p>No Songza username selected!</p>" )

                    # can't do anything without a username so exit
                    return

                if not self.isValidSongzaUsername( songzaUsername ):

                    # display 'invalid Songza username' message
                    self.ensoEndpoint.enso.displayMessage( \
                        "<p>Invalid Songza username selected!</p>" \
                        "<caption>Songza.com usernames have between " \
                        "3 and 16 alphanumeric characters</caption>" )
        
                    # can't do anything without a valid username so exit
                    return

                # remove leading and trailing spaces from the username
                songzaUsername = songzaUsername.strip();
    
                # display 'fetching' message
                self.ensoEndpoint.enso.displayMessage( \
                    "<p>Fetching %s's playlist...</p>" \
                    "<caption>from Songza.com</caption>" % songzaUsername )
    
                # URL of the Songza.com XML feed
                URL = "http://api.songza.com/1.0/feed/%s.xml" % songzaUsername

                # download and parse the XML feed
                xmlSongList = self.getXMLSongList( URL, "feed" )

                if xmlSongList == None:

                    # display 'problem downloading playlist' message
                    self.ensoEndpoint.enso.displayMessage( \
                        "<p>Couldn't download %s's playlist</p>" \
                        "<caption>from Songza.com</caption>" % songzaUsername )

                    # can't do anything without the XML song list so exit
                    return
    
                # get a list of song DOM nodes from the XML document
                # (each song is stored in a <song> tag)
                songNodeList = xmlSongList.getElementsByTagName( "song" )
    
                if songNodeList == []:
    
                    # display 'empty playlist' message
                    self.ensoEndpoint.enso.displayMessage( \
                        "<p>No songs on %s's playlist</p>" \
                        "<caption>at Songza.com</caption>" % songzaUsername )
    
                else:
    
                    # build the XHTML song list
                    xhtmlSongList = self.buildXHTMLSongList( songNodeList )
    
                    # insert the XHTML song list
                    self.ensoEndpoint.enso.insertUnicodeAtCursor( \
                        xhtmlSongList, "songza playlist" )
    
                    # tell the user about the playlist
                    self.ensoEndpoint.enso.displayMessage(
                        "<p>Songs on %s's playlist</p>" \
                        "<caption>at Songza.com</caption>" % songzaUsername )

                # release the memory used by the XML document
                xmlSongList.unlink()


        # create the 'songza playlist' command as a separate thread
        command = SongzaPlaylistCommand( self )

        # execute the command
        command.start()


if __name__ == "__main__":
    # For some reason we need to do this or else we'll get annoying
    # exceptions along the lines of "the socket operation could not
    # complete without blocking."
    socket.setdefaulttimeout( 10.0 )

    print "Starting XML-RPC server."
    serverThread = ServerThread( (EXTENSION_ENDPOINT_ADDRESS,
                                  EXTENSION_ENDPOINT_PORT) )
    serverThread.start()

    try:
        enso = xmlrpclib.ServerProxy( XMLRPC_ENDPOINT_URL )

        # Register the 'songza list {song list}' command with the Enso Developer Prototype.
        enso.registerCommand(
            EXTENSION_ENDPOINT_URL,
            "songza list {song list}",
            "Retrieves song lists from Songza.",
            "<p>Retrieves song lists from Songza.</p>",
            "bounded"
            )
        # Set valid postfixes for the 'songza list {song list}' bounded command.
        # This function can be called at any time, if and when the
        # list of valid postfixes changes.
        enso.setCommandValidPostfixes( EXTENSION_ENDPOINT_URL,
                                       "songza list {song list}",
                                       ["top", "featured"] )

        # Register the 'songza playlist' command with the Enso Developer Prototype.
        enso.registerCommand(
            EXTENSION_ENDPOINT_URL,
            "songza playlist",
            "Retrieves a Songza user's playlist from Songza.",
            "<p>Retrieves a Songza user's playlist from Songza.</p>",
            "none"
            )

        try:
            # Now just block for input while our server thread
            # listens for incoming connections from Enso.
            print "press enter to exit."
            raw_input()
        finally:
            # Before we leave, let Enso know that we're not offering
            # our commands anymore.
            enso.unregisterCommand( EXTENSION_ENDPOINT_URL,
                                    "songza list {song list}" )
            enso.unregisterCommand( EXTENSION_ENDPOINT_URL,
                                    "songza playlist" )

    finally:
        print "Shutting down XML-RPC server."
        serverThread.stop()
