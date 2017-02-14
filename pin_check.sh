#!/usr/bin/env bash

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

qvers=$( get_q4os_version.sh )
qversion="${qvers:0:1}"

if [ "$qversion" == "1" ]; then
    bad_lines=0
    while read x
    do
        if [[ ! ${x} == 100* ]]; then
            bad_lines=$((bad_lines+1))
        fi
    done << EOF
$(apt-cache policy | grep -iv "Translation-" | grep -e "\-backports/main" -e "\-backports/contrib" -e "\-backports/non-free" | grep -i "Packages" | grep -i "debian")
EOF
    if [[ ${bad_lines} > 0 ]]; then
        echo False
    else
        echo True
    fi

else
    echo True
fi