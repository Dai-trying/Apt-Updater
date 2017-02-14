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
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with apt-updater.  If not, see <http://www.gnu.org/licenses/>.

import sys
import apt_pkg


class OpNullProgress(object):
    def update(self):
        pass

    def done(self):
        pass


def do_quick_check():
    apt_pkg.init()
    try:
        cache = apt_pkg.Cache(OpNullProgress())
    except SystemError, e:
        print("Error: Failed to open cache (%s)" % e)
        sys.exit(9)
    dep_cache = apt_pkg.DepCache(cache)
    dep_cache.read_pinfile()
    dep_cache.init()
    if dep_cache.broken_count > 0:
        print("Error: There are Broken packages, please fix this first.")
        sys.exit(9)
    try:
        dep_cache.upgrade(True)
        if dep_cache.del_count > 0:
            dep_cache.init()
        dep_cache.upgrade()
    except SystemError, e:
        print("Error: Failed to mark the package for upgrade (%s)" % e)
        sys.exit(9)
    updates = 0
    for pkg in cache.packages:
        if not (dep_cache.marked_install(pkg) or dep_cache.marked_upgrade(pkg)):
            continue
        updates += 1
    if updates == 0:
        return True
    else:
        return False


def do_check():
    def is_security_update(package):
        for (filename, index) in package.file_list:
            if filename.label == "Debian-Security":
                return True
        return False
    apt_pkg.init()
    try:
        cache = apt_pkg.Cache(OpNullProgress())
    except SystemError, e:
        print("Error: Failed to open cache (%s)" % e)
        sys.exit(9)
    dep_cache = apt_pkg.DepCache(cache)
    dep_cache.read_pinfile()
    dep_cache.init()
    if dep_cache.broken_count > 0:
        print("Error: There are Broken packages, please fix this first.")
        sys.exit(9)
    try:
        dep_cache.upgrade(True)
        if dep_cache.del_count > 0:
            dep_cache.init()
        dep_cache.upgrade()
    except SystemError, e:
        print("Error: Failed to mark the package for upgrade (%s)" % e)
        sys.exit(9)
    updates = 0
    security_updates = 0
    for pkg in cache.packages:
        candidate = dep_cache.get_candidate_ver(pkg)
        current = pkg.current_ver
        if not (dep_cache.marked_install(pkg) or dep_cache.marked_upgrade(pkg)):
            continue
        updates += 1
        if is_security_update(candidate):
            security_updates += 1
        else:
            for version in pkg.version_list:
                if current and apt_pkg.version_compare(version.ver_str, current.ver_str) <= 0:
                    continue
                if is_security_update(version):
                    security_updates += 1
                    break
    return updates, security_updates

if __name__ == "__main__":
    print do_check()
