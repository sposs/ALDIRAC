'''
Created on Feb 6, 2014

@author: stephanep
'''
from DIRAC import S_OK, S_ERROR, gLogger
import os, re, glob, shutil
from distutils import dir_util, errors

def fullCopy(srcdir, dstdir, item):
    """ Copy the item from srcdir to dstdir, creates missing directories if needed
    """
    item = item.rstrip().lstrip().lstrip("./").rstrip("/")
    srcdir = srcdir.rstrip("/")
    dstdir = dstdir.rstrip("/")
    if not re.match(r"(.*)[a-zA-Z0-9]+(.*)", item):#we want to have explicit elements
        gLogger.error("You try to get all files, that cannot happen")
        return S_OK()
    src = os.path.join(srcdir, item)
    items = glob.glob(src)
    if not items:
        gLogger.error("No items found matching", src)
        return S_ERROR("No items found!")
    
    for item in items:
        item = item.replace(srcdir,"").lstrip("/")
        dst = os.path.join(dstdir, item)
        
        try:
            dir_util.create_tree(dstdir, [item])
        except errors.DistutilsFileError, why:
            return S_ERROR(str(why))
        
        if os.path.isfile(os.path.join(srcdir, item)):
            try:
                shutil.copy2(os.path.join(srcdir, item), dst)
            except EnvironmentError, why:
                return S_ERROR(str(why))
        else:
            try:
                shutil.copytree(os.path.join(srcdir, item), dst)
            except EnvironmentError, why:
                return S_ERROR(str(why))
    return S_OK()
    
