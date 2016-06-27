#!/bin/sh
### BEGIN INIT INFO
# Provides:          repoSync
# Required-Start:    $network $named $time $local_fs $syslog
# Required-Stop:
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Packrat repoSync
# Description:       Packrat repoSync
### END INIT INFO

# Author: Peter Howe

PATH=/sbin:/usr/sbin:/bin:/usr/bin
DESC="Packrat Repo Sync"             # Introduce a short description here
NAME=repoSync             # Introduce the short server's name here
DAEMON=/usr/sbin/repoSync      # Introduce the server's location here
DAEMON_ARGS= # Arguments to run the daemon with
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME

# Exit if the package is not installed
[ -x $DAEMON ] || exit 0

# Read configuration variable file if it is present
[ -r /etc/default/$NAME ] && . /etc/default/$NAME

# Load the VERBOSE setting and other rcS variables
. /lib/init/vars.sh

# Define LSB log_* functions.
# Depend on lsb-base (>= 3.0-6) to ensure that this file is present.
. /lib/lsb/init-functions

check_status()
{
	STATUS="$($DAEMON $DAEMON_ARGS status)"
	STATUS="${STATUS#Status: }"  # strip "Status: "
	STATUS="${STATUS%%:*}"       # strip :<PID>
	# could be "Stopped", "Running PID", or "Process Missing PID"

	[ "$STATUS" = "Running PID" ] && return 0
	[ "$STATUS" = "Stopped" ] && return 1
	[ "$STATUS" = "Process Missing PID" ] && return 1

	return 2
}

#
# Function that starts the daemon/service
#
do_start()
{
	# Return
	#   0 if daemon has been started
	#   1 if daemon was already running
	#   2 if daemon could not be started

	check_status
	case "$?" in
		0) return 1 ;;
		2) return 2 ;;
	esac

	$DAEMON $DAEMON_ARGS start || return 2

	return 0
}

#
# Function that stops the daemon/service
#
do_stop()
{
	# Return
	#   0 if daemon has been stopped
	#   1 if daemon was already stopped
	#   2 if daemon could not be stopped
	#   other if a failure occurred

	check_status
	case "$?" in
		1) return 1 ;;
		2) return 3 ;;
	esac

	$DAEMON $DAEMON_ARGS stop || return 2

  COUNTER=0
  while [ "$COUNTER" -lt 100 ];
  do
    sleep 2
    check_status
    case "$?" in
      1) return 1 ;;
      2) return 3 ;;
    esac
    COUNTER=$(( $COUNTER + 1 ))
  done

  $DAEMON $DAEMON_ARGS kill || return 2

  COUNTER=0
  while [ "$COUNTER" -lt 40 ];
  do
    sleep 1
    check_status
    case "$?" in
      1) return 1 ;;
      2) return 3 ;;
    esac
    COUNTER=$(( $COUNTER + 1 ))
  done

  return 2
}

case "$1" in
  start)
    [ "$VERBOSE" != no ] && log_daemon_msg "Starting $DESC " "$NAME"
    do_start
    case "$?" in
		0|1) [ "$VERBOSE" != no ] && log_end_msg 0 ;;
		2) [ "$VERBOSE" != no ] && log_end_msg 1 ;;
	esac
  ;;
  stop)
	[ "$VERBOSE" != no ] && log_daemon_msg "Stopping $DESC" "$NAME"
	do_stop
	case "$?" in
		0|1) [ "$VERBOSE" != no ] && log_end_msg 0 ;;
		2) [ "$VERBOSE" != no ] && log_end_msg 1 ;;
	esac
	;;
  status)
  status_of_proc "$DAEMON" "$NAME" && exit 0 || exit $?
  ;;
  reload|force-reload)
	log_daemon_msg "Reloading $DESC" "$NAME"
	$DAEMON $DAEMON_ARGS reload_config
	log_end_msg $?
	;;
  restart)
	log_daemon_msg "Restarting $DESC" "$NAME"
	do_stop
	case "$?" in
	  0|1)
		do_start
		case "$?" in
			0) log_end_msg 0 ;;
			1) log_end_msg 1 ;; # Old process is still running
			*) log_end_msg 1 ;; # Failed to start
		esac
		;;
	  *)
	  	# Failed to stop
		log_end_msg 1
		;;
	esac
	;;
  *)
	echo "Usage: $SCRIPTNAME {start|stop|status|restart|reload|force-reload}" >&2
	exit 3
	;;
esac

:
