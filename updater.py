#!/usr/bin/env python

#  Copyright 2016 by Dai Trying
#
#  This file is part of apt-updater.
#
#     apt-updater is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     apt-updater is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with apt-updater. If not, see <http://www.gnu.org/licenses/>.

from PyQt4 import QtGui, QtCore
import os
import sys
import getopt
import subprocess
from datetime import datetime, timedelta
from time import sleep
from update_checker import do_check, do_quick_check
import getpass
import re
import updater_rc

VERSION = "0.0.1-22"
start = datetime.now()
last_run = start
delay = 0
interval = 0
delay_default = 120  # set default delay before checking for updates in seconds
interval_default = 3600  # set default interval between update checks in seconds
u_name = getpass.getuser()
has_run = False
busy = False
UU_status = False
UU_file = '/etc/apt/apt.conf.d/20auto-upgrades'


def get_ua_status(file_name):
    global UU_status
    result = False
    if not os.path.exists(file_name):
        # print('Unattended-Upgrade file not present')
        return
    search_phrase = 'APT::Periodic::Unattended-Upgrade'
    search_file = open(file_name, 'r')
    for line in search_file:
        if not line.startswith('#'):
            if search_phrase in line:
                result = line
    search_file.close()
    status = re.findall(r'"([^"]*)"', result)
    if status[0] == '0':
        UU_status = False
    else:
        UU_status = True

get_ua_status(UU_file)


def which(program):
    def is_exe(file_path):
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

    new_file_path, file_name = os.path.split(program)
    if new_file_path:
        if is_exe(program):
            return True
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return True

    return False


def apt_free():
    if which('/usr/bin/check-apt-busy'):
        try:
            result = subprocess.check_call('/usr/bin/check-apt-busy')
        except:
            result = 1
        if result == 0:
            return True
        else:
            return False
    else:
        try:
            subprocess.check_output('lsof -c apt -u ^' + u_name, shell=True)
        except subprocess.CalledProcessError:
            try:
                subprocess.check_output('lsof -c dpkg -u ^' + u_name, shell=True)
            except subprocess.CalledProcessError:
                return True
        return False


def pin_ok():
    result = subprocess.check_output('/usr/share/dai-apt-updater/pin_check.sh')
    if result.strip() == "True":
        return True
    else:
        return False


class CheckUpdatesThread(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)
        self.security = QtCore.SIGNAL('security')
        self.normal = QtCore.SIGNAL('normal')
        self.nothing = QtCore.SIGNAL('nothing')
        self.tooltip = QtCore.SIGNAL('tooltip')
        self.lock_error = QtCore.SIGNAL('lock_error')
        self.enable_menu = QtCore.SIGNAL('set_enable')
        self.disable_menu = QtCore.SIGNAL('set_disable')

    def __del__(self):
        self.wait()

    def do_the_wait(self):
        global delay, interval, last_run, start, has_run
        now = datetime.now()
        if not has_run:
            diff = now - start
            if int(diff.total_seconds()) > int(delay):
                has_run = True
                self.emit(self.enable_menu)
                return True
        else:
            new_diff = now - last_run
            if int(new_diff.total_seconds()) > int(interval):
                return True
        return False

    def do_the_check(self):
        print("Checking...")
        global last_run, has_run
        while not apt_free():
            self.emit(self.lock_error)
            self.emit(self.tooltip, "Apt is currently busy\nWaiting for it to become free")
            self.emit(self.disable_menu)
            print("...Failed to Check...")
            sleep(10)

        last_run = datetime.now()
        upd, s_upd = do_check()
        if upd > 0:
            if s_upd > 0:
                has_run = True
                self.emit(self.enable_menu)
                self.emit(self.security)
                self.emit(self.tooltip, "We have " + str(upd) + " update(s) available\nOf which " +
                          str(s_upd) + " are security updates!\nChecked : " + last_run.strftime("%H:%M:%S"))
            else:
                has_run = True
                self.emit(self.enable_menu)
                self.emit(self.normal)
                self.emit(self.tooltip, "We have " + str(upd) + " update(s) available\nOf which " +
                          str(s_upd) + " are security updates!\nChecked : " + last_run.strftime("%H:%M:%S"))
        else:
            has_run = True
            self.emit(self.enable_menu)
            self.emit(self.nothing)
            self.emit(self.tooltip, "There are no updates available\nChecked : " + last_run.strftime("%H:%M:%S"))
        print("...checked.")

    def run(self):
        while True:
            if self.do_the_wait():
                self.do_the_check()
            sleep(1)


