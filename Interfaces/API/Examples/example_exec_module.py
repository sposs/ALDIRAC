#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created by stephanep on 02.09.15

Copyright 2015 Alpes Lasers SA, Neuchatel, Switzerland
"""
import json
import sys
import pickle


__author__ = 'stephanep'
__copyright__ = "Copyright 2015, Alpes Lasers SA"

if __name__ == "__main__":
    args = sys.argv
    bin_path = args[1]
    parameters = args[2]
    inputdata = None
    if len(args) > 2:
        inputdata = args[3]

    with open(parameters, "r") as p_file:
        p_dict = json.loads(p_file.read())

    print "Would execute a binary in %s using %s as input processing this file %s" % (bin_path, p_dict, inputdata)
    outputfile = p_dict.get(u"OutputFile", "output.pkl")
    print "producing dummy data file for output: %s" % outputfile
    with open(outputfile, "w") as outf:
        d = {"key": 23}
        pickle.dump(d, outf)
