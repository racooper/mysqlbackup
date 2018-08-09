#!/usr/bin/perl
# mysql_backup.cgi
###################################################################################################
# POD Documentation

=head1 PROGRAM NAME AND AUTHOR

        MySQL Backup v3.7
        by Peter Falkenberg Brown
        peterbrown@worldcommunity.com
        http://worldcommunitypress.com
        Build Date: March 12, 2015
        Documentation Date: November 4, 2017

!!!! NOTE !!!! LEGAL DISCLAIMER:

I use this script every day, and it has been used every day
on multiple business servers that I manage, for many years.

It works, and I'm satisfied with it. However, I have NOT thoroughly
continued to test every method of use (i.e. under Windows, FTP, etc.)
so, I state here: USE AT YOUR OWN RISK. NO WARRANTY OFFERED.

Most especially: data integrity in a backup is EVERYTHING, so I cannot
take any responsibility for your use of this script. Your use of this
script specifically relieves me of any responsibility for your use of it.

That said, it works for me, using the standard Linux methodologies with 'mysqldump'.

!!!! END OF NOTE !!!!

=SYNTAX

        Run from crontabs or the shell with NO Parameters,
        or from the shell with 3 params, with a user prompt (see below).

        The var $one_db_prompt_yes_no has to be set to 'yes' or 'no'.
        If set to 'yes', cron use, or shell use to backup more than one database, will not work.

        ...........................................................................................
        As of v3.6 and v3.7, it now can be set up to work with command line parameters.

        The 'prompt' method works with THREE REQUIRED params on the command line, e.g.
        ./mysql_backup.one.cgi db_name [create | nocreate] [ inserts | noinserts ]

        FIRST: the name of ONE database to backup.

        SECOND: the word: 'create' or 'nocreate'
              'create' will add DROP and CREATE TABLE statements to each file.
              'nocreate' will leave them off, so that you can append data.

              => You can run the script TWICE, with different params, so that you can mix files
                 into one directory, for a complex restore, e.g. an append into a new WP install,
                 that also has additional plugin tables that need to be restored.

        THIRD: the word 'inserts' or 'noinserts'
              'inserts' will create ONE insert command per row, which is a slower restore,
                       but it will allow you to edit certain rows out of the text file,
                       e.g. an admin user row for a new WP install.

              'noinserts' will use the EXTENDED_INSERT method, which is much faster.

        FOURTH: an optional 'db_host' param.

        Examples:
        ./mysql_backup.one.cgi DB-NAME create noinserts
        ./mysql_backup.one.cgi DB-NAME nocreate inserts
        ...........................................................................................

        NOTE ON THE WEB AND WINDOWS FUNCTIONS:

        I have not tested the Web or Windows versions for quite a number of versions,
        but the Linux / Shell version has been tested a lot.
        (Thus, I cannot currently confirm the viability of the Web or Windows versions.)

= HOW TO RESTORE A DATABASE

        I've written a PHP script called "import.db.php" that will
        restore files with a user prompt and some parameters.

        => Or, you can use the method below.

        Because each table is in an individual .txt file, I use this method:
        1. Unzip and Untar the backup file. (a new subdir is created)
        2. If the backup file has more than one set of DB .txt files, I move the
                  .txt files for ONE database into a new, empty subdir
        3. I then run this command:

                  find . -name "*.txt" -print | sort | xargs -t --replace cat {} | mysql DBNAME

                  (where DBNAME is your database name)

        Note that this REPLACES any database tables of the same name, in that database.
        Normally, I would use this command against an EMPTY database.

= DATABASE INTEGRITY ISSUES

        I realize that it may seem convenient to do a mysqldump and restore with ONE .sql file,
        (and it is), but I like this 'one file per table' method because of the data integrity
        check done at the end of each table dump, when the script checks for the string, 'Dump Completed'.

        => There is some possibility that locking the entire database for one full
        "database backup" might prevent secondary tables being written to with relational IDs,
        thus breaking a relational transaction.

        That is, this script locks the database, backs up a table, and then repeats the process,
        so there's a bit of a gap between database locking for each table.

        However, even in a full database backup, I think it's possible that some applications
        might write to a table with an ID, and then write to another table with the parent ID,
        and theoretically find the database locked before it could write to the second table.

        Food for thought... However, I always backup databases in the wee hours of the morning,
        when there's no activity, so this doesn't tend to be an issue.

