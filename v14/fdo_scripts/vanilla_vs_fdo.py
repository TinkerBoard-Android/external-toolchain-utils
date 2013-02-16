#!/usr/bin/python2.6
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Script to profile a page cycler, and get it back to the host."""

import getpass
import optparse
import os
import sys

import image_chromeos
import setup_chromeos
from utils import command_executer
from utils import misc
from utils import logger


class Patcher(object):
  def __init__(self, dir_to_patch, patch_file):
    self._dir_to_patch = dir_to_patch
    self._patch_file = patch_file
    self._base_patch_command = "patch -p0 %%s < %s" % patch_file
    self._ce = command_executer.GetCommandExecuter()

  def _RunPatchCommand(self, args):
    patch_command = self._base_patch_command % args
    command = ("cd %s && %s" % (self._dir_to_patch,
                                patch_command))
    return self._ce.RunCommand(command)

  def _ApplyPatch(self, args):
    full_args = "%s --dry-run" % args
    ret = self._RunPatchCommand(full_args)
    if ret:
      raise Exception("Patch dry run failed!")
    ret = self._RunPatchCommand(args)
    if ret:
      raise Exception("Patch application failed!")

  def __enter__(self):
    self._ApplyPatch("")

  def __exit__(self, type, value, traceback):
    self._ApplyPatch("-R")


class FDOComparator(object):
  def __init__(self, board, remotes, ebuild_version):
    self._board = board
    self._remotes = remotes
    self._ebuild_version = ebuild_version
    self._remote = remotes.split(",")[0]
    self._chromeos_root = "chromeos"
    self._profile_dir = "profile_dir"
    self._profile_path = os.path.join(self._chromeos_root,
                                      "src",
                                      "scripts",
                                      os.path.basename(self._profile_dir))

    self._ce = command_executer.GetCommandExecuter()
    self._l = logger.GetLogger()

  def _CheckoutChromeOS(self):
    if not os.path.exists(self._chromeos_root):
      setup_chromeos_args = [setup_chromeos.__file__,
                             "--dir=%s" % self._chromeos_root,
                             "--minilayout"]
      setup_chromeos.Main(setup_chromeos_args)

  def _BuildChromeOSUsingBinaries(self):
    image_dir = misc.GetImageDir(self._chromeos_root, self._board)
    command = "equery-%s l chromeos" % self._board
    ret = self._ce.ChrootRunCommand(self._chromeos_root, command)
    if ret:
      command = misc.GetSetupBoardCommand(self._board,
                                           usepkg=True)
      ret = self._ce.ChrootRunCommand(self._chromeos_root,
                                      command)
      if ret:
        raise Exception("Couldn't run setup_board!")
      command = misc.GetBuildPackagesCommand(self._board,
                                              True)
      ret = self._ce.ChrootRunCommand(self._chromeos_root,
                                    command)
      if ret:
        raise Exception("Couldn't run build_packages!")

  def _ReportMismatches(self, build_log):
    mismatch_signature = "-Wcoverage-mismatch"
    mismatches = build_log.count(mismatch_signature)
    self._l.LogOutput("Total mismatches: %s" % mismatches)
    stale_files = set([])
    for line in build_log.splitlines():
      if mismatch_signature in line:
        filename = line.split(":")[0]
        stale_files.add(filename)
    self._l.LogOutput("Total stale files: %s" % len(stale_files))

  def _BuildChromeAndImage(self, ebuild_version="", env_dict={}, cflags="",
                           cxxflags="", ldflags="", label=""):
    env_string = misc.GetEnvStringFromDict(env_dict)
    if not label:
      label = " ".join([env_string,
                        cflags,
                        cxxflags,
                        ldflags,
                        ebuild_version])
      label = label.strip()
      label = misc.GetFilenameFromString(label)
    if not misc.DoesLabelExist(self._chromeos_root, self._board, label):
      build_chrome_browser_args = ["--clean",
                                   "--chromeos_root=%s" % self._chromeos_root,
                                   "--board=%s" % self._board,
                                   "--env=%r" % env_string,
                                   "--cflags=%r" % cflags,
                                   "--cxxflags=%r" % cxxflags,
                                   "--ldflags=%r" % ldflags,
                                   "--ebuild_version=%s" % ebuild_version]

      build_chrome_browser = os.path.join(os.path.dirname(__file__),
                                          "..",
                                          "build_chrome_browser.py")
      command = "python %s %s" % (build_chrome_browser,
                                  " ".join(build_chrome_browser_args))
      ret, out, err = self._ce.RunCommand(command,
                                          return_output=True)
      if "-fprofile-use" in cxxflags:
        self._ReportMismatches(out)

      if ret:
        raise Exception("Couldn't build chrome browser!")
      misc.LabelLatestImage(self._chromeos_root, self._board, label)
    return label

  def _TestLabels(self, labels):
    experiment_file = "pgo_experiment.txt"
    experiment_header = """
    board: %s
    remote: %s
    """ % (self._board, self._remotes)
    experiment_tests = """
    benchmark: desktopui_PageCyclerTests {
      iterations: 5
    }
    """
    with open(experiment_file, "w") as f:
      print >>f, experiment_header
      print >>f, experiment_tests
      for label in labels:
        # TODO(asharif): Fix crosperf so it accepts labels with symbols
        crosperf_label = label
        crosperf_label = crosperf_label.replace("-", "minus")
        crosperf_label = crosperf_label.replace("+", "plus")
        experiment_image = """
        %s {
          chromeos_image: %s
        }
        """ % (crosperf_label,
               os.path.join(misc.GetImageDir(self._chromeos_root, self._board),
                            label,
                            "chromiumos_test_image.bin"))
        print >>f, experiment_image
    crosperf = os.path.join(os.path.dirname(__file__),
                            "..",
                            "crosperf",
                            "crosperf")
    command = "%s %s" % (crosperf, experiment_file)
    ret = self._ce.RunCommand(command)
    if ret:
      raise Exception("Couldn't run crosperf!")

  def _ImageRemote(self, label):
    image_path = os.path.join(misc.GetImageDir(self._chromeos_root,
                                                self._board),
                              label,
                              "chromiumos_test_image.bin")
    image_chromeos_args = [image_chromeos.__file__,
                           "--chromeos_root=%s" % self._chromeos_root,
                           "--image=%s" % image_path,
                           "--remote=%s" % self._remote,
                           "--board=%s" % self._board]
    image_chromeos.Main(image_chromeos_args)

  def _ProfileRemote(self):
    profile_cycler = os.path.join(os.path.dirname(__file__),
                                  "profile_cycler.py")
    profile_cycler_args = ["--chromeos_root=%s" % self._chromeos_root,
                           "--cycler=all",
                           "--board=%s" % self._board,
                           "--profile_dir=%s" % self._profile_path,
                           "--remote=%s" % self._remote]
    command = "python %s %s" % (profile_cycler, " ".join(profile_cycler_args))
    ret = self._ce.RunCommand(command)
    if ret:
      raise Exception("Couldn't profile cycler!")

  def _BuildGenerateImage(self):
    # TODO(asharif): add cflags as well.
    # TODO(asharif): Should not have to apply this patch...
    # First patch the tree
    with Patcher(os.path.join(self._chromeos_root,
                              "chroot",
                              misc.GetChromeSrcDir()),
                 "/home/asharif/fdo_scripts/pgo.patch"):
      cxxflags = "-fprofile-generate -w"
      labels_list = ["fprofile-generate", self._ebuild_version]
      label = "_".join(labels_list)
      generate_label = self._BuildChromeAndImage(
          env_dict={"USE": "-pgo"},
          cxxflags=cxxflags,
          ldflags="%s -lgcov" % cxxflags,
          label=label,
          ebuild_version=self._ebuild_version)
      return generate_label

  def _BuildUseImage(self):
    ctarget = misc.GetCtargetFromBoard(self._board, self._chromeos_root)
    chroot_profile_dir = os.path.join("/home/%s/trunk" % getpass.getuser(),
                                      "src",
                                      "scripts",
                                      self._profile_dir,
                                      ctarget)
    cflags = ("-fprofile-use "
              "-fprofile-correction "
              "-Wno-error "
              "-fopt-info=0 "
              "-fno-vpt "
              "-fprofile-dir=%s" %
              chroot_profile_dir)
    labels_list = ["updated_pgo", self._ebuild_version]
    label = "_".join(labels_list)
    pgo_use_label = self._BuildChromeAndImage(
        env_dict={"USE": "-pgo"},
        cflags=cflags,
        cxxflags=cflags,
        ldflags=cflags,
        label=label,
        ebuild_version=self._ebuild_version)
    return pgo_use_label

  def DoAll(self):
    self._CheckoutChromeOS()
    self._BuildChromeOSUsingBinaries()

    vanilla_label = self._BuildChromeAndImage(env_dict={"USE": "-pgo"},
                                              ebuild_version=self._ebuild_version)
    pgo_label = self._BuildChromeAndImage(env_dict={"USE": "+pgo"},
                                          ebuild_version=self._ebuild_version)
    #self._TestLabels([vanilla_label, pgo_label])

    if not os.path.exists(self._profile_path):
      # Build Chrome with -fprofile-generate
      generate_label = self._BuildGenerateImage()
      # Image to the remote box.
      self._ImageRemote(generate_label)
      # Profile it using all page cyclers.
      self._ProfileRemote()

    # Use the profile directory to rebuild it.
    updated_pgo_label = self._BuildUseImage()
    # Run crosperf on all images now.
    self._TestLabels([vanilla_label, pgo_label, updated_pgo_label])
    return 0


def Main(argv):
  """The main function."""
  # Common initializations
###  command_executer.InitCommandExecuter(True)
  command_executer.InitCommandExecuter()
  parser = optparse.OptionParser()
  parser.add_option("--remote",
                    dest="remote",
                    help="Remote machines to run tests on.")
  parser.add_option("--board",
                    dest="board",
                    default="x86-zgb",
                    help="The target board.")
  parser.add_option("--ebuild_version",
                    dest="ebuild_version",
                    default="",
                    help="The Chrome ebuild version to use.")
  options, _ = parser.parse_args(argv)
  if not options.board:
    print "Please give a board."
    return 1
  if not options.remote:
    print "Please give at least one remote machine."
    return 1
  fc = FDOComparator(options.board, options.remote, options.ebuild_version)
  return fc.DoAll()


if __name__ == "__main__":
  retval = Main(sys.argv)
  sys.exit(retval)
