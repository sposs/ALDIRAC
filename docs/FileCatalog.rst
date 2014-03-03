============
File catalog
============

Description
===========

The FileCatalog intends to provide the means to store file meta data and Physical File Names (PFN) under a directory-like structure, where the path to a file 
is its Logical File Name (LFN). 

The file meta data can be anything which can be represented as ``int``, ``float``, ``string``, ``date``. For example, in the study of designs, the DesignID is a valid 
meta data. Another example is the temperature at which a sewlab ran was performed. The creation date of a file is also a valid meta	data. Those meta data can be
defined as searchable (i.e. which can be used for file queries), and non searchable (i.e. only informative). 

The meta data can be assigned to a directory (directory-level meta data), or to a file (file-level meta data). The latter is less efficient when doing queries, so
directory-level should be preferred.

A LFN can have many PFNs, one for each storage element on which the file is physically stored. This isn't too relevant as there is only 1 Storage Element available 
for the moment, but it may be relevant later. In particular, if data is to be made available to clients, we could think about them providing a Storage Element, and
there would be automatic replications between Storage Elements.

Proposed file structure
=======================

In the context of the study of designs, the proposed file structure is::

  /alpeslasers/simu/DesignID/SimuID/000/DesignID_SimuID_TaskID.ext

The ``/alpeslasers/`` part is mandatory, due to conventions in DIRAC. The ``simu/`` allows a separation with user files, located under ``/alpeslasers/user/`` by
convention. The DesignID is the numerical identifier of the design. At that level, one could have several meta data::

  DesignID/
    |_ commonname
    |_ insertiondate
    \_ whatever else
    
Then, the next level ``SimuID/`` is the simulation ID. It holds simulation specific information::

  SimuID/
    |_ creationdate
    |_ sewlab_param_1
    |_ sewlab_param_2
    [...]
    \_ sewlab_param_n

Then, due to some file system restrictions, the files are split in chunks of 1000 under the directories ``000``, which are file_number%1000. Finally, the file name
holds the essential information needed to recover its origins: the DesignID, SimuID, TaskID. It also holds file level meta data::

  DesignID_SimuID_TaskID.ext
    |_ temperature
    |_ efield
    \_ whatever

The ``.ext`` is a generic placeholder as it still remains to be determined.

It must be noted that the directory structure is extremely rigid: once it's in use, it's very difficult to change it, as it's not possible to move files between 
directories on distributed computing systems: it requires copying the file locally, removing on the Storage Element, reupload to the new location. 
On the other hand, the meta data is very flexible as it's always possible to add/remove meta data indices.
