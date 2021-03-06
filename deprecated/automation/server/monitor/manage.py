#!/usr/bin/python2
#
# Copyright 2011 Google Inc. All Rights Reserved.
#

__author__ = 'kbaclawski@google.com (Krystian Baclawski)'

from django.core.management import execute_manager

try:
  import settings  # Assumed to be in the same directory.
except ImportError:
  import sys

  sys.stderr.write('Error: Can\'t find settings.py file in the directory '
                   'containing %r.' % __file__)
  sys.exit(1)

if __name__ == '__main__':
  execute_manager(settings)
