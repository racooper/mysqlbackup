#!/usr/bin/perl
# mysql_backup.cgi
###################################################################################
# POD Documentation

=head1 PROGRAM NAME AND AUTHOR

        MySQL Backup v3.4
        by Peter Falkenberg Brown
        peterbrown@worldcommunity.com
        http://worldcommunitypress.com/opensource
        Build Date: August 19, 2011

=PURPOSE

        Backs up mysql data safely, using
        'mysqldump', 'select to outfile' or 'normal record selection'.

        This is my attempt :-) to provide a reasonably
        full featured MySQL backup script that can be
        run from:

        1. Linux Crontab or Windows Scheduler
        2. the shell or command prompt

        3. the web (with password protection)
        (Note that I don't recommend running it from the web
        because of permission issues - however, some users
        don't have shell access. It depends upon the security
        level of your data.

        It now works from both Linux and Windows.
        See URLs at the end about where to get
        WINDOWS VERSION OF UNIX UTILITIES.

        It provides options to backup all of the databases and tables
        in one particular host, with exception lists.

        It now has the ability to select a variety of options
        for the tar and gzip functions, including using the
        tar -z switch, using bzip2 and piping data through gzip/bzip2.
        It also deletes text files in between tar and gzip, to save space.

        It also works around the sql wildcard glitch with
        underlines (_), in table names, by not using mysqlshow
        to get table names. I did this, because mysqlshow db %
        didn't work under MySQL v3.22.20a, and I wasn't able to
        determine when the % method came into being (under which
        version.) So, in order to make things work for earlier
        versions, I used 'show tables'.
        (I still use mysqlshow for database names.)

=COPYRIGHT

        Copyright 2000-2011 Peter Falkenberg Brown
        The World Community Press
        This program complies with the GNU GENERAL PUBLIC LICENSE
        and is released as "Open Source Software".
        NO WARRANTY IS OFFERED FOR THE USE OF THIS SOFTWARE

=BUG REPORTS AND SUPPORT

        Send bug reports to peterbrown@worldcommunity.com.

=OBTAINING THE LATEST VERSION

        ==> Get the most recent version of this program at:
            http://worldcommunitypress.com/opensource

=TODO

        - adding multiple recipient support

        Email your feedback and ideas to:
        peterbrown@worldcommunity.com

=VERSION HISTORY
 (See the bottom of the file, since the version notes are getting longer.)

=cut

###################################################################################

use DBI;
use POSIX qw(strftime);
use Time::Local;
use Cwd;
use File::Path;

#.............................................................
# if you're not going to use the script from the web
# you can comment out the next 3 CGI lines, if you don't have
# CGI.pm installed.

use CGI qw(:all -private_tempfiles escapeHTML unescapeHTML);
use CGI::Carp qw(fatalsToBrowser cluck);
$q = new CGI;

#.............................................................

no strict 'refs';

# MANDATORY VARIABLE SET UP SECTION
# ..................................

# Note: the file is ALWAYS save locally, whether or not
# you set ftp_backup and/or email_backup to 'yes'

$ftp_backup                  = 'no';
# use Net::FTP;
                             # set $ftp_backup to 'yes' or 'no'.
                             # => NOTE
                             # If you set it to 'yes',
                             # you'll need to install Net::FTP

                             # If you don't install Net::FTP,
                             # you MUST place a comment (#) in front of
                             # the 'use Net::FTP' line above

                             # You'll also have to set the variables
                             # for ftp host, etc (below)

$email_backup                = 'no';
# use MIME::Lite;
                             # set $email_backup to 'yes' or 'no'
                             # => NOTE
                             # If you set it to 'yes'
                             # you'll need to install MIME::Lite

                             # If you don't install MIME::Lite,
                             # you MUST place a comment (#) in front of
                             # the 'use MIME::Lite' line above

                             # See Windows Users Note below
                             # about MIME::Lite (You need it.)

                             # Go to search.cpan.org to get the libs.

# Microsoft Windows options
# ..................................

# use Net::SMTP;
                             # COMMENT out the use Net::SMTP line
                             # if you're not using smtp

                             # NOTE for Windows Users:
                             # - adjust the $find_commands section below
                             #   (set $find_commands to no)
                             # - you'll need to install Windows versions
                             #   of the utilities listed in the find_commands
                             #   section - see the urls at the end of the file

                             # - note also that your windows system may require that
                             #   libintl-2.dll and libiconv-2.dll be installed in
                             #   your c:\windows\system directory (for tar, I
                             #   believe) I downloaded "libintl-0.11.5-2-bin.exe",
                             #   from gnuwin32.sourceforge.net/packages/libintl.htm
                             #   and went through the installation, but then had to
                             #   copy the two files by hand from their default
                             #   installation directory, over to the
                             #   \windows\system directory.
                             #   -- don't bother installing them unless you receive
                             #      an error message - I only tested this on Win98.

                             # - set $chmod_backup_file to 'no'
                             # - set the smtp items in this section
                             # - install MIME::Lite and uncomment the
                             #   use MIME::Lite line above
                             # - the tar z switch and the tar/gzip pipe method
                             #   don't work on Windows
                             # - the shell command length on Win98 is 127
                             #   (although you can increase it by installing 4Dos)
                             #   -- thus, for Win98, you may wish to install
                             #      your utilities in a short dir like c:\bin
                             #      and make your backup dir short also,
                             #      like c:\data
                             #   -- For Win98 (at least) use the $max_cmd
                             #      variable to abort on commands that are
                             #      longer.

$max_cmd                     = 0;
                             # (for Windows Users, especially Win98)
                             # (for Win98 set this to '127')
                             # set this to '0' if you don't need to check the
                             # length of your shell command strings
                             # (see the ` backtick commands)

# $mailprog                    = "/var/qmail/bin/qmail-inject -h";
# $mailprog                  = '/usr/lib/sendmail -t -oi';
$mailprog                    = '/usr/sbin/sendmail -t -oi';
                             # sendmail is more common
                             # but qmail (qmail.org) is better :-).
                             # but.. qmail doesn't work on windows

$smtp_host                   = 'localhost';
                             # set only if you set send_method to 'smtp'
                             # (useful for Windows)

$send_method                 = 'sendmail';
                             # set $send_method to 'sendmail' or 'smtp';
                             # (often set to smtp for WinX)

$admin_email_to              = 'racooper@tamu.edu';
                             # the email for error and notification
                             # messages, and the email recipient
                             # of the database files.

$admin_email_from            = 'root@wiki-it.tamu.edu';

# database options
# ..................................

$web_test_database           = 'my_database';
                             # The name of your authorized database.
                             # See the notes below about logging in from the web.
                             #.....................................................
                             # Because the login must test the mysql authorization
                             # against a specific database, this new variable
                             # is required **ONLY** when logging in from the web.
                             # Use the name of ANY database for which your
                             # login username has authorized access.

                             # NOTE! This database name has NO relationship to the
                             #   -- @selected_databases and
                             #   --$process_all_databases variables
                             # You still MUST set those variables correctly.
                             # The $web_test_database var is ONLY used
                             # for an initial login test.

                             # NOTE! The user must be authorized for the
                             # test database AND the database that you place
                             # in the selected_database array
                             # If the user is NOT authorized for both,
                             # the script might pass the first login test,
                             # but fail on the specific database login,
                             # which would happen AFTER the creation of the
                             # backup directory (which is messy).

@selected_databases          = qw[];
                             # place the names of your databases here,
                             # separated by spaces, or set
                             # process_all_databases to 'yes'

$process_all_databases       = 'yes';
                             # @selected_databases is ignored if you set
                             # process_all_databases to 'yes'

                             # Many servers with virtual hosts allow you
                             # to see all of the databases while only giving
                             # you access to your own database. In that case,
                             # place the name of your database in the
                             # @selected_databases array.

                             # Someone else might want to process all of the
                             # databases, with possible exceptions. If so,
                             # place the databases to skip in the
                             # skip_databases array below.

@skip_databases              = qw[];
                             # Note: skip_databases is only parsed
                             # if process_all_databases is set to 'yes'
                             # Leave it blank if you don't want to use it., i.e:
                             # qw[];

@skip_tables                 = qw[general_log slow_log mysql\.event];
                             # skip_tables is always parsed.
                             # Leave it blank if you don't want to use it., i.e:
                             # qw[];
                             # This may be an issue with duplicate table names
                             # in multiple databases -- it's on the todo list.

$password_location           = 'cnf';
                             # NEW OPTION FOR PASSWORD LOCATION:
                             # 'from_web' ALLOWS WEB LOGIN
                             #.................................................
                             # set to 'cnf' or 'this_file' or 'from_web'
                             #.................................................
                             # NOTE!! I have NOT tested cnf under Windows.
                             #.................................................
                             # the connection subroutine uses this
                             # to decide which method to use.

                             # I've added functionality that allows the script
                             # to be run from the web, because some users
                             # don't have shell access.

                             # if $password_location is set to 'from_web',
                             # then \n chars are translated to <br> and also, a
                             # "Content-type: text/html\n\n"; is printed to sdtout.

                             # note that you'll have to either run the
                             # .cgi file from your web tree, or use a 'stub' file
                             # which I recommend. (see my web page for an example).

                             # NOTE!!! RUNNING FROM THE WEB is predicated
                             # on a number of issues:

                             # - web logins don't use a cnf file, since
                             #   the cnf file would be required to be world
                             #   readable, and because we have to check
                             #   the user login anyway, against mysql.

                             # - the backup directory ($mysql_backup_dir)
                             #   must be writeable by the web server
                             #   (since it's outside the webtree and the
                             #   the script requires a login, the risk
                             #   is controlled -- however, if your server
                             #   co-exists with other virtual servers,
                             #   you should make sure that they can't ftp
                             #   outside their own home directory.)

                             # - set $chmod_backup_file to 'no'
                             #   since files will be owned by web server
                             #   and if they're set to 600 you won't be able
                             #   to download them

                             # - depending on which user you login as
                             #   (super user or single user)
                             #   you may not have permission to
                             #   backup databases other than your own;
                             #   thus, set
                             #   -- @selected_databases and
                             #   --$process_all_databases correctly.

                             # - mysql user permissions will also influence
                             #   whether or not you can use
                             #   the 'select into outfile' method of backup
                             #   -- try myslqdump...
                             #   -- if all else fails, use 'normal_select'

                             # - Note about SSL and Web logins:
                             #   If you've got an ssl url, use it!
                             #   It's worth it to encrypt your database
                             #   username and password.
                             #   (Just run the script prefixed by
                             #    https://yourdomain.com/script_name.cgi)

                             #   SSL Note2: Even if you don't OWN an SSL Cert,
                             #   you can often use the https ssl syntax;
                             #   the web server will encrypt it anyway;
                             #   it simply warns you that you don't have
                             #   an ssl cert. What do you care :-)?
                             #   (You're the one running the script.)

                             #   The Cert/Browser marriage is a SCAM
                             #   in my opinion. Since the encryption
                             #   happens anyway, the stupid warning box
                             #   should be eliminated. Maybe a Congressional
                             #   sub-committee should investigate it :-).

                             #   If you want a CHEAP, FAST, cert, go to:
                             #   http://instantssl.com (approx. $40!)

$login_script_name           = 'mysql_backup_login.cgi';
                             # this is the name of the script that's used
                             # for web login -- either the real script,
                             # or a stub script
                             # If you're not using the web option,
                             # you can keep it blank, or whatever.
                             # See our website for an example stub script.

$chmod_backup_file         = 'yes';
                             # set to 'yes' if you want to use it
                             # (you DO NOT want to set the backup file to 600
                             # unless you can ftp in as the user that
                             # the script runs as. (see web use above)

#..............................................................................
# db host information
# set $db_host to a remote server if you need to access data
# on a different machine.

$db_host                     = '127.0.0.1';
                             # or, use a domain name or ip
                             # for databases on different machines

$db_port                     = '3318';
                             # database connection variables

$cnf_file                    = '/root/.my.cnf';
                             # use an absolute path; ~/ may not work

$cnf_group                   = 'client';
                             # you can store your user name and
                             # password in your cnf file
                             # or.. you can place the username and
                             # password in this file,
                             # but you should set this to 700 (rwx------)
                             # so that it's more secure.
                             # we assume here that your user name status
                             # equals the functions needed.
                             # (for example, 'select to outfile'
                             # requires file privileges.)

                             # NEW IN V3.0!
                             # I now longer parse the cnf file manually.
                             # (I actually didn't use the parsed data
                             # in 2.7, but I hadn't deleted the code.)
                             # If you select cnf_file, mysqlshow and mysqldump
                             # will use the cnf_group variable
                             # thus, your cnf file can include
                             # multiple groups if you wish.

                             # CNF FILE CONTENTS:
                             # [group_name]
                             # user=yourusername
                             # password=yourpassword

$user                        = '';
$password                    = '';

# $ENV{'MYSQL_UNIX_PORT'}    = '/var/lib/mysql/mysql.sock';
                             # use an absolute path; ~/ may not work
                             # especially with crontab.

                             # $ENV{'MYSQL_UNIX_PORT'}
                             # can be used under two circumstances:

                             # 1: When you have multiple instances of the
                             # MySQL daemon running on your host,
                             # where each instance of the daemon
                             # has its own mysql.sock file - Therefore
                             # the script needs to find the socket file.

                             # 2: If your MySQL socket file is NOT
                             # in a default directory, such as:
                             # /var/lib/mysql/mysql.sock
                             # then you may need to use the above
                             # environment command.

                             # If you use the normal MySQL
                             # installation, you can COMMENT OUT the above line

$site_name                   = 'Jira to Wiki-IT';
$subject                     = "MySQL Backup Done for $site_name";
                             # subject is the email subject

$mysql_backup_dir            = '/data/mysql_backup';
                             # use an absolute path; ~/ may not work
                             # the backup dir should normally be
                             # OUTSIDE of your web document root
                             # this directory must be writable by the script.
                             # If you backup from the web, then this directory
                             # should be set to 777. (see web notes above)

# MANDATORY UTILITY PATH SETTINGS
# ..................................

$find_commands               = 'yes';
                             # Set $find_commands to 'yes' or 'no'
                             # depending upon whether you want to have the program
                             # search for the command line utilities.
                             # This is a weak attempt at a ./configure concept.
                             # Do we need it, since one can edit the lines below?
                             # Probably not. :-)


                             # Set $find_commands to 'no' and edit the
                             # path vars directly -- whereis doesn't exist
                             # on WinX (it should :-).

                             # See the notes at the end of the script
                             # about where to download
                             # WINDOWS VERSION OF UNIX UTILITIES.
                             # After installing them, edit the paths in this
                             # section. Use / forward slashes.

                             # If you want to use different utilities, simply
                             # use this manual method of setting the paths (below)
                             # and also change the utility name. Note, however,
                             # that you should then check the parameters to the
                             # utilities used inside the script.

                             # THIS IS WHERE YOU MANUALLY SET THE PATHS TO
                             # THE UTILITIES
                             # ...............................................
if ( $find_commands eq 'no' )
      {
      $mysqlshow_cmd         = '/usr/bin/mysqlshow';
      $mysqldump_cmd         = '/usr/bin/mysqldump';
      $nice_cmd              = '/bin/nice';
      $tar_cmd               = '/bin/tar';
      $gzip_cmd              = '/bin/gzip';

      # pigz is multi-threaded and is another option
      # check params on line: 551
      # $gzip_cmd              = '/usr/bin/pigz';

      $bzip2_cmd             = '/usr/bin/bzip2';
      $ls_cmd	           = '/bin/ls';

      # windows examples (use a short directory - see windows notes above)
      # NOTE!! for Windows, you MUST include the .exe since the script
      # checks to see if the file exists before running.

      # $mysqlshow_cmd         = '/bin/mysqlshow.exe';
      # $mysqldump_cmd         = '/bin/mysqldump.exe';
      # $nice_cmd              = '/bin/nice.exe';
      # $tar_cmd               = '/bin/tar.exe';
      # $gzip_cmd              = '/bin/gzip.exe';
      # $bzip2_cmd             = '/bin/bzip2.exe';
      # $ls_cmd                = '/bin/ls.exe';

      # see windows notes above about libintl-2.dll and libiconv-2.dll
      # you may need to place them in your windows\system directory.
      # (I needed to, under Win98.)
      }
                             # ...............................................
                             # the automated method is done in the main body of
                             # the script

$compress_method             = 'z_switch';
                             # (blank) '', or 'z_switch' or 'pipe_method'

                             # NOTE!!! The z switch and the pipe method
                             # don't work on Windows

                             # use either 'z_switch' (for tar -z), or
                             # 'pipe_method' for piping through gzip or bzip2, or
                             # '' (blank) for the two step method
                             # (first tar, then gzip)

                             # Note that if you set $delete_text_files
                             # to 'yes' (below)
                             # then the text files will be deleted
                             # BETWEEN the tar and gzip creation, if the
                             # compress_method is set to ''.
                             # (thus saving disk space)

                             # Otherwise, the text files will be deleted
                             # after the gzip file is created, using the
                             # z switch or pipe method.

$delete_text_files           = 'yes';
                             # set delete_text_files to 'yes' if you want to
                             # delete the intermediate data text files,
                             # and only keep the tar.gzip files.
                             # I recommend this, because the text files
                             # can be large.

$use_bzip2                   = 'no';
                             # If you set 'use_bzip2' to 'yes'
                             # then it will be used instead of gzip,
                             # UNLESS!!
                             # $compress_method equals 'z_switch'
                             # (because the -z switch uses gzip)
                             # If set to 'no', the script won't check
                             # for bzip2 at all (so you don't need it on
                             # your disk)

$gzip_args                   = '-9v';
                             # set gzip arguments if you like
                             # -1 --fast  compress faster
                             # -9 --best  compress better

$bzip_args                   = '-9v';
                             # set bzip2 arguments if you like
                             # -1 .. -9   set block size to 100k .. 900k

###################################################################################
# OPTIONAL VARIABLES SET UP SECTION
# (You may not need to change the vars below)
###################################################################################

$show_file_list_in_email     = 'no';
                             # for large directories this should be set to 'no'

$print_stdout                = 'no';
                             # set this to 'yes' if you want to print
                             # messages to the screen, set it to 'no' if
                             # you only want the message to go to email

                             # Note that the print statements are
                             # created with a subroutine call &message
                             # &message('s/e/b', 'some message text';
                             # S = stdout, E = email, B = both

                             # Thus, you can selectively modify each
                             # &message print statement if you like.
                             # (screen output can only be selectively
                             # modified if $print_stdout equals 'yes')

$date_text                   = strftime("%Y-%m-%d_%H.%M.%S", localtime);
                             # the date_text var becomes part of the backup file
                             # name. see notes about 'backup_date_string' at end
                             # of file

$increments_to_save          = 5;
$seconds_multiplier          = 86400;
$increment_type              = "Day(s)";

$seconds_to_save             = $increments_to_save * $seconds_multiplier;
                             # increment_type is used for the text output,
                             # and has no impact on the math.

                             # one could set increment type to "Minute(s)"
                             # or "Hour(s)" or "Day(s)" or "Week(s)", etc.
                             # Just set the seconds_to_save number to
                             # the correct number of seconds, i.e:

                             # minute: 60 / hour: 3600 / day: 86400
                             # week: 604800

                             # these variables control how many increments
                             # (e.g. 'days') worth of
                             # backup files to save. Files with
                             # timestamps older than this will be deleted each time
                             # the script is run. Note that the file modification
                             # time is used - NOT the file name.
                             # This may have to be modified on non-Linux boxes.

$space_line                  = " " x 5;
                             # variable used for spaces at the beginning
                             # of some lines of printed output

# if you aren't going to ftp your backup file to a second server,
# you don't need to set these variables.

$ftp_host                    = '';
$ftp_port                    = '21';

$ftp_passive                 = '1';
                             # set to '0' (false) or '1' (true)
                             # you may need to use passive ftp transfers if you
                             # use ssh tunneling for ftp.
                             # Normally, you have to connect with ssh first,
                             # to the remote ftp host, using an IP number and
                             # port 21 for the local and remote host.
                             # You then use 'localhost' in the ftp script
                             # (i.e. $ftp_host above) and set $ftp_passive to '1'.
                             # Note that this script would need an addition to
                             # fire up ssh first, and then disconnect ssh afterward.
                             # (perhaps in the next version).
                             # when I manually fired up ssh first, with
                             # tunneling set, the ftp passive function worked fine.

$ftp_user                    = '';
$ftp_password                = '';

$ftp_dir                     = '/remote_dirname/mysql_backups/';
                             # NOTE!!!!
                             ## This should be set to the ABSOLUTE PATH
                             ## so that the delete old files routine works.
                             ## That is, you should use a beginning slash /.
                             # NOTE!!!!
                             ## You must also use a trailing / because of
                             ## the double check with pwd() before the old files
                             ## are deleted.

                             # For WinX users:
                             # Note that the upload directory under Win98
                             # using the free Cerberus FTP server correctly used
                             # long directory names, using either \ or / for
                             # directory delimiters. Cerberus is at:
                             # http://www.greenepa.net/~averett/cerberus.htm

$delete_old_ftp_files        = 'yes';
                             # delete old ftp files or not

$number_of_files_to_save     = 5;
                             # Number of files to keep on remote ftp server.
                             # Note that I don't use date processing to keep
                             # files older than a certain time, because of potential
                             # differences with timezones and remote server time
                             # changes. Since we can't control what the remote time
                             # is (unlike the local server), I used the concept of
                             # keeping a certain number of files in the remote ftp
                             # directory, using the list of files sorted by most
                             # recently uploaded first. Thus, if you keep 3, the
                             # the 3 that will be saved are the most recent 3.
                             # This number can't be less than 1.

$tar_options                 = '-pv';
                             # hardcoded options include 'c, f'
                             # p = retain permissions
                             # v = verbose (can be set below)

if ( $show_file_list_in_email eq 'yes' )
      {
      $tar_options .= ' -v';
      }

# backup file prefix

$file_prefix                 = 'bak.mysql';
                             # the file prefix is also used to match files
                             # for the deletion of old files. It's a real
                             # 'PREFIX', it will be placed at the front of
                             # each file name

# mysqldump variables
# ..................................

$mysql_dump_file_ext       = 'txt';

# NO LONGER USED!!
# $mysqldump_params        = '--quick --add-drop-table -c -l';
# NO LONGER USED!!
                             # NOTE!!! The variable $mysqldump_params
                             # is NO LONGER USED!!!
                             # Because I run mysqldump from the system
                             # command, I've hardcoded the above values
                             # in the system call, in the subroutine
                             # do_backup. I've left them here so folks can
                             # see this note. If you want to change the
                             # above variables, then go to the system
                             # call under mysqldump in the do_backup subroutine.

$backup_type                 = 'mysqldump';
# $backup_type               = 'outfile';
# $backup_type               = 'normal_select';

                             # set $backup_type to one of these 3 types:

                             # 'mysqldump'
                             # 'outfile'
                             # 'normal_select'

                             # (mysqldump is the best choice, followed by outfile)

                             # ! NOTE: for the 'outfile' method,
                             # you must have MySQL file privilege
                             # status, or the file will not be written
                             # (it will be 0 bytes long)

                             # 'normal_select' uses a normal
                             # select/write process; it's clunky,
                             # but some hosts don't provide access to
                             # mysqldump or 'select into outfile'
                             # (sometimes mysqldump is on a different
                             # server, and sometimes a user doesn't have
                             # 'file_privileges' for mysql.)

                             # NOTE: for LARGE data sets, 'normal_select'
                             # may not work well, because of memory problems

$backup_field_terminate    = '|';
$backup_field_enclosed_by  = '';
$backup_line_terminate     = ":!:\n";
                             # params for 'normal_select' file writing
                             # note that the "\n" must be interpolated
                             # via " double quotes or the qq method

                             # I use :!:\n in order to accomodate
                             # text or blob fields that have line feeds.

$outfile_params            = qq~ fields terminated by '|' lines terminated by ':!:\n' ~;
                             # params for 'select * from $table_name
                             # into $outfile ($outfile is created in
                             # the backup routine)

# end of mysqldump variables
# ...........................

# END OF SETUP VARIABLES

###################################################################################
# YOU NORMALLY WON'T HAVE TO MODIFY ANYTHING BELOW THIS LINE
###################################################################################

# web login routine
#..........................................

if ( $password_location eq 'from_web' )
      {
      print "Content-type: text/html\n\n";

      if ( param('w_user') =~ /\w+/ and param('w_password') =~ /\w+/ )
            {
            # test for authorized access
            &connect_to_db($web_test_database);

            # if we get to here, it means that we're authorized
            print qq~<br>
                     <b><font color="blue" size="+1">
                     Running MySQL Backup . . .
                     </font></b>
                     <pre>
                    ~;
            }
      else
            {
            print qq~<br><table width="70%" border="0" align="center" cellpadding="3" cellspacing="3" bgcolor="F0F0F0">
                     <tr><td colspan="2" bgcolor="darkblue">
                     <b><font color="white" size="+1">
                     MySQL Backup Web Login Screen</font></b>
                     <FORM method="post" action="$login_script_name"></td></tr>
                     <tr><td align="right">User Name: </td>
                     <td><input type="text" name="w_user" size="16" maxlength="16"></td></tr>
                     <tr><td align="right">Password: </td>
                     <td><input type="password" name="w_password" size="16" maxlength="16"></td></tr>
                     <tr><td>&nbsp;</td><td><input type="submit" value="Login"></td></tr>
                     <tr><td colspan="2" align="center">
                     Note: The login will not proceed unless you
                     type a value in both fields.</form></td></tr></table>
                    ~;
            exit;
            }
      }
else
      {
      # clear the screen
      if (-e "/dev/tty")
            {
#            $clear = `clear;pwd;`;
            print $clear;
            }
      }

# finish setup of email variables
#............................................

if ( $send_method eq 'sendmail' )
      {
      $mailprog_or_smtp_host = $mailprog;
      }
elsif ( $send_method eq 'smtp' )
      {
      $mailprog_or_smtp_host = $smtp_host;
      }
else
      {
      print qq~Error! You haven't setup your email parameters correctly.~;
      exit;
      }

# automatic utility setup
#................................
# CMD_ARRAY NOTE (below):
# Note that the automatic method of finding the commands that is used here
# creates variables names that match the commands. Since the script uses the
# default variable names listed in the array, you should not edit the array
# unless you also change the var names in the script.

# DON'T EDIT THIS CMD_ARRAY unless you know what you're doing :-).

@cmd_array = qw[mysqlshow mysqldump nice tar gzip bzip2 ls];

if ( $find_commands eq 'yes' )
      {
      foreach $command ( @cmd_array )
            {
            if ( $command eq 'bzip2' and $use_bzip2 ne 'yes' ){next;}

            $cmd_name = $command . '_cmd';
            ($name, $$cmd_name, $rest) = split / /, `whereis $command`, 3;
            chomp  $$cmd_name;
            }
      }

# zip variable setup

$gzip_file_type = 'x-gzip';
$bzip_file_type = 'x-bzip2';

$gzip_ext       = '.gz';
$bzip_ext       = '.bz2';

$gzip_type      = 'GZip';
$bzip_type      = 'BZip2';

if ( $use_bzip2 eq 'yes' and $compress_method ne 'z_switch' )
      {
      $gzip_cmd       = $bzip2_cmd;
      $gzip_args      = $bzip_args;
      $gzip_file_type = $bzip_file_type;
      $gzip_ext       = $bzip_ext;
      $gzip_type      = $bzip_type;
      }

# check if each cmd file exists
#...................................

foreach $command ( @cmd_array )
      {
      if ( $command eq 'bzip2' and $use_bzip2 ne 'yes' ){next;}
      $cmd_name = $command . '_cmd';
      unless ( -e $$cmd_name ){&error_message(qq~Error! $$cmd_name wasn't found.~);}
      }

# BEGIN BACKUP PROCESS
#....................................

$body_text = '';

unless ( -e "$mysql_backup_dir" )
      {
      &error_message(qq~Error! $mysql_backup_dir doesn't exist.~);
      }

chdir ("$mysql_backup_dir");

# now make a tar sub directory for this backup

$tar_dir = $file_prefix . "." . $date_text;
mkdir $tar_dir, 0777;

# we chmod the directory to 777 since the umask
# may be set differently.
# The directory needs to be set to 777 so that
# mysql can perform a 'select into outfile' in that
# directory (since mysql runs as a different user)

chmod 0777, $tar_dir;

unless ( -e "$mysql_backup_dir/$tar_dir" )
      {
      &error_message(qq~Error! $mysql_backup_dir/$tar_dir wasn't created.~);
      }

chdir ("$tar_dir");

$msg = "\nProcessing Backups Using " . uc($backup_type) .
       " in\n$mysql_backup_dir/$tar_dir\n\n";

if ( $print_stdout eq 'no' )
      {
      $msg .= qq~Screen Output (STDOUT) is turned OFF,
      so you won't see much until the script is done.\n\n
      ~;
      }

# I use print here, instead of &message,
# so that when $print_stdout is set to 'no',
# the script shows that it's working.

print "$msg";

&message('b',"Databases / Tables:\n");

# test and create the initial database array
# first convert the exception database and table arrays
# to hashes for speed searching
#............................................................................

%skip_databases = ();
%skip_tables    = ();

foreach my $database_name ( @skip_databases )
        {
        $skip_databases{$database_name} = $database_name;
        }

foreach my $table_name ( @skip_tables )
        {
        $skip_tables{$table_name} = $table_name;
        }

# test to see if we should process all databases

if ( $process_all_databases eq 'yes' )
        {
        if ( $password_location eq 'cnf' )
            {
            $cmd = qq~$mysqlshow_cmd --defaults-extra-file=$cnf_file --host=$db_host --port=$db_port~;
            }
        else
            {
            $cmd = qq~$mysqlshow_cmd --host=$db_host --user=$user --password=$password~;
            }

        &cmd_length($cmd) if $max_cmd > 0;
        @databases = `$cmd`;
        chomp ( @databases );
        }
else
        {
        @databases = @selected_databases;
        }

# here's where the backup is actually done
#............................................................................

foreach $db_main ( @databases )
        {
        if ( $db_main =~ /Databases/ )   {next;}
        if ( $db_main !~ /\w+/ )         {next;}
        $db_main =~ s/\|//g;
        $db_main =~ s/\s+//g;

        if ( $process_all_databases eq 'yes' and exists $skip_databases{$db_main} )
                {
                &message('b',"\nSkipping: [$db_main\]\n");
                next;
                }

        # connect to db
        &connect_to_db($db_main);

        &message('b',"\nDatabase: [$db_main\]\n");

        # now grab table names for this databases
        # we use 'show tables' to avoid problems with mysqlshow % with older versions
        # ............................................................................

        # NEW AS OF 2010-07-01, v.3.4
        # uses show table status, to get table types as well as table names

        $sth = $dbh->prepare("show table status") or &error_message(qq~Error!\n
                                                  Can't execute the query: $DBI::errstr~);

        $rv = $sth->execute or &error_message(qq~Error!\n
                               Can't execute the query: $DBI::errstr~);

        # while ( ( $table_name ) = $sth->fetchrow_array )

        while( $hash_ref = $sth->fetchrow_hashref )
                {
                $table_name   = $hash_ref->{'Name'};
                $table_engine = $hash_ref->{'Engine'};

        # END OF NEW AS OF 2010-07-01, v.3.4

                if ( exists $skip_tables{$table_name} )
                        {
                        &message('b',"\nSkipping: [$table_name\]\n");
                        next;
                        }

                if ( $print_stdout eq 'yes' )
                        {
                        print "$space_line table: [$table_name\]\n";
                        }

                if ( $show_file_list_in_email eq 'yes' )
                        {
                        $body_text .= "$space_line table: [$table_name\]\n";
                        }

                # NOW DO THE BACKUP
                #############################################################

                # NEW AS OF 2010-07-01, v.3.4
                # added $table_engine parameter

                $backup_text = &do_backup($db_main, $table_name, $table_engine);

                if ( $print_stdout eq 'yes' )
                        {
                        print $backup_text;
                        }

                if ( $show_file_list_in_email eq 'yes' )
                        {
                        $body_text .= $backup_text;
                        }
                }

        # disconnect from each database
        &logout;
        }

# now tar and compress
#............................................................................

chdir ("$mysql_backup_dir");

&message('b',qq~\nTarring and Zipping Files (using $gzip_cmd):\n~);

$backup_tar_file      = $mysql_backup_dir . "/" .
                        $file_prefix . "." . $date_text . "_.tar";

$backup_gzip_file     = $backup_tar_file . "$gzip_ext";
$upload_gzip_filename = $file_prefix . "." . $date_text . "_.tar" . "$gzip_ext";

$compress_output = '';

if ( $compress_method eq 'z_switch' )
      {
      # compress with tar z switch
      &message('b',qq~\nNow Compressing with the Tar -z Switch ...\n~);

      $cmd = qq~$nice_cmd $tar_cmd $tar_options -c -z -f $backup_gzip_file $tar_dir~;
      &cmd_length($cmd) if $max_cmd > 0;
      $compress_output = `$cmd`;
      }
elsif ( $compress_method eq 'pipe_method' )
      {
      # pipe through gzip or bzip2
      &message('b',qq~\nNow Compressing via a Tar / $gzip_type Pipe ...\n~);

      $cmd = qq~$nice_cmd $tar_cmd $tar_options -c -f - $tar_dir | $gzip_cmd $gzip_args > $backup_gzip_file~;
      &cmd_length($cmd) if $max_cmd > 0;
      $compress_output = `$cmd`;
      }
else
      {
      # use two step method
      &message('b',qq~\nNow Compressing via Tar followed by $gzip_type ...\n~);

      $cmd = qq~$nice_cmd $tar_cmd $tar_options -c -f $backup_tar_file $tar_dir~;
      &cmd_length($cmd) if $max_cmd > 0;
      $compress_output = `$cmd`;

      # delete text files now, to save disk space
      if ( $delete_text_files eq 'yes' )
            {
            &delete_text_files;
            # set delete_text_files to 'no'
            # so that the script doesn't try to do it again, below
            $delete_text_files = 'no';
            }

      &message('b',qq~\nNow Compressing with $gzip_type ...\n~);

      $cmd = qq~$nice_cmd $gzip_cmd $gzip_args $backup_tar_file~;
      &cmd_length($cmd) if $max_cmd > 0;
      $compress_output .= `$cmd`;
      }

&message('s',$compress_output);

if ( $chmod_backup_file eq 'yes' )
        {
        chmod 0600, $backup_gzip_file;
        }

&message('b',"\nCreated Tar $gzip_type File: $backup_gzip_file\n");

# now check option to delete text files
#............................................................................

if ( $delete_text_files eq 'yes' )
      {
      &delete_text_files;
      }
else
      {
      if ( $chmod_backup_file eq 'yes' )
            {
            chmod 0700, $tar_dir;
            }
      else
            {
            chmod 0755, $tar_dir;
            }
      }

# now clean old files from main dir (gzip files)
# includes old tar_dirs

&clean_old_files("$mysql_backup_dir");

# now do ftp, if option is set

if ( $ftp_backup eq 'yes' )
        {
        # Connect to the server:
        &message('b',"\nConnecting via FTP to $ftp_host\n");

        $ftp = Net::FTP->new("$ftp_host",
                         Timeout => "30",
                         Port    => "$ftp_port",
                         Passive => "$ftp_passive",
                         Debug   => "0") or
               &error_message(qq~Error! Net::FTP couldn't connect to $ftp_host : $@\n~);

        # Login with the username and password
        &message('b',"\nLogging in with FTP.\n");

        $ftp->login("$ftp_user", "$ftp_password") or
              &error_message(qq~Error! Net::FTP couldn't login to $ftp_host : $!\n~);

        # set the type to binary
        &message('b',"\nSetting FTP transfer to binary.\n");

        $ftp->binary or
              &error_message(qq~Error! Net::FTP couldn't set the type to binary for $ftp_host : $!\n~);

        # Change to the right directory
        &message('b',"\nChanging to FTP dir: $ftp_dir\n");

        $ftp->cwd("$ftp_dir") or
              &error_message(qq~Error! Net::FTP couldn't change to $ftp_dir at $ftp_host : $!\n~);

        #......................................................................

        if ( $delete_old_ftp_files eq 'yes' )
            {
            # First check to see if file already exists
            # and process deletions of old files
            &message('b',"\nChecking to see if file exists already: $upload_gzip_filename\n... and deleting old files.\n");

            # used 'ls' here instead of 'dir' because I only wanted the filename

            $check_pwd = $ftp->pwd() or &error_message(qq~Error!\nCouldn't check ftp dir with "pwd".~);;

            if ( "$check_pwd" ne "$ftp_dir" )
                  {
                  &error_message(qq~
                  Error! Delete Old FTP Files function in WRONG Directory. : $!

                  Setup Dir: $ftp_dir
                  Current Dir: $check_pwd

                  Possibly the script's ftp directory was not specified with
                  BEGINNING AND TRAILING SLASHES - this is necessary to match the
                  "pwd" check before deleting old files.

                  The beginning slash is mandatory for the "ls" command to work correctly,
                  to get a list of files to delete.
                  \n~);
                  }
            else
                  {
                  &message('b',"\nIn Correct FTP Directory to Delete Old Files: $check_pwd.\n");
                  }

            @files = $ftp->ls("$ftp_dir");

            @new_files = ();

            foreach my $file ( @files )
                  {
                  next if "$file" eq '.' or "$file" eq "..";
                  push @new_files, $file;
                  }

            $number_files = scalar(@new_files);

            &message('b',"\nNumber of remote files: $number_files\n");

            if ( $number_files > 0 )
                {
                if ( $number_of_files_to_save < 1 )
                      {
                      &error_message(qq~Error.\nThe variable 'Number of Files to Save' can't be less than 1.~);
                      }

                # reverse list to process deletions
                @files_reverse = reverse(@new_files);

                my $deleted_files = 0;
                my $file_count    = 1;
                # adjust starting number to include file uploaded after deletion process
                # e.g: save: 1
                # file_count (real and then including count of uploaded file):
                # 1(2)     $file_count <= $number_of_files_to_save / keep / else delete
                # 2(3)
                # 3(4)
                # +1 (uploaded file increments start count)

                foreach $file ( @files_reverse )
                    {
                    next if "$file" eq '.' or "$file" eq "..";

                    $file_count++;

                    # keep $number_of_files_to_save, delete older files

                    if ( $file_count <= $number_of_files_to_save )
                            {
                            # keep
                            &message('b', "- Keeping Remote File: $file\n");
                            }
                    else
                            {
                            # delete
                            $del_return = $ftp->delete("$file");
                            $del_size   = $ftp->size("$file");

                            if ( $del_size < 1 )
                                {
                                $deleted_files++;
                                &message('b', "$del_return File Removed: ($file\)\n");
                                }
                            else
                                {
                                &error_message("\nProblem Removing File: $file\n");
                                }
                            }

                    # check if file exists
                    if ( $file =~ /$upload_gzip_filename/ )
                          {
                          &error_message(qq~Error! $upload_gzip_filename already exists at $ftp_host : $!\n~);
                          }
                    }

                &message('b', "$deleted_files Remote File(s) Removed\n");
                }

            } # end of delete old files routine

        #......................................................................

        # Upload the file
        &message('b',"\nUploading file: $backup_gzip_file\n");

        $ftp->put("$backup_gzip_file","$upload_gzip_filename") or
              &error_message(qq~Error! Net::FTP couldn't upload $backup_gzip_file at $ftp_host : $!\n~);

        # Get file size to see if the file uploaded successfully
        &message('b',"\nChecking File Size of Remote file $upload_gzip_filename at $ftp_host\n");

        $uploaded_size = $ftp->size("$upload_gzip_filename") or
                 &error_message(qq~Error! Net::FTP couldn't get the size of $upload_gzip_filename at $ftp_host : $!\n~);

        $gzip_filesize = -s $backup_gzip_file;
        if ( $gzip_filesize == $uploaded_size )
            {
            &message('b', "\nUploaded File Size ($uploaded_size\) of $upload_gzip_filename (local size: $gzip_filesize) Matched at ftp site: $ftp_host\n");
            }
        else
            {
            &error_message(qq~Error! Uploaded File Size ($uploaded_size\) of $upload_gzip_filename (local size: $gzip_filesize) did NOT match at $ftp_host : $!\n~);
            }

        # Disconnect
        &message('b', $dir_print_text);
        &message('b',"\nDisconnecting from ftp site: $ftp_host\n");

        $ftp->quit() or
              &error_message(qq~Error! Net::FTP couldn't disconnect from $ftp_host : $!\n~);
        }

# now email admin notification of backup, with attached file option
#............................................................................

if ( $email_backup eq 'yes' )
        {
        &message('b', "\nEmailing $gzip_type File.\n");

        MIME::Lite->send("$send_method", "$mailprog_or_smtp_host", Timeout=>60);

        # Create a new multipart message:
        $msg = new MIME::Lite
                    From    =>"$admin_email_from",
                    To      =>"$admin_email_to",
                    Subject =>"$subject",
                    Type    =>"multipart/mixed";

        # Add parts
        attach $msg
                    Type     =>"TEXT",
                    Data     =>"\nTar.$gzip_type File\n[$backup_gzip_file]\nAttached\n$body_text";

        attach $msg
                    Type     =>"$gzip_file_type",
                    Encoding =>"base64",
                    Path     =>"$backup_gzip_file",
                    Filename =>"$upload_gzip_filename";

        $msg->send || die print qq~Error!\n\nError in Mailing Program!~;
        }
else
        {
        # just send notice, without attachment

        if ( $send_method eq 'smtp' )
            {
            # use this for windows machines that don't have sendmail

            MIME::Lite->send("$send_method", "$mailprog_or_smtp_host", Timeout=>60);

            $msg = new MIME::Lite
                        From     =>"$admin_email_from",
                        To       =>"$admin_email_to",
                        Subject  =>"$subject",
                        Type     =>"TEXT",
                        Encoding =>"7bit",
                        Data     =>"$body_text";

            $msg->send || die print qq~Error!\n\nError in Mailing Program!~;
            }
        else
            {
            &mail_to($admin_email_to, $admin_email_from, $subject, $body_text, $admin_email_from);
            }
        }

# I don't use &message here since the email has already gone out,
# and because it's perhaps good to give even minimilistic final output,
# even when $print_stdout is set to 'no'

print "\n\nDone! Exiting from MySQL Backup Script.\n\n";

exit;

###################################################################################
# connect_to_db
sub connect_to_db
{

# &connect_to_db($db_main);

my ($db_main) = @_;

if ( $password_location eq 'from_web' )
      {
      # we assume that the admin user should NOT use a .cnf file, but should
      # be forced to login from a form.

      # we test against 'w_user' and 'w_password' just in case
      # the 'user' and 'password' have been added to the setup section.

      $w_user     = param('w_user');
      $w_password = param('w_password');

      if ( $w_user !~ /\w+/ or $w_password !~ /\w+/ )
            {
            &error_message(qq~Error!<p>The Username and Password can't be
                             blank. Please hit BACK and try again.~);
            }

        $dbh = DBI->connect("DBI:mysql:$db_main:$db_host:$db_port", $w_user, $w_password)
                || &error_message(qq~<p>
                You were unable to connect to the database<br>
                It may be that you typed in your username or password
                incorrectly.<br>
                Please hit BACK and try again.~);

      # we now have to copy the username and password to $user and $password
      # so that mysqlshow and mysqldump will find them

      $user     = $w_user;
      $password = $w_password;
      }

elsif ( $password_location eq 'this_file' )
        {
        $dbh = DBI->connect("DBI:mysql:$db_main:$db_host:$db_port", $user, $password)
                || &error_message(qq~Error!\n
                You were unable to connect to the database.\n
                $DBI::errstr~);
        }

elsif ( $password_location eq 'cnf' )
        {
        $dbh = DBI->connect("DBI:mysql:$db_main:$db_host:$db_port"
                             . ";mysql_read_default_file=$cnf_file"
                             . ";mysql_read_default_group=$cnf_group",
                             $user, $password)
                             || &error_message(qq~Error!\n
                             You were unable to connect to the database.\n
                             $DBI::errstr~);
        }
else
        {
        &error_message(qq~Error!\n
                        ... connecting to the Database.\n
                        You were unable to connect to the database.
                        Please check your setup.
                        ~);

        }

$dbh->{PrintError} = 1;
$dbh->{RaiseError} = 0;

}
###################################################################################
# logout
sub logout
{

warn $DBI::errstr if $DBI::err;
if ( $dbh ){$rcdb = $dbh->disconnect;}

}
###################################################################################
# error_message
sub error_message
{

# &error_message($error_text);

my ($error_text) = @_;

my $subject = "$site_name MySQL Backup Error";

print qq~\n$subject\n$error_text\n~;

if ( $send_method eq 'smtp' )
      {
      # use this for windows machines that don't have sendmail

      MIME::Lite->send("$send_method", "$mailprog_or_smtp_host", Timeout=>60);

      $msg = new MIME::Lite
                  From     =>"$admin_email_from",
                  To       =>"$admin_email_to",
                  Subject  =>"$subject",
                  Type     =>"TEXT",
                  Encoding =>"7bit",
                  Data     =>"$error_text";

      $msg->send || die print qq~Error!\n\nError in Mailing Program!~;
      }
  else
      {
      &mail_to($admin_email_to, $admin_email_from, $subject, $error_text, $admin_email_from);
      }

exit;

}
###################################################################################
# message
sub message
{

# &message('s/e/b', $message);
# S = stdout
# E = email
# B = both

my ($output_method, $message) = @_;

if ( $print_stdout eq 'yes' )
      {
      if ( $output_method eq 's' or $output_method eq 'b' )
            {
            if ( $password_location eq 'from_web' )
                  {
                  $message_to_web = $message;

                  # $message_to_web =~ s/\n/<br>\n/g;

                  # I've disabled this because I use a <pre> code
                  # prior to the web output.

                  print $message_to_web;
                  }
            else
                  {
                  print $message;
                  }
            }
      }

if ( $output_method eq 'e' or $output_method eq 'b' )
      {
      if ( $body_text !~ /\w+/ )
            {
            $body_text  = $message;
            }
      else
            {
            $body_text .= $message;
            }
      }

}
###################################################################################
# cmd_length
sub cmd_length
{

# &cmd_length($cmd);

my ($cmd) = @_;

if ( length($cmd) > $max_cmd )
      {
      &error_message(qq~
                       Error:<p>
                       The length of [$cmd\] is longer than $max_cmd\.
                       <p>
                       Check things like the length of the directory name
                       where you store your unix utilities.
                       You might like to shorten it to '/bin'.
                      ~)
      }

}
###################################################################################
# mail_to
sub mail_to
{

# &mail_to($email_to, $email_from, $subject, $mail_body, $reply_to);

my ($email_to, $email_from, $subject, $mail_body, $reply_to) = @_;

if ( $reply_to !~ /\@/ ){$reply_to = $email_from;}

open (MAIL, "|$mailprog") || die print qq~Error!\n\nCan't open $mailprog!~;

print MAIL "To: $email_to\n";
print MAIL "From: $email_from\n";
print MAIL "Subject: $subject\n";
print MAIL "Reply-To: $reply_to\n";
print MAIL "\n";
print MAIL "$mail_body";
print MAIL "\n";
close (MAIL);

}
###################################################################################
# do_backup
sub do_backup
{

# NEW AS OF 3.4 (table_engine param)
# $backup_text = &do_backup($db_main, $table_name, $table_engine);

my ($db_main, $table_name, $table_engine) = @_;
my $response_text = '';

my $sth, $rv, $backup_file, $mysqldumpcommand;
my $backup_str, $row_string, $field_value;
my $len_field_terminate;
my @row;

$backup_file = $file_prefix . "." . $date_text . "_" . $db_main . "." . $table_name . "." . $mysql_dump_file_ext;
$full_file   = "$mysql_backup_dir/$tar_dir/$backup_file";

if ( $backup_type eq 'mysqldump' )
        {
        if ( $password_location eq 'cnf' )
            {

            # NEW AS 3.4 (table_engine param)

            if ( $table_engine eq "InnoDB" )
                  {
                  &message('s',"\nBacking up InnoDB Table...\n\n");

                  # system("$mysqldump_cmd", "--defaults-extra-file=$cnf_file", "--host=$db_host", "--port=$db_port", 
                  # "--opt", "--skip-quote-names", "--routines", "--triggers", "--single-transaction",
                  # "--result-file=$full_file", "$db_main", "$table_name");

                  system("$mysqldump_cmd", "--defaults-extra-file=$cnf_file", "--host=$db_host", "--port=$db_port", "--opt", "--skip-quote-names", "--routines", "--triggers", "--single-transaction", "--result-file=$full_file", "$db_main", "$table_name");
                  }
            else
                  {
                  system("$mysqldump_cmd", "--defaults-extra-file=$cnf_file", "--host=$db_host", "--port=$db_port", "--quick", "--add-drop-table", "-c", "-l", "--result-file=$full_file", "$db_main", "$table_name");
                  }

            }
        else
            {
            system("$mysqldump_cmd", "--host=$db_host", "--port=db_port", "--user=$user", "--password=$password", "--quick", "--add-drop-table", "-c", "-l", "--result-file=$full_file", "$db_main", "$table_name");
            }
        }
elsif ( $backup_type eq 'outfile' )
        {
        $backup_str = qq~
                      select * into outfile
                      '$full_file'
                      $outfile_params
                      from $table_name
                      ~;

        $sth =  $dbh->do("$backup_str")
                      or &error_message(qq~Error!\n
                      Can't backup data: $DBI::errstr~);

        }
else
        {
        unless ( open(FILE, ">$full_file" ))
                {
                &error_message(qq~Error!\n
                Can't open File $backup_file.~);
                }

        $sth  = $dbh->prepare("select * from $table_name")
                or &error_message(qq~Error!\n
                Can't do select for backup: $DBI::errstr~);

        $rv   = $sth->execute
                or &error_message(qq~Error!\n
                Can't execute the query: $DBI::errstr~);

        while ( @row = $sth->fetchrow_array )
                {
                $row_string = '';

                foreach $field_value (@row)
                        {
                        $row_string .= $backup_field_enclosed_by .
                                       $field_value .
                                       $backup_field_enclosed_by .
                                       $backup_field_terminate;
                        }

                $len_field_terminate = length($backup_field_terminate);
                if ( substr($row_string,-$len_field_terminate,$len_field_terminate) eq $backup_field_terminate)
                        {
                        substr($row_string, -$len_field_terminate,$len_field_terminate) = '';
                        }

                $row_string .= $backup_line_terminate;

                print FILE $row_string;
                }

        close(FILE);

        }

if ( $chmod_backup_file eq 'yes' )
        {
        chmod 0600, $full_file;
        }

$filesize = -s $full_file;
$response_text .= ' ' x 13 . "file: ($filesize bytes) $backup_file\n";

unless ( -e "$full_file" )
      {
      &error_message(qq~Error! "$full_file" wasn't created!~);
      }

return ($response_text);

}
###################################################################################
# delete_text_files
sub delete_text_files
{

&message('b', qq~\nRemoving Directory: $mysql_backup_dir/$tar_dir\n~);

chdir ("$mysql_backup_dir");

# this requires File::Path

$removed_dir = rmtree($tar_dir,0,1);

if ( -e "$tar_dir" )
      {
      &error_message(qq~Error! Tar Dir: $tar_dir wasn't deleted!<br>
                        Output results:<br>
                        $removed_dir
                       ~);
      }
else
      {
      &message('b', "Removed temporary Tar Dir: $mysql_backup_dir/$tar_dir\n");
      }

}
###################################################################################
# clean_old_files
sub clean_old_files
{

# $mysql_backup_dir
# $seconds_to_save  = $increments_to_save * $seconds_multiplier;

# call this subroutine with the '$full_dir_name'

my ($full_dir_name) = @_;

unless ( -e $full_dir_name )
      {
      &message('b',"\nCould NOT Clean Old Files - $full_dir_name doesn't exist.\n");
      return;
      }

&message('b',"\nCleaning Old Files\n");

$save_time  = time() - $seconds_to_save;
$deleted_files = 0;

&message('b', "\nRemoving Files Older than $increments_to_save $increment_type\n");

opendir (DIRHANDLE, $full_dir_name);

# we use $file_prefix to make it safer; we don't want to delete
# any files except those matching the file spec

@filelist = grep { /^$file_prefix\./ } readdir(DIRHANDLE);

closedir (DIRHANDLE);

@sortlist   = sort(@filelist);

my $file_count = @sortlist;
my $file_msg   = "File Count in Backup Dir: $file_count \n\n";
&message('b', $file_msg);

# loop through directory
foreach $infile (@sortlist)
        {
        $infile_str = $infile;
        $infile     = "$full_dir_name/$infile";

        ($modtime) = (stat($infile))[9];

        if ( $modtime < $save_time )
                {
                # file is older, so delete it
                # check if file is a directory
                if ( -d $infile )
                    {
                    &message('b', "\n - Deleting Tar Subdir: $infile\n");
                    $deleted_dir = rmtree($tar_dir,0,1);

                    if ( -e "$infile" )
                        {
                        &error_message("\n - Problem Deleting Tar Subdir - $infile_str\.\n");
                        }
                    else
                        {
                        $deleted_files++;
                        &message('b', " - Deleted Tar Subdir Correctly - $infile_str\.\n\n");
                        }
                    }
                else
                    {
                    $delete_count  = unlink "$infile";

                    if ( ! -e $infile )
                            {
                            $deleted_files++;
                            &message('b', "$delete_count File Removed: ($infile_str\)\n");
                            }
                    else
                            {
                            &error_message("\nProblem Removing File: $infile_str\n");
                            }
                    }
                }
        else
                {
                &message('b', "- Keeping: $infile_str\n");
                }

        } # end of file loop

&message('b', "\nRemoved $deleted_files Files and/or Directories.\n");

}
###################################################################################
# END OF SCRIPT
###################################################################################

=head1 WINDOWS VERSION OF UNIX UTILITIES

        Here are some urls for windows versions of the unix utilities
        that I use in this program.
        Note that there are some differences:

        - chmod doesn't mean much on Winx (I use Perl's internal chmod
          so that utility doesn't have to be imported anyway).

        - tar won't filter through gzip

        1. UnxUtils (bzip2, gzip, ls, tar)
        ----- http://www.weihenstephan.de/~syring/win32/UnxUtils.html
              !!!(can't pipe to gzip, can't create tar.gz)

        2. shell utils (nice)
        ----- http://gnuwin32.sourceforge.net/packages/sh-utils.htm

        3. cron for windows
        ----- http://www.kalab.com/freeware/cron/cron.htm
              you can use cron for windows or Windows Scheduler
              (or one of the other numerous scheduling utilities)

        4. libintl-2.dll and libiconv-2.dll
        ----- http://gnuwin32.sourceforge.net/packages/libintl.htm
              You may need to install these dlls in your
              \windows\system directory. See Windows notes in setup.
              I only tested this in Win98. I didn't run into the problem
              in Windows 2000, but my testing wasn't extensive there.

        Thanks to Seth Rajkumar in London for urls 1. and 3.

        ALTERNATE URLS

        4. file utils (ls)
        ----- http://gnuwin32.sourceforge.net/packages/fileutils.htm
        5. tar
        ----- http://gnuwin32.sourceforge.net/packages/tar.htm
              !!!(can't pipe to gzip, can't create tar.gz)
        6. gzip
        ----- http://gnuwin32.sourceforge.net/packages/gzip.htm
        7. bzip2
        ----- http://gnuwin32.sourceforge.net/packages/bzip2.htm


=BACKUP DATE STRING NOTES

        This is a handy method to initialize date display
        it requires the POSIX and Time::Local calls above
        I use this because I got tired of messing with date routines

        e.g: $backup_date_string = strftime("%Y-%m-%d_%H.%M.%S", localtime);

        - strftime notes:
        If you want your code to be portable, your format argument
        should use only the conversion specifiers defined by the ANSI C
        standard. These are:

        a A b B c d H I j m M p S U w W x X y Y Z %

        DON'T USE: C D e E F G g h k l n O P r R s t T u V z +
        They usually work under Linux, but not necessarily under WinX.

        I specifically had problems with 'e' and 'l'.
        They didn't work on a Win2000 machine I tested them on.
        I had to change them from 'e' to 'd' and 'l' to 'I'.

        Note that 'e' and 'l' wouldn't normally be used for
        a file name string anyway, because of the spaces in their output.

        %e - Like  %d, the day of the month as a decimal number,
	       but a leading zero is replaced by a space. (SU)

        %d - The day of the month as a decimal number (range 01 to 31).

        %l - The hour (12-hour clock) as a decimal number (range
	       1 to  12);  single digits are preceded by a blank.
	       (See also %I.) (TZ)

        %I - The hour as a decimal number using a 12-hour clock
             (range 01 to 12).

        .......................................................................
        Rather than list all the code definitions, here's a url to visit a
        Unix manpage site, such as: http://unixhelp.ed.ac.uk/CGI/man-cgi
        (type in 'strftime').

        Or, from the shell prompt, type in 'man strftime'.
        .......................................................................

=VERSION HISTORY

v.3.4 - June 30, 2010    - Modified code check for InnoDB tables (only with cnf usage, so far)

v.3.3 - July 24, 2008    - Added code to make sure remote directory to delete ftp files
                           matches setup variable for remote directory when using "pwd".

                           If it doesn't match, the 'ls' command returns zero files,
                           so the remote list of files never gets deleted.
                           One doesn't want one's remote server to fill up!

                           Ftp 'ls' requires the beginning slash to read the file list.
                           If it doesn't have the beginning slash, it would assume the
                           directory is a subdirectory of the current directory.

                           'pwd' produces a trailing slash, so both slashes are required in
                           the setup ftp directory variable.

                         - Added code to remove '.' and '..' from remote ftp list of files.

v.3.2 - May 15, 2006     - Added code to not break if the remote ftp dir
                           didn't have any files in it. Thanks to a number of
                           users for pointing this out.

                         - Added code to delete remote ftp files, based on
                           the variable $number_of_files_to_save (see comments
                           under variable, in set up section)

v.3.1 - Nov. 21, 2003    - Added code to check if file has already been
                           uploaded to the ftp site -- it yes, aborts.

                           Note that if your filename has seconds
                           in the datetime string, you shouldn't run into
                           the ftp overwrite / bad file descriptor problem.
                           In any case, the script will abort if the file exists.

                         - Added code to check the filesize of the uploaded file,
                           and removed code that simply listed the name

                         - rearranged the order of the message/code lines
                           in the ftp section to be clearer

                         - changed order of --result-file in mysqldump
                           to *before* the dbname

v.3.0 - May 17, 2003     - Note that I skipped from 2.7 to 3.0
                           because I consider this a 'major' upgrade.

                         - See the end of this v3.0 section for acknowledgements.

                         - NEW: MYSQLDUMP --RESULT-FILE FLAG!
                           new method of invoking mysqldump: --result-file
                           NOTE!! some earlier versions of mysqldump don't
                           have the --result-file flag -- if your version
                           doesn't, you may have to
                           a) upgrade mysql or
                           b) use the outfile or normal_select method
                           I tested it on:
                           - Linux with MySQL v3.23.54 - worked fine
                           - Win98 with MySQL v3.23.33 - no result-file flag
                           I searched and SEARCHED :-) through the History
                           notes at mysql.com to find out when they introduced
                           the result-file flag, but I haven't found it yet.
                           If someone finds it, let me know.

                           I use the --result-file=$file and system call method
                           with mysqldump because I had problems with the
                           backtick and > redirection symbol on Win98, running
                           from the script. I'm still trying to figure out why.
                           Also note that the system method with a list
                           doesn't invoke the shell, so that we don't run into
                           the 127 character command limit on Win98.

                         - I now longer parse the cnf file manually.
                           (I actually didn't use the parsed data
                           in 2.7, but I hadn't deleted the code.)
                           If you select cnf_file, mysqlshow and mysqldump
                           will use the cnf_group variable
                           thus, your cnf file can include
                           multiple groups if you wish.

                         - added the mysqlshow and mysqldump flag:
                           --defaults-extra-file=$cnf_file
                           so that cron will find the correct cnf file
                           Thanks to Kaloyan Tenchov.

                         - added a note about the env var:
                           $ENV{'MYSQL_UNIX_PORT'}.
                           If your MySQL socket file is NOT
                           in a default directory, such as:
                           /var/lib/mysql/mysql.sock
                           then you may need to use the above
                           environment command.

                         - uncommented
                           $dbh->{PrintError} = 1;
                           $dbh->{RaiseError} = 0;
                           and changed PrintError to 1
                           and RaiseError to 0
                           so that errors don't cause the
                           script to die, but still provide output

                         - added variable for the command 'ls'

                         - removed the need for the utility commands
                           find, rm, xargs, wc
                           by recoding two subroutines in Perl.
                           (delete_text_files and clean_old_files)
                           (There's always more than one way to do it. :-)
                           This was stimulated by the problems with
                           backticks and pipes on Win98.
                           I now use File::Path to remove directories
                           and simple directory arrays to remove files,
                           since the directories aren't nested.

                         - added note with urls to get windows
                           versions of unix utilities used in the script

                         - updated automatic method of the whereis
                           section that finds commands (cleaner)

                         - added chomp command to whereis output

                         - added routine to check for script utilities
                           on the disk and abort with error if not found

                         - changed the zip filename in the MIME::Lite
                           attachment section to not have the path

                         - added a bit of code to clear the screen when
                           the script is run (from the shell)

                         - added option for bzip2
                         - added options for gzip and bzip2 parameters
                         - changed gzip output labels to include bzip2

                         - added a compress_method option for
                           standard two step compression, or tar -z,
                           or the tar gzip pipe method.

                         - changed code to delete text files in between
                           tar and gzip if options are set.

                         - moved code to delete text files into subroutine

                         - modified some of the output

                         - added a variable $print_stdout
                           so that if it's not set to 'yes', the messages
                           will only get sent to the admin email, rather
                           than printed to the stdout (screen)
                           Thanks to Matthew Moffitt for the idea.

                         - create &message subroutine to make the print
                           and $body_text email statements cleaner.
                           (the &message subroutine allows selective
                           output, using 's' for screen, 'e' for email,
                           and 'b' for both)

                         - fixed mysql outfile method,
                           by chmoding tar_dir to 777 so that mysql
                           can write to that directory.
                           Also added full path name to the outfile.

                           (The last time I tested the outfile method,
                           I was using a separate instance of mysql,
                           running as my own user, rather than 'mysql',
                           which is why it worked then, but not when
                           it runs as mysql.)

                         - added code to chmod tar_dir to 700 if
                           $chmod_backup_file is set to yes; otherwise
                           it's chmoded to 755 (from 777 - see above)

                         - added error routines to check for the creation
                           of tar_dir, the existence of mysql_backup_dir,
                           the creation of the backup files, and the
                           deletion of the files to be deleted.

                         - added a number of variables and code bits
                           that allow one to run the script from the
                           web, with a password protected login,
                           for users that don't have shell access.

                         - re-arranged the layout of some of the setup
                           variables, to be more convenient (some are
                           closer to the top of the file).

                         - added notes about libintl-2.dll and libiconv-2.dll
                           I needed to install these dlls in \windows\system
                           under Win98.

                         - added the record delimiter :!: to the outfile and
                           normal select method of backing up (with a \n)
                           to accomodate multiline text records easily

                         - note about segmentation faults on startup:
                           As far as I can tell, some versions of DBI/DBD::mysql
                           caused a fault when the connect parameters
                           'mysql_read_default_file=$cnf_file"' and
                           'mysql_read_default_group=$cnf_group"' were used.
                           The mysql site has notes about this.
                           If you're experiencing this:
                           1. try to use the 'this_file' method of connecting,
                              and commment out the cnf file params, and
                           2. check out the mysql site for a better version
                              of DBI/DBD.

                         - modified the email commands to use Net::SMTP
                           for Windows users (or for anyone)
                           Note that to successfully email from Windows,
                           with Net::SMTP, you need to connect to a running
                           mailserver. I had good results with the Microsoft
                           IIS mailserver on Win2000, although it was a pain
                           to setup (I didn't set it up :-).

                         - placed die print commands in Mime::Lite routines,
                           instead of &error_message, because &error_message
                           invokes the email routine, which would cause a loop.

                         - confirmed that passive ftp with ssh tunneling works.

                         - moved the contents of $mysqldump_params into the
                           subroutine do_backup, because of the system call syntax.

                         - added notes about strftime under WinX.

                         - moved the use Net::FTP; and use MIME::Lite;
                           lines up to the associated vars for convenience.

                         - Acknowledgements:
                           =================
                           Thanks to all the suggestions, code ideas and
                           patch contributions from our users!
                           About patches: I usually "integrate" patches,
                           or patch ideas, into the program within my own
                           particular coding style. So, most patches won't
                           appear exactly as submitted (often because I
                           change things alot as I upgrade.)

                           However, I deeply appreciate the patch efforts,
                           and code suggestions. v3.0 is due to all of your
                           comments and input! Thanks go to: (listed by alpha)

                           Achim Dreyer, Alexander Klein, Andreas Gunleikskas,
                           Artur Neumann, Bob Uehlein, Borracho, Carsten Grohmann,
                           Cesar Mendoza, Chris Wright, Christian Mohn, Coffe,
                           Craig Paterson, Daniel Myers, David Adams,
                           Eric Eichberger, Erik Meusel, Frank Van Damme,
                           Ilya Palagin, Jean-Francois Laflamme, Joe Claborn,
                           Jonathan Hutchins, Joris, Kaloyan Tenchov, Ken Kirchner,
                           Kenneth Kabagambe, Kevin Zembower, Manfred Larcher,
                           Martin Kos, Matthew Boehm, Matthew Moffitt,
                           Michael C. Neel, Michael Haydock, Michael Klug,
                           Mike Yrabedra, Nate Parsons, Normand J. Charette,
                           Paul Kremer, Russell Uman, Seth Rajkumar, Stephen Calia,
                           The Sysadmin of Oceanet Technology, Vladyslav Shvedenko,
                           Zak Zebrowski (I apologize if I forgot anyone! :-).

v2.7 - June 11, 2002     - Bug fix:
                           moved the two 'use' statements for
                           Net::FTP and MIME::Lite to the top of the file
                           with instructions to comment out those two lines
                           if the libraries aren't installed, since the
                           'use' lines do get parsed.

v2.6 - June 10, 2002     - added the ftp_option
                           The initial ftp code was contributed by
                           Gil Hildebrand, Jr. (root@moflava.net)
                           with additional code by myself.
                           (added error checking, extra params, etc.)

                         - added code to skip loading
                           Net::FTP and MIME::Lite if
                           $ftp_backup and $email_backup are set to 'no'
                           If you don't want to install them,
                           you no longer have to comment out code sections.
                           (see v2.7 above for bug fix)
                           (the main code doesn't have to be commented out,
                           but the 'use' lines do.)

                         - changed semi-colon ; to comma , after:
                           attach $msg ....
                                  Path     =>"$backup_gzip_file",
                           Thanks to Kenneth Martis for finding the bug.

                         - added a segment under $find_commands
                           to configure the paths for the command line utils
                           mysqldump, mysqlshow, nice, tar, gzip
                           Thanks to Luc Schiltz for the concept.
                           NOTE: If you use the automatic option, you
                           should of course check the results.

                         - added --host=$db_host to
                           mysqlshow and mysqldump commands
                           so one can use a remote host.
                           Thanks to Serge Colin and Gil Hildebrand, Jr.
                           for the suggestion.

                         - separated Mandatory Variables from Optional Variables
                           in the setup section, to make setup quicker.

v2.5 - March 1, 2002     - removed the password from the mysqldump and mysqlshow
                           lines if .cnf files are being used, since using the
                           user/pass on the command line shows up in 'ps'.
                           (Thus, it's highly advisable to use a .cnf file!)

                         - added $show_file_list_in_email var, to trim large emails.
                           The file list will not be included in the email unless
                           the var is set to 'yes'.

                         - Added functionality to backup LARGE systems, i.e:
                         - changed the tar method to tar a subdirectory with all
                           the files, so tar doesn't choke if there are too many
                           files. The subdir is removed once the tar file is made,
                           if $delete_text_files is set to yes. If not, the files
                           in old tar_dirs are cleaned out later by clean_old_files.

                         - modified 'ls -la' to use xargs so that large directories
                           don't choke.

v2.4 - June 20, 2001     - A bug fix of a bug fix. Oy.
                           Changed 'w_user' and 'w_password'
                           in the setup section back to 'user' and 'password'
                           to make it more consistent with .cnf files, and to
                           fix a bug I created when I changed it in v2.2
                           (with mysqldump looking for $user)
                           Now, we use $user and $password everywhere.
                           Thanks to our sharp eyed users!

v2.3 - June 5, 2001      - Changed the ~/ for the home directory in the vars
                           $cnf_file, $ENV{'MYSQL_UNIX_PORT'} and $mysql_backup_dir
                           to use absolute paths instead of the ~/. The ~/ didn't
                           work, and is a fine example of the need for testing :-)
                           I thought I was being clever and convenient, but I
                           actually didn't use it on my system (I used the absolute
                           paths instead.) Thanks to Rick Morbey in London.

v2.2 - May 25, 2001      - Bug fix; a typo. Changed 'user' and 'password'
                           in the setup section to 'w_user' and 'w_password'
                           so that the connect_to_db routine works.
                           Thanks to Glen Knoch.

v2.1 - May 23, 2001      - First public release of new Perl version
                         - bug fixes and added some options
                           . changed 'mysqlshow db %' for tables, to 'show tables'
                           . added prefixes to file deletes for safety
                           . fixed error in regex that checked for text file delete
                           . changed %e to %d in date string for file name
                           . added vars for nice, tar, gzip paths
                           . removed &error_message($error_text) from &mail_to,
                             to avoid recursive loop, since &error_message calls &mail_to
                           . fixed error in attached email file path
                           . commented out $dbh->{PrintError} = 1; and
                                           $dbh->{RaiseError} = 1; so that the script
                                           wouldn't die before emailing the error.
                           . made all vars in &do_backup 'my' to avoid conflicts

v2.0 - February 15, 2001 - completely rewritten as a Perl script
                           . added all core options

v1.0 - January 2, 2000   - written as a simple shell script

=cut

###################################################################################
# we place a 1; on the last line, because this file can now be 'required' in
# so that the script can be run from the web.

1;
