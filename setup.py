#!/usr/bin/python
# Encoding: ISO-8859-1
# vim: tw=80 ts=4 sw=4 fenc=latin-1 noet
# -----------------------------------------------------------------------------
# Project           :   LambdaFactory         <http://www.ivy.fr/lambdafactory>
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Revised BSD License
# -----------------------------------------------------------------------------
# Creation date     :   06-Nov-2006
# Last mod.         :   06-Nov-2006
# -----------------------------------------------------------------------------

import sys ; sys.path.insert(0, "Sources")
import lambdafactory
from distutils.core import setup

NAME        = "LambdaFactory"
VERSION     = lambdafactory.__version__
WEBSITE     = "http://www.ivy.fr/" + name.lower()
SUMMARY     = "Fine-grained object-oriented program structural representation."
DESCRIPTION = """\
LambdaFactory is a library to create object-oriented representation of programs.
It can be used for writing new languages, manipulating existing language source
code, generate API documentation, graph program structure, etc.

LambdaFactory integrates a type system that enables to easy addition of type
verification on top of existing program models. LambdaFactory is also integrated
with the SDoc <http://www.ivy.fr/sdoc> API generation tool, which allows easy
representation of existing program structures.
"""
# ------------------------------------------------------------------------------
#
# SETUP DECLARATION
#
# ------------------------------------------------------------------------------

setup(
    name        = NAME
    version     = VERSION
    author      = "Sebastien Pierre", author_email = "sebastien@type-z.org",
    description = SUMMARY, long_description = DESCRIPTION,
    license     = "Revised BSD License",
    keywords    = "program representation, structural analysis, documentation",
    url         =  WEBSITE,
    download_url=  WEBSITE + "/%s-%s.tar.gz" % (NAME.lower(), VERSION) ,
    package_dir = { "": "Sources" },
    packages    = ["sink"],
    #scripts     = ["Scripts/"],
    classifiers = [
      "Development Status :: 4 - Beta",
      "Environment :: Web Environment",
      "Intended Audience :: Developers",
      "Intended Audience :: Information Technology",
      "License :: OSI Approved :: BSD License",
      "Natural Language :: English",
      "Topic :: System :: Archiving :: Backup",
      "Topic :: System :: Archiving :: Mirroring",
      "Topic :: System :: Filesystems",
      "Topic :: Utilities",
      "Operating System :: POSIX",
      "Operating System :: Microsoft :: Windows",
      "Programming Language :: Python",
    ]
)

# EOF