=PURPOSE

        Backs up mysql data safely, using
        'mysqldump', 'select to outfile' or 'normal record selection'.

        => Update: 2017: Note that I've used the "mysqldump" method for many years,
        and have NOT tested the other two methods for a long time.

        This is my attempt :-) to provide a reasonably
        full featured MySQL backup script that can be
        run from:

        1. Linux Crontab or Windows Scheduler
        2. the shell or command prompt

        3. the web (with password protection)
        (Note that I do not recommend running it from the web
        because of permission issues - however, some users
        do not have shell access. It depends upon the security
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
        did not work under MySQL v3.22.20a, and I was not able to
        determine when the % method came into being (under which
        version.) So, in order to make things work for earlier
        versions, I used 'show tables'.
        (I still use mysqlshow for database names.)

=COPYRIGHT

        Copyright 2000-2017 Peter Falkenberg Brown
        The World Community Press
        This program complies with the GNU GENERAL PUBLIC LICENSE
        and is released as "Open Source Software".
        NO WARRANTY IS OFFERED FOR THE USE OF THIS SOFTWARE

=BUG REPORTS AND SUPPORT

        Send bug reports to peterbrown@worldcommunity.com.

=OBTAINING THE LATEST VERSION

        ==> Get the most recent version of this program at:
              http://worldcommunitypress.com

        Email your feedback and ideas to:
        peterbrown@worldcommunity.com

=VERSION HISTORY
 (See the bottom of the file, since the version notes are getting longer.)

=cut

###################################################################################################

use DBI;
use POSIX qw(strftime);
use Time::Local;
use Cwd;
use File::Path;
use File::Basename;

#.............................................................
# if you are not going to use the script from the web
# you can comment out the next 3 CGI lines, if you do not have
# CGI.pm installed.

use CGI qw(:all -private_tempfiles escapeHTML unescapeHTML);
use CGI::Carp qw(fatalsToBrowser cluck);
$q = new CGI;

# ........................................................................

no strict 'refs';

# MANDATORY VARIABLE SET UP SECTION
# ........................................................................
# with v3.5 I moved the most commonly changed vars to this top section.
# START OF 'PERSONAL' VARS

# with v3.6, I added a prompt ability to specify one db from the command line.

$one_db_prompt_yes_no        = 'no';
                             # 'yes' or 'no
                             # allows program to be used with a promnpt to backup ONE database
                             # if set to 'yes', can ONLY be used with prompt
                             # that is, it won't work unattended, in a crontab

                             # syntax for command line:
                             # ./mysql_backup.cgi db_name [create | nocreate] [ inserts | noinserts ]

$admin_email_to              = 'your_email@your_domain.com';
                             # the email for error and notification
                             # messages, and the email recipient
                             # of the database files.

$admin_email_from            = 'your_email@your_domain.com';

$home_dir                    = $ENV{'HOME'};
$home_dir_last               = basename($home_dir);

$cnf_file                    = $home_dir . '/.my.cnf';
                             # use an absolute path; ~/ may not work

$server                      = `uname -n`;
                               chomp($server);

# this might be applicable:
# $server                      =~ s/\.your_domain\.com//;

$site_name                   = $server . ' (' . $home_dir_last . ')';

# the prefix makes the email easy to see:

$subject_prefix              = '[SYS] ';

$subject                     = $subject_prefix . "MySQL Backup Done for $site_name in :!:processing_time:!:";
                             # subject is the email subject
                             # if :!:processing_time:!: is placed in the subject line,
                             # it will get replaced with the minutes and seconds
                             # taken to do the backup

$mysql_backup_dir          = $home_dir . '/mysql_backup';

# or, use some other custom directory, e.g.:

# $mysql_backup_dir          = '/mysql/mysql_backup';

                             # use an absolute path; ~/ may not work
                             # the backup dir should normally be
                             # OUTSIDE of your web document root
                             # this directory must be writable by the script.
                             # If you backup from the web, then this directory
                             # should be set to 777. (see web notes above)

                             # !!! ......................................................
                             # !!! See code at end of personal vars
                             #     about using ONE database name on the command line,
                             #     which will create a SUBDIR OF THE CURRENT DIR
                             #     with the database name and a prefix

$db_host                     = 'localhost';
                             # 'localhost', or use a domain name or ip for databases on different machines
                             # NOTE:
                             # db_host is read in this order:
                             # (this is done to allow multi-account use from a shared version of this script)
                             #
                             # 1. if $one_db_prompt_yes_no = yes, and the optional host param is used,
                             #    then that version is used.
                             #
                             # 2. if $one_db_prompt_yes_no = yes, and no host param is used, it looks for the
                             #    host in the .my.cnf file. If it exists, that is used.
                             #
                             # 3. if $one_db_prompt_yes_no = yes, and the first two do not exist, it uses
                             #    the default above. If none exists, it fails.
                             #
                             # 4. If $one_db_prompt_yes_no != yes, then it uses the default value above.

$mysqldump_add_events_param  = 'yes';
                             # 'yes' or 'no'
                             # if 'yes', '--events' is added to the mysqldump parameters

                             # => This param was introduced in MySQL 5.1.8
                             # so it will not work in earlier versions.
                             # From 5.1.8 on, if you have an 'events' table,
                             # the script will complain unless you use the above param, (due to a bug in MySQL)
                             # which directs MySQL to dump the events table in the internal schema database.

$drop_table_param            = '--add-drop-table';
$create_table_param          = '--create-options';
                             # these are the defaults: to add the drop and create options

# $drop_table_param          = '--skip-add-drop-table';
# $create_table_param        = '--no-create-info';
                             # these can be used when you just want to append data
                             # you can run the script twice, with different params,
                             # to create two sets of data; one with drop/create, one without,
                             # and then mix and match the files, on an import.

$compare_table_file_count    = 'no';
                             # 'yes' or 'no' - this compares the number of records in the table
                             # against the number of 'INSERT INTO ' statements in the backup file
                             # this takes a second or so more, and could be erroneous, if rows are
                             # being added or deleted during the backup

$skip_extended_insert        = 'no';
                             # as of 3.6, this will modify the mysqldump params:
                             # --skip-extended-insert OR --extended-insert
                             # => --extended-insert is much faster;

                             # --skip-extended-insert creates one insert statement for each row,
                             # that the count method uses, and is much slower on restores of large tables.

      # we recheck this in the ONE DB block of code: this is just for the default

      if ( $skip_extended_insert eq 'yes' )
            {
            # we skip the extended insert, because we want one insert command per row

            $extended_insert_method = '--skip-extended-insert';
            }
      else
            {
            # we use the extended insert because we don't count the rows (i.e. the 'INSERT' commands)

            $extended_insert_method = '--extended-insert';
            }

@selected_databases          = qw[];
                             # place the names of your databases here,
                             # separated by spaces, or set
                             # process_all_databases to 'yes'

                             # !!! NOTE: the foreach $db_main ( @databases ) loop
                             # has code to automatically skip the databases
                             # 'information_schema' and 'performance_schema'

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
                             # Leave it blank if you do not want to use it., i.e:
                             # qw[];

@skip_tables                 = qw[];
                             # skip_tables is always parsed.
                             # Leave it blank if you do not want to use it., i.e:
                             # qw[];
                             # This may be an issue with duplicate table names
                             # in multiple databases -- it is on the todo list.

###################################################################################################
# END OF 'PERSONAL' VARS AND ONE DB PARAM FUNCTIONS
###################################################################################################

# Note: the file is ALWAYS save locally, whether or not
# you set ftp_backup and/or email_backup to 'yes'

$ftp_backup                  = 'no';
# use Net::FTP;
                             # set $ftp_backup to 'yes' or 'no'.
                             # => NOTE
                             # If you set it to 'yes',
                             # you will need to install Net::FTP

                             # If you do not install Net::FTP,
                             # you MUST place a comment (#) in front of
                             # the 'use Net::FTP' line above

                             # You will also have to set the variables
                             # for ftp host, etc (below)

$email_backup                = 'no';
# use MIME::Lite;
                             # set $email_backup to 'yes' or 'no'
                             # => NOTE
                             # If you set it to 'yes'
                             # you will need to install MIME::Lite

                             # If you do not install MIME::Lite,
                             # you MUST place a comment (#) in front of
                             # the 'use MIME::Lite' line above

                             # See Windows Users Note below
                             # about MIME::Lite (You need it.)

                             # Go to search.cpan.org to get the libs.

# Microsoft Windows options
# ..................................

# use Net::SMTP;
                             # COMMENT out the use Net::SMTP line
                             # if you are not using smtp

                             # NOTE for Windows Users:
                             # - adjust the $find_commands section below
                             #   (set $find_commands to no)
                             # - you will need to install Windows versions
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
                             #   -- do not bother installing them unless you receive
                             #      an error message - I only tested this on Win98.

                             # - set $chmod_backup_file to 'no'
                             # - set the smtp items in this section
                             # - install MIME::Lite and uncomment the
                             #   use MIME::Lite line above
                             # - the tar z switch and the tar/gzip pipe method
                             #   do not work on Windows
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
                             # set this to '0' if you do not need to check the
                             # length of your shell command strings
                             # (see the ` backtick commands)

$smtp_host                   = 'your.mailserver.domain.or.ip';
                             # set only if you set send_method to 'smtp'
                             # (useful for Windows)

$send_method                 = 'sendmail';
                             # set $send_method to 'sendmail' or 'smtp';
                             # (often set to smtp for WinX)

# admin_email_to             - this var is now at the top of the file
# admin_email_from           - this var is now at the top of the file

# $mailprog                  = '/usr/lib/sendmail -t -oi';
# $mailprog                  = '/usr/sbin/sendmail -t -oi';

$mailprog                    = "/usr/sbin/sendmail -t -oi -oem -r $admin_email_from";

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

#.............

# these params have been moved up to the personal vars section

     # @selected_databases
     # $process_all_databases
     # @skip_databases
     # @skip_tables

#.............

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

                             # I have added functionality that allows the script
                             # to be run from the web, because some users
                             # do not have shell access.

                             # if $password_location is set to 'from_web',
                             # then \n chars are translated to <br> and also, a
                             # "Content-type: text/html\n\n"; is printed to sdtout.

                             # note that you will have to either run the
                             # .cgi file from your web tree, or use a 'stub' file
                             # which I recommend. (see my web page for an example).

                             # NOTE!!! RUNNING FROM THE WEB is predicated
                             # on a number of issues:

                             # - web logins do not use a cnf file, since
                             #   the cnf file would be required to be world
                             #   readable, and because we have to check
                             #   the user login anyway, against mysql.

                             # - the backup directory ($mysql_backup_dir)
                             #   must be writeable by the web server
                             #   (since it is outside the webtree and the
                             #   the script requires a login, the risk
                             #   is controlled -- however, if your server
                             #   co-exists with other virtual servers,
                             #   you should make sure that they cannot ftp
                             #   outside their own home directory.)

                             # - set $chmod_backup_file to 'no'
                             #   since files will be owned by web server
                             #   and if they are set to 600 you will not be able
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
                             #   If you have an ssl url, use it!
                             #   It is worth it to encrypt your database
                             #   username and password.
                             #   (Just run the script prefixed by
                             #    https://yourdomain.com/script_name.cgi)

                             #   SSL Note2: Even if you do not OWN an SSL Cert,
                             #   you can often use the https ssl syntax;
                             #   the web server will encrypt it anyway;
                             #   it simply warns you that you do not have
                             #   an ssl cert. What do you care :-)?
                             #   (You are the one running the script.)

                             #   The Cert/Browser marriage is a SCAM
                             #   in my opinion. Since the encryption
                             #   happens anyway, the stupid warning box
                             #   should be eliminated. Maybe a Congressional
                             #   sub-committee should investigate it :-).

                             #   If you want a CHEAP, FAST, cert, go to:
                             #   http://instantssl.com (approx. $40!)

$login_script_name           = 'mysql_backup_login.cgi';
                             # this is the name of the script that is used
                             # for web login -- either the real script,
                             # or a stub script
                             # If you are not using the web option,
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

# db_host                    - this var is now at the top of the file

$db_port                     = '3306';
                             # database connection variables

# cnf_file                   - this var is now at the top of the file

$cnf_group                   = 'client';
                             # you can store your user name and
                             # password in your cnf file
                             # or.. you can place the username and
                             # password in this file,
                             # but you should set this to 700 (rwx------)
                             # so that it is more secure.
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

# site_name                  - this var is now at the top of the file

# subject                    - this var is now at the top of the file

# mysql_backup_dir           - this var is now at the top of the file

# MANDATORY UTILITY PATH SETTINGS
# ..................................

$find_commands               = 'yes';
                             # Set $find_commands to 'yes' or 'no'
                             # depending upon whether you want to have the program
                             # search for the command line utilities.
                             # This is a weak attempt at a ./configure concept.
                             # Do we need it, since one can edit the lines below?
                             # Probably not. :-)

                             # WINDOWS USERS: NOTE:
                             # Set $find_commands to 'no' and edit the
                             # path vars directly -- whereis does not exist
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
      $ionice_cmd            = '/usr/bin/ionice';

      $tar_cmd               = '/bin/tar';
      $gzip_cmd              = '/bin/gzip';

      # pigz is multi-threaded; might be worthwhile
      # $gzip_cmd            = '/usr/bin/pigz';

      $bzip2_cmd             = '/usr/bin/bzip2';
      $ls_cmd	           = '/bin/ls';

      $tail_cmd              = '/usr/bin/tail';
      $grep_cmd              = '/bin/grep';

      # windows examples (use a short directory - see windows notes above)
      # NOTE!! for Windows, you MUST include the .exe since the script
      # checks to see if the file exists before running.

      # $mysqlshow_cmd         = '/bin/mysqlshow.exe';
      # $mysqldump_cmd         = '/bin/mysqldump.exe';
      # $nice_cmd              = '/bin/nice.exe';
      # $ionice_cmd            = ''; # ? not sure about this one.
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

$compress_method             = '';
                             # (blank) '', or 'z_switch' or 'pipe_method'

                             # NOTE!!! The z switch and the pipe method
                             # do not work on Windows

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
                             # If set to 'no', the script will not check
                             # for bzip2 at all (so you do not need it on
                             # your disk)

$gzip_args                   = '-9v';
                             # set gzip arguments if you like
                             # -1 --fast  compress faster
                             # -9 --best  compress better

$bzip_args                   = '-9v';
                             # set bzip2 arguments if you like
                             # -1 .. -9   set block size to 100k .. 900k

$nice_params                 = '-n19';

$ionice_params               = '-c2 -n7';

###################################################################################
# OPTIONAL VARIABLES SET UP SECTION
# (You may not need to change the vars below)
###################################################################################

$show_file_list_in_email     = 'yes';
                             # for large directories this should be set to 'no'

$print_stdout                = 'yes';
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
# you do not need to set these variables.

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

$ftp_dir                     = '/some_dir/mysql_backups/';
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

$delete_old_ftp_files        = 'no';
                             # delete old ftp files or not

$number_of_files_to_save     = 5;
                             # Number of files to keep on remote ftp server.
                             # Note that I do not use date processing to keep
                             # files older than a certain time, because of potential
                             # differences with timezones and remote server time
                             # changes. Since we cannot control what the remote time
                             # is (unlike the local server), I used the concept of
                             # keeping a certain number of files in the remote ftp
                             # directory, using the list of files sorted by most
                             # recently uploaded first. Thus, if you keep 3, the
                             # the 3 that will be saved are the most recent 3.
                             # This number cannot be less than 1.

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
                             # but some hosts do not provide access to
                             # mysqldump or 'select into outfile'
                             # (sometimes mysqldump is on a different
                             # server, and sometimes a user does not have
                             # 'file_privileges' for mysql.)

                             # NOTE: for LARGE data sets, 'normal_select'
                             # may not work well, because of memory problems

$mysqldump_success_string  = 'Dump completed';
                             # This string is looked for, using 'tail', at the end of each
                             # sql .txt file, to make sure that the dump was completed successfully

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
# YOU NORMALLY WILL NOT HAVE TO MODIFY ANYTHING BELOW THIS LINE
###################################################################################

###################################################################################
### START OF ONE DATABASE PROMPT SECTION
###################################################################################

# SET UP FOR 'ONE' VERSION OF SCRIPT

# scenarios
#     . import all tables into empty database - drop/create okay
#     . import all tables with no drop/no create -- i.e. append all

#     . import some table with drop/create table; others with no drop/no create -- just append data
#           this is done manually, by doing two types of export, and then combining files into one directory.
#..................................................................................................

# params:
# db_name [create | nocreate] [ inserts | noinserts ] [db_host]

$clear = `clear`;

$mysql_one_header = qq~

      MySQL_Backup:

      You are seeing this screen because the script has been set to the
      PROMPT METHOD and you did not use at least 3 command line parameters.

      The 'prompt' method works with THREE REQUIRED params on the command line, e.g.
      ./mysql_backup.one.cgi db_name [create | nocreate] [ inserts | noinserts ]
      and ONE OPTIONAL 4th parameter (db_host).

      FIRST: the name of ONE database to backup.

      SECOND: the word: 'create' or 'nocreate'
            'create' will add DROP and CREATE TABLE statements to each file.
            'nocreate' will leave them off, so that you can append data.

            => You can run the script TWICE, with different params, so that you can mix files
               into one directory, for a complex restore, e.g. an append into a new WP install,
               that also has additional plugin tables that need to be restored.

      THIRD: the word 'inserts' or 'noinserts'
            'inserts' will create ONE insert command per row, which is a slower restore,
                     but it will allow you to edit certain rows out of the text file,
                     e.g. an admin user row for a new WP install.

            'noinserts' will use the EXTENDED_INSERT method, which is much faster.

      FOURTH: the database host (e.g. 'localhost', an IP, or other host name that will work.)
        NOTE: with accounts that have been set up with a .my.cnf file with a HOST VALUE, you do NOT
              need to type the fourth parameter.

      Examples:
      ./mysql_backup.one.cgi DB-NAME create noinserts
      ./mysql_backup.one.cgi DB-NAME nocreate inserts

      ./mysql_backup.one.cgi DB-NAME nocreate inserts host_name_or_ip

~;

$db_host_param = '';

if ( ( @ARGV == 3 || @ARGV == 4 ) && $one_db_prompt_yes_no eq 'yes' )
      {
      print $clear;

      $selected_databases[0] = $ARGV[0];
      $sql_create_no_create  = $ARGV[1];
      $sql_insert_no_insert  = $ARGV[2];
      $db_host_param         = $ARGV[3];

      my $one_selected_database = $selected_databases[0];
      #.......................................................

      if ( $sql_create_no_create eq 'create' )
            {
            $drop_table_param   = '--add-drop-table';
            $create_table_param = '--create-options';
            }
      elsif ( $sql_create_no_create eq 'nocreate' )
            {
            $drop_table_param   = '--skip-add-drop-table';
            $create_table_param = '--no-create-info';
            }
      else
            {
            print $mysql_one_header;
            print "\nError! Wrong parameter on 'sql_create_no_create'. You typed: [$sql_create_no_create]\n\n";
            exit;
            }

      #.....................................

      if ( $sql_insert_no_insert eq 'inserts' )
            {
            $skip_extended_insert = 'yes';
            }
      elsif ( $sql_insert_no_insert eq 'noinserts' )
            {
            $skip_extended_insert = 'no';
            }
      else
            {
            print $mysql_one_header;
            print "\nError! Wrong parameter on '$sql_insert_no_insert'. You typed: [$sql_insert_no_insert]\n\n";
            exit;
            }

      if ( $skip_extended_insert eq 'yes' )
            {
            # we skip the extended insert, because we want one insert command per row

            $extended_insert_method = '--skip-extended-insert';
            }
      else
            {
            # we use the extended insert because we don't count the rows (i.e. the 'INSERT' commands)

            $extended_insert_method = '--extended-insert';
            }

      #.....................................
      #.....................................

      $process_all_databases = 'no';
      @skip_databases        = qw[];
      @skip_tables           = qw[];

      $site_name            .= ' (' . $selected_databases[0] . ')';
      $subject               = $subject_prefix . "MySQL Backup Done for $site_name in :!:processing_time:!:";

      $pwd = cwd();

      $mysql_backup_dir      = $pwd . '/mysql_backup_ONE_' . $selected_databases[0];

      # select correct host
            # db_host is read in this order:
            # (this is done to allow multi-account use from a shared version of this script)
            #
            # 1. if $one_db_prompt_yes_no = yes, and the optional host param is used,
            #    then that version is used.
            #
            # 2. if $one_db_prompt_yes_no = yes, and no host param is used, it looks for the
            #    host in the .my.cnf file. If it exists, that is used.
            #
            # 3. if $one_db_prompt_yes_no = yes, and the first two do not exist, it uses
            #    the default above. If none exists, it fails.
            #
            # 4. If $one_db_prompt_yes_no != yes, then it uses the default value above.

      if ( $db_host_param ne '' )
            {
            # use $db_host_param
            $db_host = $db_host_param;
            }
      elsif ( $db_host_param eq '' and -e $cnf_file )
            {
            # use host in cnf file, if exists, else use default

            $host_line = `grep -m 1 host $cnf_file`;
            chomp($host_line);

            if ( $host_line ne '' )
                  {
                  ($host_atom, $host_value) = split('=', $host_line);
                  $host_value =~ s/\"//g;
                  $host_value =~ s/\'//g;

                  $db_host = $host_value;
                  }
            }
      else
            {
            # use default above (already set)
            }

      #............................................................................................
      # display output and ask for confirmation

      print qq~

MySQL_Backup:

Your backup will proceed as follows:

             MySQL cnf file - $cnf_file
              Database Host - $db_host
          Selected_Database - $one_selected_database

       Sql_Create_No_Create - $sql_create_no_create
           Drop_Table_Param - $drop_table_param
         Create_Table_Param - $create_table_param

       Sql_Insert_No_Insert - $sql_insert_no_insert
       Skip_Extended_Insert - $skip_extended_insert
     Extended_Insert_Method - $extended_insert_method

       Site_Name / Database - $site_name
                        Pwd - $pwd
           Mysql_Backup_Dir - $mysql_backup_dir

~;

      # check user input
      #.............................

      $| = 1;

      # check for Unix or DOS, for console input

      if (-e "/dev/tty")
           {$console = "/dev/tty";}
      else {$console = "con";}

      unless ( open(USER_PROMPT, "$console"))
          {
          print "Can't open console: $!\n";
          exit;
          }

      #..............................

      $process = "false";

      while ($process eq "false")
            {
            print "\nDo you wish to continue?  (enter only 'y' or 'n') ";

            $continue = <USER_PROMPT>;
            chop $continue;
            $continue = lc($continue);

            if ($continue eq "y")
                  {
                  $process = "true";
                  }
            elsif ($continue eq "n")
                  {
                  $process = "false";
                  close(USER_PROMPT);
                  print "\n";
                  exit;
                  }
            else
                  {
                  $process = "false";
                  }
            }

      close(USER_PROMPT);

      # check if mysql is working with selected host

      $host_check = `mysqlshow -h $db_host 2>&1`;

      if ( $host_check =~ /Can\'t connect/i )
            {
            &error_message(qq~\n\nMySQL is not working on Host: $db_host.\n\n~);
            }

      # create custom directory
      #.........................................................................

      unless ( -e "$mysql_backup_dir" )
            {
            mkdir $mysql_backup_dir, 0755;
            chmod 0755, $mysql_backup_dir;
            }

      unless ( -e "$mysql_backup_dir" )
            {
            &error_message(qq~Error! CUSTOM DIR: $mysql_backup_dir was not created.~);
            }

      }
elsif ( @ARGV != 3 && @ARGV != 4 && $one_db_prompt_yes_no eq 'yes' )
      {
      print $clear;
      print $mysql_one_header;
      exit;
      }
elsif ( @ARGV >= 1 && $one_db_prompt_yes_no eq 'no' )
      {
      print $clear;
      print "\n\nDo not type any parameters if you have the 'one_db_prompt' var set to 'no'.\n\n";
      exit;
      }
else
      {
      print $clear;
      }

###################################################################################
### END OF ONE DATABASE PROMPT SECTION
###################################################################################

$start = time;

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
            $clear = `clear;pwd;`;
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
      print qq~Error! You have not setup your email parameters correctly.~;
      exit;
      }

# automatic utility setup
#................................
# CMD_ARRAY NOTE (below):
# Note that the automatic method of finding the commands that is used here
# creates variables names that match the commands. Since the script uses the
# default variable names listed in the array, you should not edit the array
# unless you also change the var names in the script.

# DO NOT EDIT THIS CMD_ARRAY unless you know what you are doing :-).

@cmd_array = qw[mysqlshow mysqldump nice ionice tar gzip bzip2 ls tail grep];

# see section below that adds params to nice and ionice commands

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
      unless ( -e $$cmd_name ){&error_message(qq~Error! $$cmd_name was not found.~);}
      }

