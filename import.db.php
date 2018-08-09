#!/usr/bin/php -Cq
<?php
###################################################################################################
# import.db.php
# by Peter Falkenberg Brown, peterbrown@worldcommunity.com
# This file's build date: October 6, 2014

# THIS SCRIPT IS USED TO IMPORT (RESTORE) MYSQL FILES THAT
# HAVE BEEN BACKED UP WITH MY "mysql.backup.cgi" SCRIPT.
# IT'S ADVANTAGE IS THAT IT HAS A USER PROMPT BEFORE ITS ACTION,
# AS WELL AS SOME USEFUL PARAMETERS.

# Copyright 2014 Peter Falkenberg Brown
# The World Community Press
# This program complies with the GNU GENERAL PUBLIC LICENSE
# and is released as "Open Source Software".
# NO WARRANTY IS OFFERED FOR THE USE OF THIS SOFTWARE

###################################################################################################
###NOTE:
      /*
      From comment at: http://php.net/manual/en/function.getcwd.php:

      If your PHP cli binary is built as a cgi binary (check with php_sapi_name),
      the cwd functions differently than you might expect.

      say you have a script /usr/local/bin/purge
      you are in /home/username

      php CLI: getcwd() gives you /home/username
      php CGI: getcwd() gives you /usr/local/bin

      This can trip you up if you\'re writing command line scripts with php.
      You can override the CGI behavior by adding -C to the php call:

      #!/usr/local/bin/php -Cq

      and then getcwd() behaves as it does in the CLI-compiled version.
      */

###################################################################################################
### SET UP VARS

passthru("clear");

$curdir  = getcwd();

$header_msg = <<<EOD

import.db.php: A script to import SQL files into MySQL databases.
=======================================================================================================================
Current Directory: $curdir

This script only works with files created by the mysql_backup.cgi script.
The current directory must ONLY contain SQL files with this filename format:
bak.mysql.YYYY-MM-DD_HH.MM.SS_database.table.txt --- Only files for **ONE** database can be processed.
=======================================================================================================================

EOD;

$database_param_msg = <<<EOD

ERROR:

You must pass ONE database name as an input argument.
This database name is the name of the database to IMPORT **INTO**.
Unless you want to APPEND data, you must import into an EMPTY database.

EOD;

$second_param_msg = <<<EOD

If you pass an OPTIONAL SECOND paramater, it can only be the string: 'notempty'.
Using this parameter will APPEND data to any existing data tables of the same name.
BE VERY CAREFUL WITH THIS OPTION.


EOD;

$db_max_length_msg    = "\nDatabase Names cannot be longer than 64 chars.\n\n";
$db_illegal_chars_msg = "\nIllegal character(s) in database name. Please try again.\n\n";

$db_name         = '';
$not_empty_param = '';
$drop_table      = '';
$database_status = 'EMPTY';
$table_msg       = '';

echo $header_msg;

###################################################################################################
### CHECK INPUT PARAMS

if ( $_SERVER["argc"] == 2 )
      {
      $db_name = $argv[1];
      }
elseif ( $_SERVER["argc"] == 3 )
      {
      $db_name         = $argv[1];
      $not_empty_param = $argv[2];

      if ( $not_empty_param != 'notempty' )
            {
            echo $database_param_msg;
            echo $second_param_msg;
            echo "Incorrect SECOND PARAMETER:\n";
            echo "You passed the params: [$db_name] [$not_empty_param]\n\n";
            exit;
            }
      }
else
      {
      echo $database_param_msg;
      echo $second_param_msg;
      exit;
      }

if ( strlen($db_name) > 64 )
      {
      echo $db_max_length_msg;
      exit;
      }

if ( preg_match('/[^A-Za-z0-9_]+/', $db_name ) )
      {
      echo $db_illegal_chars_msg;
      exit;
      }

$dbnames_array = array();

###################################################################################################
### CHECK FILES IN CURRENT DIR; MUST MATCH BACKUP FILE SYNTAX

$files = scandir('.');

