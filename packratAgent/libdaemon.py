import os
import sys
import logging
import signal
from logging.handlers import SysLogHandler, WatchedFileHandler

#NOTE: this is not compatible with python < 2.6

class Daemon( object ):
  def __init__( self, proc_name, pidfile, interactive=False, error_log=None ):
    super( Daemon, self ).__init__()
    self.proc_name = proc_name
    self.interactive = interactive
    self.error_log = error_log
    self.pidfile = pidfile
    self.need_restart = False
    signal.signal( signal.SIGINT, self._sigHandler )
    signal.signal( signal.SIGQUIT, self._sigHandler )
    signal.signal( signal.SIGTERM, self._sigHandler )
    signal.signal( signal.SIGHUP, self._sigHandler )
    signal.signal( signal.SIGSYS, self._sigHandler )
    signal.signal( signal.SIGUSR1, self._sigHandler )
    signal.signal( signal.SIGUSR2, self._sigHandler )

  ## implemet these in subclass, return True if all is good, other wise return False, except for do_stop
  def main( self ):
    return True

  def do_stop( self ):
    pass

  def do_loadconfig( self ):
    return True

  def do_extra_1( self ):
    return True

  def do_extra_2( self ):
    return True
  ## end

  def _initLogging( self ):
    logging.basicConfig()
    logger = logging.getLogger()

    if self.interactive:
      logger.setLevel( logging.DEBUG )
    else:
      logger.removeHandler( logger.handlers[0] ) # get rid of the default one
      if self.error_log:
        handler = WatchedFileHandler( filename=self.error_log )  # something that can handle logrotate
        handler.setFormatter( logging.Formatter( fmt='\n\n%(asctime)s   pid:%(process)d   thread:   %(thread)d\n%(module)s - %(lineno)d\n%(message)s' ) )
        handler.setLevel( logging.ERROR )
        logger.addHandler( handler )
      handler = SysLogHandler( address='/dev/log', facility=SysLogHandler.LOG_DAEMON )
      handler.setFormatter( logging.Formatter( fmt=self.proc_name + '[%(process)d]: %(message)s' ) )
      logger.addHandler( handler )
      logger.setLevel( logging.INFO )

  def _stopLogging( self ):
    logging.shutdown()

  def _daemonize( self ):
    logging.debug( 'libdaemon: Damonizing...' )
    #http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    logging.debug( 'libdaemon: First Fork...' )
    try:
      pid = os.fork()
      if pid > 0:
        sys.exit( 0 ) # another parent dies for the sake of the child
    except OSError as e:
      logging.exception( 'libdaemon: Exception on first fork, errno: %s' % e.errno )
      raise e

    logging.debug( 'libdaemon: Unataching process...' )
    os.chdir( '/' )
    os.setsid()
    os.umask( 0 )

    logging.debug( 'libdaemon: Second Fork...' )
    try:
      pid = os.fork()
      if pid > 0:
        sys.exit( 0 ) # yet another parent dies for the sake of the child
    except OSError as e:
      logging.exception( 'libdaemon: Exception on second fork, errno: %s' % e.errno )
      raise e

    logging.debug( 'libdaemon: Detaching stdout/err/in...' )
    # we are the child now, go go go
    sys.stdout.flush()
    sys.stderr.flush()
    tmp = file( '/dev/null', 'r' )
    os.dup2( tmp.fileno(), sys.stdin.fileno() )
    tmp = file( '/dev/null', 'a+' )
    os.dup2( tmp.fileno(), sys.stdout.fileno() )
    tmp = file( '/dev/null', 'a+', 0 )
    os.dup2( tmp.fileno(), sys.stderr.fileno() )

  def _writepid( self ):
    logging.debug( 'libdaemon: Writing PID to "%s"...', self.pidfile )
    tmp = file( self.pidfile, 'w' )
    tmp.write( '%s\n' % os.getpid() )
    tmp.close()

  def _readpid( self ): # can't log in _readpid, called from non-logging inited state
    if not os.path.exists( self.pidfile ):
      return None

    tmp = file( self.pidfile, 'r' )
    pid = int( tmp.read().strip() )
    tmp.close()

    return pid

  def _delpid( self ):
    logging.debug( 'libdaemon: Deleting "%s"...', self.pidfile )
    try:
      os.unlink( self.pidfile )
    except:
      pass

  def _sigHandler( self, sig, frame ):
    logging.debug( 'libdaemon: Got Signal %d' % sig )
    if sig in ( signal.SIGINT, signal.SIGQUIT, signal.SIGTERM ):
      logging.info( 'libdaemon: Got Stop Signal' )
      self.need_restart = False
      self.do_stop()

    elif sig == signal.SIGHUP:
      logging.info( 'libdaemon: Got Restart Signal' )
      self.need_restart = True
      self.do_stop()

    elif sig == signal.SIGSYS:
      logging.info( 'libdaemon: Got Reload Config Signal' )
      if not self.do_loadconfig():
        self.need_restart = False
        self.do_stop()

    elif sig == signal.SIGUSR1:
      logging.info( 'libdaemon: Got Extra Signal 1' )
      if not self.do_extra_1():
        self.need_restart = False
        self.do_stop()

    elif sig == signal.SIGUSR2:
      logging.info( 'libdaemon: Got Extra Signal 2' )
      if not self.do_extra_2():
        self.need_restart = False
        self.do_stop()

    else:
      logging.debug( 'libdaemon: Unknown Signal' )

    logging.debug( 'libdaemon: Done with Signal %d' % sig )

  def start( self ):
    logging.debug( 'libdaemon: Starting...' )
    self._initLogging()

    pid = self._readpid()
    if pid:
      logging.error( 'libdaemon: pidfile %s found, allready running?' % self.pidfile )
      return False

    if not self.do_loadconfig():
      return False

    if not self.interactive:
      self._daemonize()

    self._writepid()

    while True:
      self.need_restart = False
      logging.debug( 'libdaemon: Calling main...' )
      try:
        self.main()
        rc = True
      except:
        logging.exception( 'libdaemon: Exception in main' )
        rc = False
        break

      if not self.need_restart:
        break

      if not self.do_loadconfig():
        rc = False
        break

    logging.debug( 'libdaemon: Cleanning up...' )
    self._stopLogging()
    self._delpid()

    logging.debug( 'libdaemon: All Done.' )
    return rc

  #NOTE: these don't get called inside the running Process, they are signialling to the Process, only the signal goes through to _sigHandler
  def stop( self ):
    pid = self._readpid()
    if not pid:
      print 'pidfile not %s found.' % self.pidfile
      return False

    try:
      os.kill( pid, signal.SIGTERM )
    except OSError as e:
      if str( e ).find( 'No such process' ) > 0:
        print 'Process from pid file is dead, cleanning up pid file.'
        self._delpid()
      else:
        raise e

    return True

  def kill( self ):
    pid = self._readpid()
    if not pid:
      print 'pidfile not %s found.' % self.pidfile
      return False

    try:
      os.kill( pid, signal.SIGKILL )
    except OSError as e:
      if str( e ).find( 'No such process' ) > 0:
        print 'Process from pid file is dead, cleanning up pid file.'
        self._delpid()
      else:
        raise e

    return True

  def restart( self ):
    pid = self._readpid()
    if not pid:
      print 'pidfile not %s found.' % self.pidfile
      return False

    try:
      os.kill( pid, signal.SIGHUP )
    except OSError as e:
      if str( e ).find( 'No such process' ) > 0:
        print 'Process %s is not running' % pid
        return False
      else:
        raise e

    return True

  def reload_config( self ):
    pid = self._readpid()
    if not pid:
      print 'pidfile not %s found.' % self.pidfile
      return False

    try:
      os.kill( pid, signal.SIGSYS )
    except OSError as e:
      if str( e ).find( 'No such process' ) > 0:
        print 'Process %s is not running' % pid
        return False
      else:
        raise e

    return True

  def extra_1( self ):
    pid = self._readpid()
    if not pid:
      print 'pidfile not %s found.' % self.pidfile
      return False

    try:
      os.kill( pid, signal.SIGUSR1 )
    except OSError as e:
      if str( e ).find( 'No such process' ) > 0:
        print 'Process %s is not running' % pid
        return False
      else:
        raise e

    return True

  def extra_2( self ):
    pid = self._readpid()
    if not pid:
      print 'pidfile not %s found.' % self.pidfile
      return False

    try:
      os.kill( pid, signal.SIGUSR2 )
    except OSError as e:
      if str( e ).find( 'No such process' ) > 0:
        print 'Process %s is not running' % pid
        return False
      else:
        raise e

    return True

  def status( self ):
    pid = self._readpid()
    if not pid:
      return 'Stopped'

    else:
      try:
        os.kill( pid, 0 )
      except OSError as e:
        if str( e ).find( 'No such process' ) > 0:
          return 'Process Missing PID:%s' % pid
        else:
          raise e

      return 'Running PID:%s' % pid
