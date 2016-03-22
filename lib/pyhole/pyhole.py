#!/usr/bin/env python3

# pyhole - a clone of the Pi-hole DNS adblocker, written in Python.
# pyhole  (c) 2016 by ryt51V
# Pi-Hole (c) 2015, 2016 by Jacob Salmela

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# For running system commands
import os
# For getting our invoked arguments.
import sys
# For validating user provided IPs.
import ipaddress
# For managing our conf file
import configparser
# For finding out the current user.
import getpass

########################
###     Variables    ###
########################

# These should already exist if installed by the .deb package.
config_dir = '/etc/pyhole'
share_dir  = '/usr/share/pyhole'
var_dir    = '/var/lib/pyhole'

conf_file_path = os.path.join(config_dir, 'pyhole.conf')

adlists_default = os.path.join(config_dir, 'adlists.default')
adlists_file    = os.path.join(config_dir, 'adlists.list')

whitelist_file  = os.path.join(config_dir, 'whitelist.txt')
blacklist_file  = os.path.join(config_dir, 'blacklist.txt')

hosts_file      = os.path.join(var_dir   , 'gravity.list' )

########################
##  Helper Functions  ##
########################

def valid_ip(ip):
    """Return True if an IP is valid, false otherwise."""
    try:
        ipaddress.ip_address(ip)
        return True
    except:
        return False
    #end except
#end def valid_ip(ip):

def valid_port(port):
    """Return True if a port is valid, false otherwise."""
    try:
        port_int = int(port)
        return port_int in range(1,65536)
    except:
        return False
    #end except:
#end def valid_port(port):

########################
###     Conf file    ###
########################

def read_config():
    """Read the pyhole config from file."""
    global config
    global conf_file_path
    
    # Reinitialise the config object.
    config = configparser.ConfigParser()
    
    # Note: Reading the config does not seem to fail if it does not exist.
    config.read(conf_file_path)
#end def read_config():

def write_config():
    """Write the pyhole config to file."""
    global config
    global conf_file_path
    
    with open(conf_file_path, 'w') as conf_file:
        config.write(conf_file)
    #end with
    
#end def write_config:

# Read the config
read_config()

########################
###       Sudo       ###
########################

def sudo_root():
    # If not root, rerun as root with sudo.
    if os.geteuid() != 0:
        print("Rerunning as root with sudo...")
        os.execvp("sudo", ["sudo"] + sys.argv)
    #end if os.geteuid() != 0:
#end def sudo_root():

def sudo_pyhole():
    if getpass.getuser() != "pyhole":
        print("Rerunning as pyhole with sudo...")
        os.execvp("sudo", ["sudo", "--user=pyhole"] + sys.argv)
    #end if getpass.getuser() != "pyhole":
#end def sudo_pyhole():

########################
###      Gravity     ###
########################

def gravity_collapse(adlists_file):
    """Determine our adlist sources, and output as a list."""
    
    with open(adlists_file, 'rt') as f:
        # We need all lines that are not blank and are not comments.
        
        # Get all lines with trailing whitespace stripped.
        lines = (line.rstrip() for line in f) 
        # Get all lines that
        #   (a) Are not blank, AND
        #   (b) Do not begin with a hash (after any leading whitespace).
        sources = list(
                        line for line in lines if (line and not line.lstrip().startswith('#') )
                      )
        #sources = list(for line in lines if line and not line.lstrip().startswith('#'))
    #end with open(adlist_file, 'rt') as f:
    
    return sources
#end def gravity_collapse(adlists_file):

# Note:
#   We're going to be handling a large number of domains here,
#   so we save a lot of stuff in files rather than in memory
#   so that we're not wasting RAM.

def gravity_download_source(url : str, destination_filename : str, headers = {}, post_values = {} ):
    """Download the source to a file, using any headers or POST data required."""
    # Unlike curl in the original Pi-Hole, with urllib we don't seem to have
    # the facility to download filex newer than xyz datetime.
    # So empty files here are leaning more towards errors.
    
    # We will first save to a temp file, so that if our result is an empty file
    # then we won't overwrite an old nonempty file.  So let's initialise one.
    # This type won't be automatically deleted upon close.
    temp_file = tempfile.mkstemp()[1]
    
    # PROTIP: Below, Replace post_values with True to get
    # an HTTP error with some providers.  Useful for testing
    if post_values:
        data = urllib.parse.urlencode(post_values)
        data = data.encode('ascii')
    else:
        data = None
    #end else:
    req = urllib.request.Request(url, data, headers)
    with urllib.request.urlopen(req, timeout = 20) as response, open (temp_file, 'wb') as f:
        f.write( response.read() )
    #end with
    
    if os.path.getsize(temp_file) == 0:
        nonempty = False
    else:
        nonempty = True
        shutil.copyfile(temp_file, destination_filename)
    #end if
    
    # Delete the temporary file
    os.remove(temp_file)
    
    return nonempty
    
#end def gravity_download_source(url : str, destination_filename : str, headers = {}, post_values = {} ):