foreach( $files as $file )
      {
      if ( $file === '.' || $file === '..')     {continue;}
      if ( is_dir($file) )                      {continue;}

      $filename_len = strlen($file);
      if ( $filename_len < 37 )
            {
            echo "\nERROR:\n\n";
            echo "File exists that is less than 37 characters long. Aborting.\n\n";
            echo "Incorrect file: $file\n\n";

            echo "A valid import file will have this format:\n";
            echo "bak.mysql.YYYY-MM-DD_HH.MM.SS_DB_NAME.TABLE_NAME.txt\n\n";
            echo "ARE YOU IN THE BACKUP DIRECTORY?\n\n\n";
            exit;
            }

      $parse_string = substr($file, 30);
      list($db_string, $table_name, $file_ext) = explode(".", $parse_string);

      if ( empty($db_string) || empty($table_name) || $file_ext != 'txt' )
            {
            echo "\nERROR:\n\n";
            echo "Invalid filename for SQL import.\n";
            echo "Filename: $file\n";
            echo "Parsed segment: $parse_string\n";
            echo "db, table, ext: [$db_string / $table_name / $file_ext]\n\n\n";
            exit;
            }

      if ( ! in_array($db_string, $dbnames_array) )
            {
            $dbnames_array[] = $db_string;
            }
      }

if ( ! $dbnames_array )
      {
      echo "\nERROR:\n\n";
      echo "There are no database names listed.\n\n";
      exit;
      }

if ( count($dbnames_array) > 1 )
      {
      echo "\nERROR:\n\n";
      echo "The SQL files in this directory reference more than one database. They are:\n\n";

      foreach ( $dbnames_array as $db_item )
            {
            echo "     -- $db_item\n";
            }

      echo "\nThus, we abort, because you do not want to import two databases into one.\n\n\n";
      exit;
      }

###################################################################################################
### CHECK FILES FOR DROP TABLE PATTERN AND GET FILE COUNTS

echo "... Checking for Drop Table Directives...\n";

$drop_table_list    = rtrim(shell_exec("grep -lir 'DROP TABLE IF EXISTS' *.txt"));
$drop_file_count    = rtrim(shell_exec("grep -lir 'DROP TABLE IF EXISTS' *.txt | wc -l"));
$no_drop_file_count = rtrim(shell_exec("grep -Lir 'DROP TABLE IF EXISTS' *.txt | wc -l"));
$import_file_count  = rtrim(shell_exec("find . -maxdepth 1 -name '*.txt' | wc -l"));

$drop_table_list_array  = explode("\n", $drop_table_list);
$drop_table_concat_list = '';

foreach( $drop_table_list_array as $drop_table_long_string )
      {
      $drop_table_parse_string = substr($drop_table_long_string, 30);

      list($db_string2, $drop_table_name, $file_ext2) = explode(".", $drop_table_parse_string);

      $drop_table_concat_list .= "| $drop_table_name ";
      }

$drop_table_msg = "
Drop File Count: $drop_file_count | No_Drop File Count: $no_drop_file_count | Import File Count: $import_file_count
";

$drop_table_list_msg = "\nThe table(s) with the DROP TABLE COMMAND are:\n$drop_table_concat_list\n";

if ( $not_empty_param == 'notempty' )
      {
      if ( ($drop_file_count > 0) && ($drop_file_count == $import_file_count) )
            {
            echo "\nERROR! You passed the 'notempty' parameter, which will APPEND data\n";
            echo "but all of the import files have a DROP TABLE directive.\n\n";
            echo "... thus, aborting.\n";
            echo "$drop_table_msg\n";
            exit;
            }
      }
else
      {
      if ( $drop_file_count < $import_file_count )
            {
            echo "\nERROR! You did NOT pass the 'notempty' parameter;\n";
            echo "thus we assume you want to CREATE ALL tables,\n";
            echo "but some of the import files are missing DROP TABLE / CREATE TABLE directives.\n\n";
            echo "... thus, aborting.\n";
            echo "$drop_table_msg\n";
            exit;
            }
      }

###################################################################################################
### CHECK DATABASE STATUS

$db_name_esc       = escapeshellarg($db_name);

$mysqlshow_db_text = shell_exec("mysqlshow --count $db_name_esc");

if ( strpos($mysqlshow_db_text, "Database: $db_name") === false )
      {
      ###########################################
      ### DATABASE DOES NOT EXIST

      echo "\nERROR:\n\n";
      echo "The database [$db_name] that you want to IMPORT INTO does not exist.\n\n\n";
      exit;
      }

