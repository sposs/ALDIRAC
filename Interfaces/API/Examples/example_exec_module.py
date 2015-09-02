#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created by stephanep on 02.09.15

Copyright 2015 Alpes Lasers SA, Neuchatel, Switzerland
"""
import json
import sys

__author__ = 'stephanep'
__copyright__ = "Copyright 2015, Alpes Lasers SA"

if __name__ == "__main__":
    args = sys.argv
    bin_path = args[1]
    parameters = args[2]
    with open(parameters, "r") as p_file:
        p_dict = json.loads(p_file.read())

    print "Would execute a binary in %s using %s as input" % (bin_path, p_dict)
