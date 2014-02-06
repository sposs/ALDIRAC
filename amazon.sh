#!/bin/bash

adduser dirac -d /opt/dirac
su dirac -c"mkdir -p /opt/dirac/etc/grid-security"
cp /home/ec2-user/amazon-test.p12 /opt/dirac/etc/grid-security
cd /opt/dirac/etc/grid-security
openssl pkcs12 -in amazon-test.p12 -clcerts -nokeys -out hostcert.pem
openssl pkcs12 -in amazon-test.p12 -nocerts -nodes -out hostkey.pem
chown dirac:dirac host*
rm -f amazon-test.p12
su dirac -c"chown 0400 hostkey.pem"
cd /opt/dirac
wget --no-check-certificate -O dirac-install 'https://github.com/DIRACGrid/DIRAC/raw/integration/Core/scripts/dirac-install.py'
chmod a+x dirac-install
su dirac -c'python dirac-install -r v6r10p8 -e VMDIRAC'
source bashrc
