=============
Using ALDIRAC
=============

Obtaining a certificate
=======================

To obtain a user certificate, one needs to use SimpleAuthority. It's located under ``/common/exe/simpleauthority``, and the program is ``sauth``. 
To issue a certificate, simply click on the button on the top left, then fill in the information, and finally, create the certificate by
clicking on the ``new certificate`` button on the bottom of the window. This will require the CA certificate, and it's the "normal" root password starting with G.
It will also require a user specific password, **DO NOT USE THE ROOT PASSWORD** here.

This will also produce on your desktop the certificate, under ``.p12`` format (and ``.cer``, but it's not needed). You can then import that file into your browser 
(check its doc on how to do that, it depends on the browser). At this stage, a dirac administrator (S Poss) need to register you in the dirac system.

Using DIRAC
===========

With the certificate loaded in the browser, and after being registered in the system, you can connect to the 
`dirac server <https://dirac.internal.alp:8443/DIRAC>`_. It's possible that the connection could be considered as untrusted by the browser (due to 
certificate/hostname differences), so just add a permanent exception. 

You can also use the DIRAC client, after obtaining the pem files. To get them, use the following::

  source /common/exe/dirac/bashrc
  dirac-cert-convert.sh path_to_cert.p12

You'll need to enter your password a few times. Once this is done, you can test that everything works by issuing a::

  dirac-proxy-init
  
call that will create a 24h long proxy. If you get something like ``/C=CH/O=AlpesLasers/CN=user isn't registered``, it means something isn't right. In that case, 
contact S Poss for assistance.

Obtaining a proxy is mandatory for ALL dirac interactions, as all connections are secured.

