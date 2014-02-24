===================
Software management
===================

Preparing the software for installation
=======================================

The AlpesLasers ``Packages`` must be made available on a server that has very limited access rights. This server's address should be set in the Configuration
Service (CS) under::

  /Operations/Defaults/SoftwareInstall/Host

In addition, the user (referred to as 'User' later on) used to connect via ssh should be set in the CS under::

  /Operations/Defaults/SoftwareInstall/User

Finally, the root path under which the ``Packages`` directory is located is set in the CS under::

  /Operations/Defaults/SoftwareInstall/Path

Additional software can be put also at the same level as the ``Packages``. For example, ``sewlab`` should be added as a parallel directory to the ``Packages``.

Setting up the running hosts
============================

The last version of ALDIRAC must be installed on the host. Ideally, and certainly in some future, this installation will be done automatically when the host boots.

Then as DIRAC is ran as root (on Amazon EC2), when preparing the hosts, one should create an ssh key as root with::

  ssh-keygen -t dsa
  
This will create the key of type dsa, a bit more secure than rsa, and it's also supported by SSH2 (which should be always used). Make sure you don't
set a password, as we want to have automatic connections.

Once the key is created, you'll have 2 new files ``$HOME/.ssh/id_dsa`` and ``$HOME/.ssh/id_dsa.pub``. The ``.pub`` file is the public key. You need to copy this file
to the server hosting the software, then add its content to the ``authorized_keys`` of the User::

  cat id_dsa.pub >> $HOME/.ssh/authorized_keys

where you'll be connected as the User.

This allows secured, but without password, connections from the running host (a VM on amazon for example) to the host serving our software.

Clearly, this should be done for ALL the AMIs needed. Currently, there are 2, one for micro (free) instances, and one for "expensive" instances. Also, if using the 
local farm ``AL.farm.ch``, it should also be done on all the machines, using the Dirac user.

Installation procedure
======================

The installation procedure is followed by the module under ``ALDIRAC.Core.Utilities.SoftwareInstall``. It uses ``rsync`` to synchronize the ``Packages`` directory. 
Then it installs the ``sewlabwrapper`` given the local cache. This also installs the ``configuration_manager`` as this is in the dependencies.

As for sewlab itself, this still needs to be sorted out: the compilation of a given version needs to be performed on Amazon, then the binaries need to be brought
back from there into the host serving the software. The versioning scheme needs to be sorted out.