def gravity_spinup(sources : list):
    """Download each source to a file."""
    print(":::")
    i = 0
    sources_out = []
    for s in sources:
        
        # Get just the domain name itself.
        domain = urllib.parse.urlparse(s).netloc
        
        # Generate our save filename.
        basename = "list.{0}.{1}.domains".format( i, domain )
        filename = os.path.join( pyhole.var_dir, basename )
        
        # Our default headers and post values...
        headers = {
                        'User-Agent' : 'Mozilla/10.0'
                  }
        post_values = {}
        # Handle our special cases
        if "adblock.mahakala.is" in s:
            headers = {
                            'User-Agent'    : 'Mozilla/5.0 (X11; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0',
                            'Referer'       : 'http://forum.xda-developers.com/'
                      }
        elif "pgl.yoyo.org" in s:
            post_values = {
                                'mimetype'      : 'plaintext',
                                'hostformat'    : 'hosts'
                          }
        #end elif
        
        print("::: Getting {0} list...".format(domain) , end='')
        
        tryold = False
        success = False
        
        try:
            nonempty = gravity_download_source( s, filename, headers, post_values)
        except urllib.error.HTTPError as inst:
            print("encountered error {0} {1}.  ".format(inst.code, inst.reason), end='' )
            tryold = True
        except:
            print("encountered an unknown error: {0}.  ".format(sys.exc_info()[0]), end='' )
            tryold = True
        else:
            if nonempty == False:
                print("downloaded an empty file.  ", end='')
                tryold = True
            else:
                print("successful!")
                success = True
            #end else
        #end else
        
        if tryold == True:
            # But do we already have an older version of this file?
            nonempty_oldfile = False
            try:
                nonempty_oldfile = (os.path.getsize(filename) >= 0)
            except:
                pass
            #end except
            
            if nonempty_oldfile:
                print("Using previous download.")
                success = True
            else:
                print("No previous download.")
            #end else
            
        #end if
        
        if success == True:
            # Add to sources_out a 2-tuple of the source and filename.
            sources_out.append( ( s, filename ) )
        #end if
        
        i = i + 1
    #end for s in sources:
    
    return sources_out
#end def gravity_spinup(sources : list):

def gravity_advanced(source_files, destination_filename):
    """Read all of the source files, remove all comments, and outputs just the domain."""
    
    print("::: Aggregating list of domains and formatting to remove comments...")
    
    # This looks inefficient but runs surprisingly fast!
    with open (destination_filename, 'wt') as outfile:
        for s in source_files:
            with open(s, 'rt') as infile:
                for line in infile:
                    # Remove any trailing comments - from the comment character to the end of the line
                    line = line.partition('#')[0]
                    line = line.partition('/')[0]
                    # Remove all leading and trailing whitespace.
                    # Note that this includes line breaks.
                    line = line.strip()
                    # If it's not blank at this point...
                    if line:
                        # If we split it, does it have more than one component?
                        split_line = line.split()
                        if len(split_line) >= 2:
                            # If so then the domain has to be the second component.
                            outfile.write(split_line[1])
                        else:
                            # If not then it has to be the only component.
                            outfile.write(split_line[0])
                        #end else
                        # Put back in that line break.
                        outfile.write("\n")
                    #end if
                #end for
            #end with
        #end for
    #end with
    
#end def gravity_advanced(source_files, destination_filename):

def gravity_unique( source_filename, destination_filename ):
    """Sort and remove duplicates"""
    print("::: Removing duplicate domains....")
    # The 'sort' binary still seems the best way to do this.
    cmd = 'sort -u "{0}" > "{1}"'.format(source_filename, destination_filename)
    os.system(cmd)
    
#end def gravity_unique( infile, outfile ):

def domain_hostformat(addr, domain):
    return "{0} {1}".format(addr,domain)
#end def add_hostname(str):

def gravity_hostformat( source_filename, destination_filename, ipv4_addr = None, ipv6_addr = None ):
    print("::: Formatting domains into a HOSTS file...")
    with open(source_filename, 'rt') as infile, open (destination_filename, 'wt') as outfile:
        # Add a dummy record to the start
        dummy = ""
        if ipv4_addr:
            dummy += domain_hostformat(ipv4_addr, "pyhole.isworking.ok")
            dummy += "\n"
        #end if
        if ipv6_addr:
            dummy += domain_hostformat(ipv6_addr, "pyhole.isworking.ok")
            dummy += "\n"
        #end if
        outfile.write(dummy)
        for line in infile:
            # Note that we don't need /n here as it's already included.
            if ipv4_addr:
                outfile.write( domain_hostformat(ipv4_addr, line) )
            #end if
            if ipv6_addr:
                outfile.write( domain_hostformat(ipv6_addr, line) )
            #end if
        #end for
    #end with
#end def gravity_hostformat( source_filename, destination_filename ):

def gravity_blackbody( dir, source_files ):
    """Delete all list.*.*.domains files are not in our source_files list, and any pyhole.* files."""
    glob_string = os.path.join(dir, 'list.*.*.domains')
    files = glob.glob(glob_string)
    for f in files:
        if not f in source_files:
            os.remove(f)
        #end if
    #end for
#end def gravity_blackbody( dir, source_files )

def gravity_reload():
    print(":::")
    print("::: Refreshing lists in dnsmasq...")
    # Not yet implemented.
#end def gravity_reload():


