#!/usr/bin/env python

import os
import sys
import logging

logger = logging.getLogger('apt-updater')
log_handler = logging.FileHandler('/tmp/UU_error.log')
logger.addHandler(log_handler)

UU_file = '/etc/apt/apt.conf.d/20auto-upgrades'


def inplace_change(file_name, old_string, new_string):
    with open(file_name) as f:
        s = f.read()
        if old_string not in s:
            return False
    with open(file_name, 'w') as f:
        s = s.replace(old_string, new_string)
        f.write(s)
    return True


if not os.path.exists(UU_file):
    logger.error("File not present")
    sys.exit()

UU_off = 'APT::Periodic::Unattended-Upgrade "0"'
UU_on = 'APT::Periodic::Unattended-Upgrade "1"'

if inplace_change(UU_file, UU_on, UU_off):
    logger.error("UU disabled")
    sys.exit()
else:
    logger.error("UU NOT disabled")
    sys.exit()
