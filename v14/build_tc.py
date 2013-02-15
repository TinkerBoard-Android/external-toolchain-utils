#!/usr/bin/python2.6
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""Script to build the ChromeOS toolchain.

This script sets up the toolchain if you give it the gcctools directory.
"""

__author__ = "asharif@google.com (Ahmad Sharif)"

import optparse
import sys
from utils import utils

# Common initializations
(rootdir, basename) = utils.GetRoot(sys.argv[0])
utils.InitLogger(rootdir, basename)


def Main():
  """The main function."""
  parser = optparse.OptionParser()
  parser.add_option("-c", "--chromeos_root", dest="chromeos_root",
                    help="ChromeOS root checkout directory.")
  parser.add_option("-t", "--toolchain_root", dest="toolchain_root",
                    help="Toolchain root directory.")
  parser.add_option("-b", "--board", dest="board",
                    help="board is the argument to the setup_board command.")
  parser.add_option("-C", "--clean", dest="clean",
                    action="store_true", help="Uninstall the toolchain.")
  parser.add_option("-i", "--incremental", dest="incremental",
                    help="The toolchain component that should be "
                    "incrementally compiled.")

  options = parser.parse_args()[0]

  if options.toolchain_root is None or options.board is None:
    parser.print_help()
    sys.exit()

  if options.chromeos_root is None:
    options.chromeos_root = "../.."

  f = open(options.chromeos_root + "/src/overlays/overlay-" +
           options.board + "/toolchain.conf", "r")
  target = f.read()
  f.close()
  target = target.strip()
  features = "noclean"
  env = CreateEnvVarString(" FEATURES", features)
  toolchain_root = "/home/${USER}/toolchain_root"
  env += CreateEnvVarString(" PORT_LOGDIR", toolchain_root + "/log")
  env += CreateEnvVarString(" PKGDIR", toolchain_root + "/pkgs")
  env += CreateEnvVarString(" PORTAGE_TMPDIR", toolchain_root + "/tmp")
  BuildTC(options.chromeos_root, options.toolchain_root, env, target,
          options.clean, options.incremental)


def CreateEnvVarString(variable, value):
  return variable + "=" + EscapeQuoteString(value)


def EscapeQuoteString(string):
  return "\\\"" + string + "\\\""


def BuildTC(chromeos_root, toolchain_root, env, target, uninstall,
            incremental_component):
  """Build the toolchain."""
  binutils_version = "2.20.1-r1"
  gcc_version = "9999"
  libc_version = "2.10.1-r1"
  kernel_version = "2.6.30-r1"
  if incremental_component is not None and len(incremental_component) > 0:
    env += "FEATURES+=" + EscapeQuoteString("keepwork")

  if uninstall == True:
    tflag = " -C "
  else:
    tflag = " -t "

  command = (rootdir + "/tc-enter-chroot.sh")
  if chromeos_root is not None:
    command += " --chromeos_root=" + chromeos_root
  if toolchain_root is not None:
    command += " --toolchain_root=" + toolchain_root
  command += " -- sudo " + env

  if incremental_component == "binutils":
    command += " emerge =cross-" + target + "/binutils-" + binutils_version
  elif incremental_component == "gcc":
    command += " emerge =cross-" + target + "/gcc-" + gcc_version
  elif incremental_component == "libc" or incremental_component == "glibc":
    command += " emerge =cross-" + target + "/glibc-" + libc_version
  else:
    command += (" crossdev -v " + tflag + target +
                " --binutils " + binutils_version +
                " --libc " + libc_version +
                " --gcc " + gcc_version +
                " --kernel " + kernel_version +
                " --portage -b --portage --newuse")

  retval = utils.RunCommand(command)
  return retval

if __name__ == "__main__":
  Main()
