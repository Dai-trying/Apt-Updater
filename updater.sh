#!/bin/bash

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


delay=0
interval=0
re='^[0-9]+$'

while [ $# -gt 0 ]; do
    case "$1" in
        -i)
            if [[ ${2-} =~ $re ]] ; then
                interval=(${2-})
            else
                python /usr/share/dai-apt-updater/updater.py -h
                exit 1
            fi
            shift
            ;;
        -d)
            if [[ ${2-} =~ $re ]] ; then
                delay=(${2-})
            else
                python /usr/share/dai-apt-updater/updater.py -h
                exit 1
            fi
            shift
            ;;
        -h)
            python /usr/share/dai-apt-updater/updater.py -h
            exit 0
            ;;
        -v)
            python /usr/share/dai-apt-updater/updater.py -v
            exit 0
            ;;
        *)
            python /usr/share/dai-apt-updater/updater.py -h
            exit 1
            ;;
    esac
    shift
done

if ! mkdir /tmp/apt-updater.lock; then
    printf "Failed to acquire lock.\n" >&2
    exit 1
fi
trap 'rm -rf /tmp/apt-updater.lock' EXIT  # remove the lock-dir on exit

if [ ${interval} == 0 ] && [ ${delay} == 0 ]; then
    python /usr/share/dai-apt-updater/updater.py
    exit 0
fi
if [ ${interval} == 0 ]; then
    python /usr/share/dai-apt-updater/updater.py -d ${delay}
    exit 0
fi
if [ ${delay} == 0 ]; then
    python /usr/share/dai-apt-updater/updater.py -i ${interval}
    exit 0
fi

python /usr/share/dai-apt-updater/updater.py -i ${interval} -d ${delay}