if ( strpos($mysqlshow_db_text, "rows in set") !== false )
      {
      ###########################################
      ### DATABASE EXISTS AND HAS TABLES

      $mysqlshow_db_row_count = shell_exec("mysql -e 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \"$db_name_esc\";'");

      $mysqlshow_db_row_count = str_replace("COUNT(*)", "COUNT: ", $mysqlshow_db_row_count);
      $mysqlshow_db_row_count = str_replace("\n", "", $mysqlshow_db_row_count);

      if ( $not_empty_param == 'notempty' )
            {
            # we import even though it's not empty, appending data.

            $database_status = 'NOT EMPTY';

            $table_msg .= "
            The database [$db_name] that you want to IMPORT INTO exists, but it also has TABLES.
            Some or all of the import data will be APPENDED ONTO EXISTING TABLES.
            Are you sure that you want to do that? TABLE $mysqlshow_db_row_count\n";
            }
      else
            {
            echo "\nERROR:\n\n";
            echo "The database [$db_name] that you want to IMPORT INTO exists,\n";
            echo "but it also has TABLES. To import, the database must be empty.\n\n";
            echo "TABLE $mysqlshow_db_row_count\n\n";
            echo "If you wish to APPEND data, you must use the second param: 'notempty'\n";
            echo "and make sure that the APPEND tables do NOT have the DROP TABLE / CREATE TABLE directives.\n";
            echo "$drop_table_msg\n";
            exit;
            }
      }
else
      {
      ###############################################
      ### DATABASE EXISTS BUT DOES NOT HAVE TABLES

      if ( $not_empty_param == 'notempty' )
            {
            echo "\nERROR:\n\n";
            echo "The database [$db_name] that you want to IMPORT INTO exists, but it does NOT have TABLES.\n";
            echo "To import, you will need the DROP/CREATE statements for ALL tables,\n";
            echo "and you CANNOT use the 'notempty' parameter.\n";
            echo "$drop_table_msg\n";
            exit;
            }
      }

#..........................................................
# finish setting up $table_msg, with indents

$table_msg .= $drop_table_msg;

if ( ($drop_file_count > 0 ) && ($drop_file_count < $import_file_count) )
      {
      $table_msg .= $drop_table_list_msg;
      }

###################################################################################################
### GET DATABASE CHARSET AND COLLATION AND SET UP FIND COMMAND

$mysqlshow_db_charset = shell_exec("mysql -e 'SELECT schema_name, default_character_set_name,default_collation_name FROM information_schema.schemata WHERE schema_name = \"$db_name_esc\";'");

$charset_array = preg_split("/\s+/", $mysqlshow_db_charset);
$charset       = $charset_array[4];
$collation     = $charset_array[5];

#..................................................................................................
# original command:
# find . -name "*.txt" -print | sort | xargs -t --replace cat {} | mysql DBNAME

# echo passthru("find . -name '$db_search_string' -print | sort | xargs --verbose -I {} ls -1 {}");
# echo passthru("find . -name '$db_search_string' -print | sort | xargs --verbose -I {} cat {} | mysql $db_name_esc");

$import_database  = $dbnames_array[0];
$db_search_string = '*_' . $import_database . '.*.txt';

$cmd = "find . -name '$db_search_string' -print | sort | xargs --verbose -I {} cat {} | mysql $db_name_esc";

###################################################################################################
### PROMPT USER

# The import command to be run: $cmd

echo <<<EOD

STOP!! Please check the details below.

     Importing FROM: [$import_database]
    TARGET Database: [$db_name]
             Status: [$database_status]
Char Set, Collation: [$charset - $collation]
$table_msg
=======================================================================================================================
EOD;

echo "\nIf this is ALL correct, type 'y' to proceed, or any other character to quit: ";

$stdin = fopen('php://stdin', 'r');
$input = fgets($stdin);
fclose($stdin);

if ( trim($input) != 'y' )
      {
      echo "\nABORTING!\n\n";
      exit;
      }

###################################################################################################
### RUN IMPORT COMMAND

echo "\n\nProcessing...\n\n";

echo passthru($cmd);

echo "\n\nDone!\n\n";

exit;

###################################################################################################
