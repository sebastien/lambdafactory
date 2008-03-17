#!/usr/bin/python
# Encoding: ISO-8859-1
# -----------------------------------------------------------------------------
# Project           :   LambdaFactory
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   Revised BSD License
# -----------------------------------------------------------------------------
# Creation date     :   17-Mar-2008
# Last mod.         :   17-Mar-2008
# -----------------------------------------------------------------------------

from distutils.core import setup

NAME        = "LambdaFactory"
VERSION     = "0.8.6"
WEBSITE     = "http://www.ivy.fr/" + NAME.lower()
SUMMARY     = "Programming language development toolkit"
DESCRIPTION = """\
LambdaFactory is a library/tool/framework that eases the development of
programming languages by allowing you to plug-in your parser, drive the factory,
create your program representation and translate it Python, JavaScript,
ActionScript or Pnuts (and you can add your own).

LambdaFactory provides a fine-grained OO model to represent your program, and
also offers a flexible architecture to insert your own program transformation
passes (documentation, representation, analysis, optimization)
"""

# ------------------------------------------------------------------------------
#
# SETUP DECLARATION
#
# ------------------------------------------------------------------------------

setup(
    name        = NAME,
    version     = VERSION,
    author      = "Sebastien Pierre", author_email = "sebastien@ivy.fr",
    description = SUMMARY, long_description = DESCRIPTION,
    license     = "Revised BSD License",
    keywords    = "program representation, structural analysis, documentation",
    url         =  WEBSITE,
    download_url=  WEBSITE + "/%s-%s.tar.gz" % (NAME.lower(), VERSION) ,
    package_dir = { "": "Distribution" },
    package_data= {
       "lambdafactory.languages.actionscript": ["*.as"],
       "lambdafactory.languages.javascript": ["*.js"]
    },
    packages    = [
        "lambdafactory",
        "lambdafactory.languages",
        "lambdafactory.languages.actionscript",
        "lambdafactory.languages.javascript",
        "lambdafactory.languages.pnuts"
    ],
    classifiers = [
      "Development Status :: 4 - Beta",
      "Environment :: Console",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: BSD License",
      # TODO: Add more here
      "Natural Language :: English",
      "Operating System :: POSIX",
      "Operating System :: Microsoft :: Windows",
      "Programming Language :: Python",
    ]
)

# EOF - vim: tw=80 ts=4 sw=4 noet 
