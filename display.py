import curses, time, traceback, sys
import curses.wrapper
from twisted.python import log
from twisted.internet import reactor


class CursesStdIO:
    """fake fd to be registered as a reader with the twisted reactor.
       Curses classes needing input should extend this"""

    def fileno(self):
        """ We want to select on FD 0 """
        return 0

    def doRead(self):
        """called when input is ready"""

    def logPrefix(self): return 'CursesClient'

class Screen(CursesStdIO):
    def __init__(self, stdscr, recorder):
        self.timer = 0
        self.statusText = "Press space to record message."
        self.searchText = ''
        self.stdscr = stdscr

        self.recorder = recorder

        # set screen attributes
        self.stdscr.nodelay(1) # this is used to make input calls non-blocking
        curses.cbreak()
        self.stdscr.keypad(1)
        curses.curs_set(0)     # no annoying mouse cursor

        self.rows, self.cols = self.stdscr.getmaxyx()
        self.lines = []

        curses.start_color()

        # create color pair's 1 and 2
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

        self.paintStatus(self.statusText)

    def connectionLost(self, reason):
        log.err("connection lost")
        pass
        # self.close()

    def addLine(self, text):
        """ add a line to the internal list of lines"""

        self.lines.append(text)
        self.redisplayLines()

    def redisplayLines(self):
        """ method for redisplaying lines
            based on internal list of lines """

        self.stdscr.clear()
        self.paintStatus(self.statusText)
        i = 0
        index = len(self.lines) - 1
        while i < (self.rows - 3) and index >= 0:
            self.stdscr.addstr(self.rows - 3 - i, 0, self.lines[index],
                               curses.color_pair(2))
            i = i + 1
            index = index - 1
        self.stdscr.refresh()

    def paintStatus(self, text):
        if len(text) > self.cols: raise TextTooLongError
        self.stdscr.addstr(self.rows-2,0,text + ' ' * (self.cols-len(text)),
                           curses.color_pair(1))
        # move cursor to input line
        self.stdscr.move(self.rows-1, self.cols-1)

    def doRead(self):
        """ Input is ready! """
        log.err("!!READ READ READ!!")

        curses.noecho()
        c = self.stdscr.getch() # read a character

        if c == ord(' '):
            log.err("TOGGLE!")
            self.recorder.toggle()
            if self.recorder.is_recording():
                self.paintStatus("Recording")
            else:
                self.paintStatus("Press space to record message.")

        elif c == ord('q'):
            self.close()
        
        self.stdscr.refresh()

    def close(self):
        """ clean up """
        log.err("CLOSE CLOSE CLOSE")
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

        reactor.stop()