class SystemTrayIcon(QtGui.QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        QtGui.QSystemTrayIcon.__init__(self, icon, parent)
        self.setToolTip(
            "Waiting for Delay period\nScheduled for " + (start + timedelta(seconds=int(delay))).strftime("%H:%M:%S"))
        self.activated.connect(self.icon_activated)
        self.menu = QtGui.QMenu(parent)

        if UU_status:
            self.UU_disable = self.menu.addAction("Disable Unattended Upgrades")
        self.check_now = self.menu.addAction("Check updates Now")
        self.update_apt = self.menu.addAction("Refresh apt db Now")
        self.show_version = self.menu.addAction("Version")
        self.exit_action = self.menu.addAction("Exit")

        if UU_status:
            self.UU_disable.triggered.connect(self.disable_uu)
        self.check_now.triggered.connect(check_updates_now)
        self.update_apt.triggered.connect(self.update_apt_now)
        self.show_version.triggered.connect(self.display_verion)
        self.exit_action.triggered.connect(get_out)

        self.setContextMenu(self.menu)

        self.get_thread = CheckUpdatesThread()
        self.connect(self.get_thread, self.get_thread.security, self.set_security)
        self.connect(self.get_thread, self.get_thread.normal, self.set_normal)
        self.connect(self.get_thread, self.get_thread.nothing, self.set_no_updates)
        self.connect(self.get_thread, self.get_thread.tooltip, self.set_tooltip)
        self.connect(self.get_thread, self.get_thread.lock_error, self.set_lock_error)
        self.connect(self.get_thread, self.get_thread.enable_menu, self.set_free)
        self.connect(self.get_thread, self.get_thread.disable_menu, self.set_busy)
        self.get_thread.start()
        self.set_busy()

    def display_verion(self):
        QtGui.QMessageBox.information(QtGui.QMessageBox(), 'Version', 'Dai\'s Apt Updater\n'+str(VERSION), QtGui.QMessageBox.Ok)

    def disable_uu(self):
        result = False
        if which('tdesu'):
            ua_off = subprocess.Popen(['tdesu', '/usr/share/dai-apt-updater/disable_uu.py'])
            ua_off.wait()
        elif which('gksudo'):
            ua_off = subprocess.Popen(['gksudo', '/usr/share/dai-apt-updater/disable_uu.py'])
            ua_off.wait()
        else:
            QtGui.QMessageBox.warning(QtGui.QMessageBox(), "Cannot disable Unattended Upgrades",
                                      "I cannot find the required packages  to make changes to the system\nPlease "
                                      "re-install or fix missing dependencies", QtGui.QMessageBox.Ok)

        if os.path.exists('/tmp/UU_error.log'):
            with open('/tmp/UU_error.log') as f:
                s = f.read()
                if "UU disabled" in s:
                    result = True
                elif "UU NOT disabled" in s:
                    result = False
                elif "File not present" in s:
                    result = False
                else:
                    result = False
            if which('tdesu'):
                subprocess.check_call(['tdesu', 'rm', '/tmp/UU_error.log'])
            elif which('gksudo'):
                subprocess.check_call(['gksudo', 'rm', '/tmp/UU_error.log'])
        if result:
            self.menu.removeAction(self.UU_disable)

    def update_apt_now(self):
        self.set_busy()
        if which('tdesu'):
            errors = 0
            try:
                proc = subprocess.Popen(['tdesu', 'apt-get -qq', 'update'], stdout=subprocess.PIPE)
                for line in proc.stdout:
                    errors += 1
            except subprocess.CalledProcessError as e:
                print(e)
            if errors > 0:
                QtGui.QMessageBox.warning(QtGui.QMessageBox(), 'apt-get Error',
                                          'apt-updater encountered errors while updating the database\nPlease check '
                                          'your internet connection\nAlternatively check apt installation',
                                          QtGui.QMessageBox.Ok)
                return
        elif which('gksudo'):
            errors = 0
            try:
                proc = subprocess.Popen(['gksudo', 'apt-get -q', 'update'], stdout=subprocess.PIPE)
                for line in proc.stdout:
                    if line.startswith('Err'):
                        errors += 1
            except subprocess.CalledProcessError as e:
                print(e)

            if errors > 0:
                QtGui.QMessageBox.warning(QtGui.QMessageBox(), 'apt-get Error',
                                          'apt-updater encountered errors while updating the database\nPlease check '
                                          'your internet connection\nAlternatively check apt installation',
                                          QtGui.QMessageBox.Ok)
                return
        else:
            QtGui.QMessageBox.warning(QtGui.QMessageBox(), 'Cannot update apt db',
                                      'I cannot find the required packages to update the system\nPlease re-install or '
                                      'fix missing dependencies', QtGui.QMessageBox.Ok)

        self.set_free()
        check_updates_now()
        return "done"

    def icon_activated(self, reason):
        if not has_run:
            return
        if busy:
            return
        if reason == 3:
            self.run_updates()

    def run_updates(self):
        self.set_busy()
        if not pin_ok():
            QtGui.QMessageBox.warning(QtGui.QMessageBox(), 'apt-pin Error',
                                      'apt-updater encountered errors while checking the database pin settings\nI will'
                                      ' now attempt to update the apt database', QtGui.QMessageBox.Ok)
            if self.update_apt_now() == "done":
                QtGui.QMessageBox.information(QtGui.QMessageBox(), 'Apt Updated', 'Update successful',
                                              QtGui.QMessageBox.Ok)
            else:
                QtGui.QMessageBox.warning(QtGui.QMessageBox(), 'Apt Update Failed',
                                          'For some reason I could not update the apt database\nPlease check your '
                                          'internet connection', QtGui.QMessageBox.Ok)
                return
        if which("tdesu"):
            subprocess.call(['tdesu', '-d', '--comment', 'Please enter your password to update the system',
                             '/usr/sbin/synaptic -t "UPDATE MANAGER MODE" --dist-upgrade-mode --hide-main-window'
                             ' --non-interactive'])
        elif which("gksudo"):
            subprocess.call(['gksudo', '-m "Please enter your password to update the system"',
                             '/usr/sbin/synaptic -t "UPDATE MANAGER MODE" --dist-upgrade-mode --hide-main-window '
                             '--non-interactive'])
        else:
            QtGui.QMessageBox.warning(QtGui.QMessageBox(), 'Cannot update the system',
                                      'I cannot find the required packages to update the system\nPlease re-install or '
                                      'fix missing dependencies', QtGui.QMessageBox.Ok)
        check_updates_now()
        if do_quick_check():
            self.set_no_updates()
            if reboot_required():
                result = QtGui.QMessageBox.warning(QtGui.QMessageBox(), "REBOOT REQUIRED",
                                                   "It has been detected that you must reboot\nShould I reboot"
                                                   " immediately?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                if result == QtGui.QMessageBox.Yes:
                    if which("dcop"):
                        subprocess.call(["dcop ksmserver ksmserver logout 0 1 3"], shell=True)
                    elif which("gksudo"):
                        subprocess.call(['gksudo', '-m', 'Please enter user password to reboot system', 'reboot'])
                    else:
                        QtGui.QMessageBox.critical(QtGui.QMessageBox(), 'Cannot update the system',
                                                   'I cannot find the required packages to update the system\nPlease '
                                                   're-install or fix missing dependencies', QtGui.QMessageBox.Ok)
                elif result == QtGui.QMessageBox.No:
                    QtGui.QMessageBox.warning(QtGui.QMessageBox(), "REBOOT REQUIRED", "Please reboot as soon as "
                                                                                      "possible!", QtGui.QMessageBox.Ok)
        else:
            if reboot_required():
                result = QtGui.QMessageBox.warning(QtGui.QMessageBox(), "REBOOT REQUIRED",
                                                   "It has been detected that you must reboot\nbut there are more "
                                                   "updates to install\nPlease install more updates after reboot!\n"
                                                   "Should I reboot immediately?",
                                                   QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                if result == QtGui.QMessageBox.Yes:
                    if which("dcop"):
                        subprocess.call(["dcop ksmserver ksmserver logout 0 1 3"], shell=True)
                    elif which("gksudo"):
                        subprocess.call(['gksudo', '-m', 'Please enter user password to reboot system', 'reboot'])
                    else:
                        QtGui.QMessageBox.critical(QtGui.QMessageBox(), 'Cannot update the system',
                                                   'I cannot find the required packages to update the system\n'
                                                   'Please re-install or fix missing dependencies',
                                                   QtGui.QMessageBox.Ok)
                elif result == QtGui.QMessageBox.No:
                    QtGui.QMessageBox.warning(QtGui.QMessageBox(), "REBOOT REQUIRED",
                                              "Please reboot as soon as possible to install more updates!",
                                              QtGui.QMessageBox.Ok)

    def set_normal(self):
        self.setIcon(QtGui.QIcon(":/update.png"))
        self.show()

    def set_security(self):
        self.setIcon(QtGui.QIcon(":/update-security.png"))
        self.show()

    def set_no_updates(self):
        self.setIcon(QtGui.QIcon(":/no-updates.png"))
        self.show()

    def set_lock_error(self):
        self.setIcon(QtGui.QIcon(":/error.png"))
        self.show()

    def set_busy(self):
        global busy
        self.check_now.setDisabled(True)
        self.update_apt.setDisabled(True)
        busy = True

    def set_free(self):
        global busy
        self.check_now.setDisabled(False)
        self.update_apt.setDisabled(False)
        busy = False

    def set_tooltip(self, var):
        self.setToolTip(var)


def reboot_required():
    if os.path.exists("/var/run/reboot-required"):
        return True
    else:
        return False


def get_out():
    sure = QtGui.QMessageBox.question(QtGui.QMessageBox(),
                                      "Are You Sure?", "This will prevent apt-updater from checking for available "
                                                       "updates.\nAre you sure you want to quit?",
                                      QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
    if sure == QtGui.QMessageBox.Yes:
        sys.exit(0)


def check_updates_now():
    global last_run
    last_run = datetime.now() - timedelta(seconds=int(interval))


def main(argv):
    global delay, interval, last_run, delay_default, interval_default
    try:
        opts, args = getopt.getopt(argv, "vhd:i:")
    except getopt.GetoptError:
        print 'Option Error\n  Please check your options before trying again.\n\n  Usage:\n' \
              '    apt-updater -i <interval> -d <delay> -h -v\n'
        sys.exit(9)
    for opt, arg in opts:
        if opt in ("-h", "-?", "--help"):
            print '\nUsage:\n    apt-updater -i <interval> -d <delay> -h -v\n'
            sys.exit(0)
        elif opt in ("-d", "--delay"):
            delay = arg
        elif opt in ("-i", "--interval"):
            interval = arg
        elif opt in ("-v", "--version"):
            print "\nVersion is %s\n" % VERSION
            sys.exit(0)

    if delay == 0:
        delay = delay_default
    if interval == 0:
        interval = interval_default

    app = QtGui.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = QtGui.QWidget()
    tray_icon = SystemTrayIcon(QtGui.QIcon(":/plain.png"), w)
    tray_icon.show()
    app.exec_()


if __name__ == '__main__':
    main(sys.argv[1:])