# add params to nice and ionice commands

$nice_cmd   = "$nice_cmd $nice_params";
$ionice_cmd = "$ionice_cmd $ionice_params";

# BEGIN BACKUP PROCESS
#....................................

$body_text = '';

unless ( -e "$mysql_backup_dir" )
      {
      &error_message(qq~Error! $mysql_backup_dir does not exist.~);
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
      &error_message(qq~Error! $mysql_backup_dir/$tar_dir was not created.~);
      }

chdir ("$tar_dir");

$msg = "\nProcessing Backups Using " . uc($backup_type) .
       " in\n$mysql_backup_dir/$tar_dir\n\n";

if ( $print_stdout eq 'no' )
      {
      $msg .= qq~Screen Output (STDOUT) is turned OFF,
      so you will not see much until the script is done.\n\n
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
# note that if $one_db_prompt_yes_no eq 'yes', then
# even if process_all_databases is set to yes, the routine
# changes it to 'no'.
# in other words, process all databases always uses the default $db_host
# even if the cnf file has a different one

if ( $process_all_databases eq 'yes' )
        {
        if ( $password_location eq 'cnf' )
            {
            $cmd = qq~$mysqlshow_cmd --defaults-extra-file=$cnf_file --host=$db_host~;
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
        if ( $db_main =~ /lost\+found/ ) {next;}

        # clean up line item
        $db_main =~ s/\|//g;
        $db_main =~ s/\s+//g;

        if ( $db_main eq 'information_schema' ) {next;}
        if ( $db_main eq 'performance_schema' ) {next;}

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
                                                  Cannot execute the query: $DBI::errstr~);

        $rv = $sth->execute or &error_message(qq~Error!\n
                               Cannot execute the query: $DBI::errstr~);

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

      $cmd = qq~$nice_cmd $ionice_cmd $tar_cmd $tar_options -c -z -f $backup_gzip_file $tar_dir~;
      &cmd_length($cmd) if $max_cmd > 0;
      $compress_output = `$cmd`;
      }
elsif ( $compress_method eq 'pipe_method' )
      {
      # pipe through gzip or bzip2
      &message('b',qq~\nNow Compressing via a Tar / $gzip_type Pipe ...\n~);

      $cmd = qq~$nice_cmd $ionice_cmd $tar_cmd $tar_options -c -f - $tar_dir | $gzip_cmd $gzip_args > $backup_gzip_file~;
      &cmd_length($cmd) if $max_cmd > 0;
      $compress_output = `$cmd`;
      }
else
      {
      # use two step method
      &message('b',qq~\nNow Compressing via Tar followed by $gzip_type ...\n~);

      $cmd = qq~$nice_cmd $ionice_cmd $tar_cmd $tar_options -c -f $backup_tar_file $tar_dir~;
      &cmd_length($cmd) if $max_cmd > 0;
      $compress_output = `$cmd`;

      # delete text files now, to save disk space
      if ( $delete_text_files eq 'yes' )
            {
            &delete_text_files;
            # set delete_text_files to 'no'
            # so that the script does not try to do it again, below
            $delete_text_files = 'no';
            }

      &message('b',qq~\nNow Compressing with $gzip_type ...\n~);

      $cmd = qq~$nice_cmd $ionice_cmd $gzip_cmd $gzip_args $backup_tar_file~;
      &cmd_length($cmd) if $max_cmd > 0;
      $compress_output .= `$cmd`;
      }

&message('b',$compress_output);

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

if ( @ARGV == 3 && $one_db_prompt_yes_no eq 'yes' )
      {
      # do not clean old files
      }
else
      {
      &clean_old_files("$mysql_backup_dir");
      }

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
               &error_message(qq~Error! Net::FTP could not connect to $ftp_host : $@\n~);

        # Login with the username and password
        &message('b',"\nLogging in with FTP.\n");

        $ftp->login("$ftp_user", "$ftp_password") or
              &error_message(qq~Error! Net::FTP could not login to $ftp_host : $!\n~);

        # set the type to binary
        &message('b',"\nSetting FTP transfer to binary.\n");

        $ftp->binary or
              &error_message(qq~Error! Net::FTP could not set the type to binary for $ftp_host : $!\n~);

        # Change to the right directory
        &message('b',"\nChanging to FTP dir: $ftp_dir\n");

        $ftp->cwd("$ftp_dir") or
              &error_message(qq~Error! Net::FTP could not change to $ftp_dir at $ftp_host : $!\n~);

        #......................................................................

        if ( $delete_old_ftp_files eq 'yes' )
            {
            # First check to see if file already exists
            # and process deletions of old files
            &message('b',"\nChecking to see if file exists already: $upload_gzip_filename\n... and deleting old files.\n");

            # used 'ls' here instead of 'dir' because I only wanted the filename

            $check_pwd = $ftp->pwd() or &error_message(qq~Error!\nCould not check ftp dir with "pwd".~);;

            if ( "$check_pwd" ne "$ftp_dir" )
                  {
                  &error_message(qq~
                  Error! Delete Old FTP Files function in WRONG Directory. : $!

                  Setup Dir: $ftp_dir
                  Current Dir: $check_pwd

                  Possibly the script ftp directory was not specified with
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
                      &error_message(qq~Error.\nThe variable 'Number of Files to Save' cannot be less than 1.~);
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
              &error_message(qq~Error! Net::FTP could not upload $backup_gzip_file at $ftp_host : $!\n~);

        # Get file size to see if the file uploaded successfully
        &message('b',"\nChecking File Size of Remote file $upload_gzip_filename at $ftp_host\n");

        $uploaded_size = $ftp->size("$upload_gzip_filename") or
                 &error_message(qq~Error! Net::FTP could not get the size of $upload_gzip_filename at $ftp_host : $!\n~);

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
              &error_message(qq~Error! Net::FTP could not disconnect from $ftp_host : $!\n~);
        }

# calculate time spent and add to subject line
#............................................................................

$end        = time;
$seconds    = $end - $start;

$minutes    = $seconds / 60;
$minutes    = sprintf("%.2f",$minutes);

$processing_time = "$minutes minutes ($seconds seconds)";

$subject    =~ s/:!:processing_time:!:/$processing_time/;

&message('b', "\nProcessed Backup in $minutes minutes ($seconds seconds.)\n\n");

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
            # use this for windows machines that do not have sendmail

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

# I do not use &message here since the email has already gone out,
# and because it's perhaps good to give even minimilistic final output,
# even when $print_stdout is set to 'no'

print "\n\nDone! Exiting from MySQL Backup Script.\n\n";

exit;

###################################################################################################
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
            &error_message(qq~Error!<p>The Username and Password cannot be
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
###################################################################################################
# logout
sub logout
{

warn $DBI::errstr if $DBI::err;
if ( $dbh ){$rcdb = $dbh->disconnect;}

}
###################################################################################################
# error_message
sub error_message
{

# &error_message($error_text);

my ($error_text) = @_;

my $subject = $subject_prefix . "$site_name MySQL Backup Error";

print qq~\n$subject\n$error_text\n~;

if ( $send_method eq 'smtp' )
      {
      # use this for windows machines that do not have sendmail

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
###################################################################################################
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
###################################################################################################
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
###################################################################################################
# mail_to
sub mail_to
{

# &mail_to($email_to, $email_from, $subject, $mail_body, $reply_to);

my ($email_to, $email_from, $subject, $mail_body, $reply_to) = @_;

if ( $reply_to !~ /\@/ ){$reply_to = $email_from;}

open (MAIL, "|$mailprog") || die print qq~Error!\n\nCannot open $mailprog!~;

print MAIL "To: $email_to\n";
print MAIL "From: $email_from\n";
print MAIL "Subject: $subject\n";
print MAIL "Reply-To: $reply_to\n";
print MAIL "\n";
print MAIL "$mail_body";
print MAIL "\n";
close (MAIL);

}
###################################################################################################
# do_backup
sub do_backup
{

my ($db_main, $table_name, $table_engine) = @_;
my $response_text = '';

my $sth, $rv, $backup_file, $mysqldumpcommand;
my $backup_str, $row_string, $field_value;
my $len_field_terminate;
my @row;
my $mysql_dump_string_check = '';
my $table_name_count        = 0;
my $table_file_count        = 0;

$backup_file = $file_prefix . "." . $date_text . "_" . $db_main . "." . $table_name . "." . $mysql_dump_file_ext;
$full_file   = "$mysql_backup_dir/$tar_dir/$backup_file";

#..............................................................................
# check if db or table has space in name

if ( $db_main =~ /\s+/ || $table_name =~ /\s+/ )
      {
      my $msg = qq~Alert! [$db_main] or [$table_name] has a SPACE in the name.
                   Do you want to fix that name?
                  ~;

      my $msg_subject = "MySQL Backup SPACE IN NAME ALERT! for $site_name";

      &mail_to($admin_email_to, $admin_email_from, $msg_subject, $msg, $admin_email_from);
      }

#..............................................................................
# set up arrays for mysqldump system calls
# this is where you can modify parameters

@mysqldump_all_params_array   = (
                                 "$nice_cmd",
                                 "$ionice_cmd",
                                 "$mysqldump_cmd",
                                );

@mysqldump_cnf_array          = (
                                 "--defaults-extra-file=$cnf_file",
                                );

@mysqldump_no_cnf_array       = (
                                 "--user=$user",
                                 "--password=$password",
                                );

@mysqldump_innodb_array       =   (
                                   "--single-transaction",
                                   "--routines",
                                   "--triggers",
                                  );

@mysqldump_myisam_array       =   (
                                   "--lock-tables",
                                  );

@mysqldump_main_params_array  =   (
                                   "--host=$db_host",
                                   "--skip-opt",
                                   "--set-charset",
                                   "--disable-keys",
                                   "$drop_table_param",
                                   "$create_table_param",
                                   "--add-locks",
                                   "--quick",
                                   "--complete-insert",
                                   "$extended_insert_method",
                                   "--result-file='$full_file'",
                                  );

@mysqldump_db_array           = (
                                 "'$db_main'",
                                 "'$table_name'",
                                );

#..............................................................................

if ( $password_location eq 'cnf' )
      {
      push(@mysqldump_all_params_array, @mysqldump_cnf_array);
      }
else
      {
      push(@mysqldump_all_params_array, @mysqldump_no_cnf_array);
      }

#..............................................................................

if ( $table_engine eq "InnoDB" )
      {
      &message('b',"\n$space_line $space_line  Backing up InnoDB Table...\n\n");

      push(@mysqldump_all_params_array, @mysqldump_innodb_array);
      }
else
      {
      push(@mysqldump_all_params_array, @mysqldump_myisam_array);
      }

#..............................................................................
# now add final params

if ( $mysqldump_add_events_param eq 'yes' )
      {
      push(@mysqldump_all_params_array, '--events');
      }

push(@mysqldump_all_params_array, @mysqldump_main_params_array);
push(@mysqldump_all_params_array, @mysqldump_db_array);

#..............................................................................
# get count of table records

if ( $compare_table_file_count eq 'yes' && $skip_extended_insert eq 'yes' )
      {
      ( $table_name_count ) = $dbh->selectrow_array("select count(*) from `$table_name`")
                              or &error_message(qq~Error!\n\nCannot get data: $DBI::errstr~);
      }

#..............................................................................

if ( $backup_type eq 'mysqldump' )
      {
      # $mysqldump_system_command = join(' ', @mysqldump_all_params_array);
      # print "\n\n$mysqldump_system_command\n\n";

      system("@mysqldump_all_params_array");
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
                    Cannot backup data: $DBI::errstr~);
      }
else
      {
      unless ( open(FILE, ">$full_file" ))
              {
              &error_message(qq~Error!\n
              Cannot open File $backup_file.~);
              }

      $sth  = $dbh->prepare("select * from $table_name")
              or &error_message(qq~Error!\n
              Cannot do select for backup: $DBI::errstr~);

      $rv   = $sth->execute
              or &error_message(qq~Error!\n
              Cannot execute the query: $DBI::errstr~);

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
      chmod 0600, "$full_file";
      }

$filesize = -s "$full_file";
$response_text .= ' ' x 13 . "File: ($filesize bytes) [$backup_file]\n\n";

unless ( -e "$full_file" )
      {
      &error_message(qq~Error! "$full_file" was not created!~);
      }

# check mysqldump files for completion
#............................................................

if ( $backup_type eq 'mysqldump' )
      {
      # check for completion string
      #......................................................

      my $mysql_dump_string_check = `$tail_cmd -c 500 "$full_file" | $grep_cmd "$mysqldump_success_string"`;

      # check ending string

      if ( $mysql_dump_string_check =~ / $mysqldump_success_string / )
            {
            # all is well

            &message('b',"$space_line $space_line  $mysql_dump_string_check\n");
            }
      else
            {
            # mysqldump file did not complete

            my $mysqldump_error_subject = "MySQL Backup: COMPLETION ERROR! $site_name";

            my $mysqldump_error = qq~
            Error! The file: [$full_file]
            did not contain the phrase: $mysqldump_success_string
            Thus: the table was NOT backed up successfully.

             Details

                File: [$full_file]
              Server: [$site_name]
            Database: [$db_main]
               Table: [$table_name]

            ~;

            # email alert, but keep going

            &mail_to($admin_email_to, $admin_email_from, $mysqldump_error_subject, $mysqldump_error, $admin_email_from);
            }

      #.......................................................................
      # check table_file_count against table_name_count
      # $table_name_count
      # $table_file_count

      if ( $compare_table_file_count eq 'yes' && $skip_extended_insert eq 'yes' )
            {
            $table_file_count = `$grep_cmd -c 'INSERT INTO ' "$full_file"`;

            if ( $table_file_count == $table_name_count )
                  {
                  # all is well

                  &message('b',"$space_line $space_line  Table Count: $table_name_count - File Count: $table_file_count\n");
                  }
            else
                  {
                  # counts are off; error

                  my $mysqldump_error_subject = "MySQL Backup: COUNT MISMATCH!!! $site_name";

                  my $mysqldump_error = qq~
                  Alert!!!

                  The Table Count and File Count of Rows did not match,
                  but the mysqldump completed successfully.

                  Rows may have changed because of deletions or insertions.

                  Table Count: $table_name_count
                   File Count: $table_file_count

                      File: [$full_file]
                    Server: [$site_name]
                  Database: [$db_main]
                     Table: [$table_name]

                  ~;

                  # email alert, but keep going

                  &mail_to($admin_email_to, $admin_email_from, $mysqldump_error_subject, $mysqldump_error, $admin_email_from);
                  }
            }
      }

return ($response_text);

}
###################################################################################################
# delete_text_files
sub delete_text_files
{

&message('b', qq~\nRemoving Directory: $mysql_backup_dir/$tar_dir\n~);

chdir ("$mysql_backup_dir");

# this requires File::Path

$removed_dir = rmtree($tar_dir,0,1);

if ( -e "$tar_dir" )
      {
      &error_message(qq~Error! Tar Dir: $tar_dir was not deleted!<br>
                        Output results:<br>
                        $removed_dir
                       ~);
      }
else
      {
      &message('b', "Removed temporary Tar Dir: $mysql_backup_dir/$tar_dir\n");
      }

}
###################################################################################################
# clean_old_files
sub clean_old_files
{

# $mysql_backup_dir
# $seconds_to_save  = $increments_to_save * $seconds_multiplier;

# call this subroutine with the '$full_dir_name'

my ($full_dir_name) = @_;

unless ( -e $full_dir_name )
      {
      &message('b',"\nCould NOT Clean Old Files - $full_dir_name does not exist.\n");
      return;
      }

&message('b',"\nCleaning Old Files\n");

$save_time  = time() - $seconds_to_save;
$deleted_files = 0;

&message('b', "\nRemoving Files Older than $increments_to_save $increment_type\n");

opendir (DIRHANDLE, $full_dir_name);

# we use $file_prefix to make it safer; we do not want to delete
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

        - chmod does not mean much on Winx (I use the Perl internal chmod
          so that utility does not have to be imported anyway).

        - tar will not filter through gzip

        1. UnxUtils (bzip2, gzip, ls, tar)
        ----- http://www.weihenstephan.de/~syring/win32/UnxUtils.html
              !!!(cannot pipe to gzip, cannot create tar.gz)

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
              !!!(cannot pipe to gzip, cannot create tar.gz)
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

        DO NOT USE: C D e E F G g h k l n O P r R s t T u V z +
        They usually work under Linux, but not necessarily under WinX.

        I specifically had problems with 'e' and 'l'.
        They did not work on a Win2000 machine I tested them on.
        I had to change them from 'e' to 'd' and 'l' to 'I'.

        Note that 'e' and 'l' would not normally be used for
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
        Rather than list all the code definitions, here is a url to visit a
        Unix manpage site, such as: http://unixhelp.ed.ac.uk/CGI/man-cgi
        (type in 'strftime').

        Or, from the shell prompt, type in 'man strftime'.
        .......................................................................

###################################################################################################

=VERSION HISTORY

v.3.7 - March 12, 2015
                         - added: $subject_prefix = '[SYS] ' to prepend to $subject where it occurs
                           for easy subject line scanning in email inboxes.

                         - added: if ( $db_main =~ /lost\+found/ ) {next;} to mysqlshow db loop

                         - added capability get $db_host from .my.cnf file, or user parameter

                         - added $variable to pull home dir from $ENV var $HOME,
                           for directory for .my.cnf. This allows more than one user to use this script,
                           assuming that the script is stored in a central location in their path.

v.3.6 - September 16, 2014
                         - added function to backup ONE database, with the dbname supplied
                           as a command line parameter, with two additional params to control
                           the insertion of drop table / create table directives and the insertion
                           of one INSERT command per row. See POD notes at top.

                         - IN POD Notes at top:
                         - added note on syntax
                         - added note on how to do restores, with a 'find' command.
                         - added notes about command line usage with ONE database

                         - IN PERSONAL VARS SECTION:

                         - NOTE: I\'ve removed "--add-drop-table" from the params,
                           because in certain types of upgrades, one doesn\'t want to drop the table,
                           and, in empty databases, the param doesn\'t matter.
                           if you need it, it\'s in the subroutine 'do_backup'.
                           you\'ll have to move it from there, back to the main_param array,
                           @mysqldump_main_params_array

                         - added var to control count checks and use of
                           extended insert or not, via var:
                           $compare_table_file_count    = 'no';
                           (setting it to 'no' speeds up restores)

                         - added ability (at least under Linux) to use ONE database name
                           on the command line, which will backup one database in a custom
                           subdirectory of the current directory.

                         - NOTE:
                           I have not tested the Web or Windows versions for quite a number of versions,
                           but the Linux / Shell version has been tested a lot.

                           (Thus, I cannot currently confirm the viability of the Web or Windows versions.)

v.3.5 - February 18, 2014
                         - moved some commonly changed vars to the top of the file, for convenience
                           for those folks who have many servers, and thus many copies of the script

                         - added ionice to the commands (ONLY TESTED ON LINUX)
                         - added vars for the nice and ionice command params, which get appended to the commands
                         - now use both nice and ionice at the same time

                         - added nice and ionice before the mysqldump command

                         - you may wish to use nice and ionice before the script command in your crontab, e.g.
                           /bin/nice -n19 /usr/bin/ionice -c2 -n7 /path_to_script/mysql_backup.3.5.cgi

                         - added code to skip the databases 'information_schema' and 'performance_schema'
                           because they interfere with the error checks below

                         - added variable for $mysqldump_success_string in set up area
                         - added variable for $compare_table_file_count ('yes' / 'no' ) in setup area
                         - added :!:processing_time:!: to $subject line of email
                         - added code for the utilities 'tail' and 'grep'

                         - added a var in setup ($mysqldump_add_events_param)
                           to decide whether or not to add the --events param,
                           which does not work until MySQL 5.1.8

                         - in the subroutine "do_backup", added the following:
                           .......................................................................

                         - changed mysqldump system params to predefined arrays

                         - added "--skip-extended-insert" param to create one row per insert statement
                                 to avoid long lines in output file,
                                 and to allow for the record match count of "INSERT INTO "

                         - added innodb routines to "no cnf" mysqldump method
                         - added check for dbs and tables with spaces in names; email alert, but backup anyway
                         - added quotes around table names and files to account for spaces in names

                         - check $mysqldump_success_string for backup success
                         - added routine to email admin on backup failure, based on above (with mysqldump files only)

                           Note that with this failure, the script keeps going with other tables,
                           and simply sends an email with the warning message, so that at least the other tables
                           get backed up. (Instead of aborting the whole backup.)

                         - added routine to do count(*) of records in each table, and compare against
                           counts of 'INSERT INTO ' phrase in the backup file
                                 (if $compare_table_file_count equals 'yes')
                         - note that the email on count discrepancy does not abort the backup, but simply
                                 sends a warning email, since rows could have been deleted or added during the backup.
                         - also note that this is dependent upon the correct setting in the mysqldump params

v.3.4 - June 30, 2010    - Modified code check for InnoDB tables (only with cnf usage, so far)

v.3.3 - July 24, 2008    - Added code to make sure remote directory to delete ftp files
                           matches setup variable for remote directory when using "pwd".

                           If it does not match, the 'ls' command returns zero files,
                           so the remote list of files never gets deleted.
                           One does not want a remote server to fill up!

                           Ftp 'ls' requires the beginning slash to read the file list.
                           If it does not have the beginning slash, it would assume the
                           directory is a subdirectory of the current directory.

                           'pwd' produces a trailing slash, so both slashes are required in
                           the setup ftp directory variable.

                         - Added code to remove '.' and '..' from remote ftp list of files.

v.3.2 - May 15, 2006     - Added code to not break if the remote ftp dir
                           did not have any files in it. Thanks to a number of
                           users for pointing this out.

                         - Added code to delete remote ftp files, based on
                           the variable $number_of_files_to_save (see comments
                           under variable, in set up section)

v.3.1 - Nov. 21, 2003    - Added code to check if file has already been
                           uploaded to the ftp site -- it yes, aborts.

                           Note that if your filename has seconds
                           in the datetime string, you should not run into
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
                           NOTE!! some earlier versions of mysqldump do not
                           have the --result-file flag -- if your version
                           does not, you may have to
                           a) upgrade mysql or
                           b) use the outfile or normal_select method
                           I tested it on:
                           - Linux with MySQL v3.23.54 - worked fine
                           - Win98 with MySQL v3.23.33 - no result-file flag
                           I searched and SEARCHED :-) through the History
                           notes at mysql.com to find out when they introduced
                           the result-file flag, but I have not found it yet.
                           If someone finds it, let me know.

                           I use the --result-file=$file and system call method
                           with mysqldump because I had problems with the
                           backtick and > redirection symbol on Win98, running
                           from the script. I am still trying to figure out why.
                           Also note that the system method with a list
                           does not invoke the shell, so that we do not run into
                           the 127 character command limit on Win98.

                         - I now longer parse the cnf file manually.
                           (I actually did not use the parsed data
                           in 2.7, but I had not deleted the code.)
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
                           so that errors do not cause the
                           script to die, but still provide output

                         - added variable for the command 'ls'

                         - removed the need for the utility commands
                           find, rm, xargs, wc
                           by recoding two subroutines in Perl.
                           (delete_text_files and clean_old_files)
                           (There is always more than one way to do it. :-)
                           This was stimulated by the problems with
                           backticks and pipes on Win98.
                           I now use File::Path to remove directories
                           and simple directory arrays to remove files,
                           since the directories are not nested.

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
                           so that if it is not set to 'yes', the messages
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
                           it is chmoded to 755 (from 777 - see above)

                         - added error routines to check for the creation
                           of tar_dir, the existence of mysql_backup_dir,
                           the creation of the backup files, and the
                           deletion of the files to be deleted.

                         - added a number of variables and code bits
                           that allow one to run the script from the
                           web, with a password protected login,
                           for users that do not have shell access.

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
                           If you are experiencing this:
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
                           to setup (I did not set it up :-).

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
                           particular coding style. So, most patches will not
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
                           if the libraries are not installed, since the
                           'use' lines do get parsed.

v2.6 - June 10, 2002     - added the ftp_option
                           The initial ftp code was contributed by
                           Gil Hildebrand, Jr. (root@moflava.net)
                           with additional code by myself.
                           (added error checking, extra params, etc.)

                         - added code to skip loading
                           Net::FTP and MIME::Lite if
                           $ftp_backup and $email_backup are set to 'no'
                           If you do not want to install them,
                           you no longer have to comment out code sections.
                           (see v2.7 above for bug fix)
                           (the main code does not have to be commented out,
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
                           (Thus, it is highly advisable to use a .cnf file!)

                         - added $show_file_list_in_email var, to trim large emails.
                           The file list will not be included in the email unless
                           the var is set to 'yes'.

                         - Added functionality to backup LARGE systems, i.e:
                         - changed the tar method to tar a subdirectory with all
                           the files, so tar does not choke if there are too many
                           files. The subdir is removed once the tar file is made,
                           if $delete_text_files is set to yes. If not, the files
                           in old tar_dirs are cleaned out later by clean_old_files.

                         - modified 'ls -la' to use xargs so that large directories
                           do not choke.

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
                           to use absolute paths instead of the ~/. The ~/ did not
                           work, and is a fine example of the need for testing :-)
                           I thought I was being clever and convenient, but I
                           actually did not use it on my system (I used the absolute
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
                                           would not die before emailing the error.
                           . made all vars in &do_backup 'my' to avoid conflicts

v2.0 - February 15, 2001 - completely rewritten as a Perl script
                           . added all core options

v1.0 - January 2, 2000   - written as a simple shell script

=cut

###################################################################################################
# we place a 1; on the last line, because this file can now be 'required' in
# so that the script can be run from the web.

1;
