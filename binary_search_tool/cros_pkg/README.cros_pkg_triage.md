# CrOS's binary search tool

`binary_search_state.py` is a general binary search triage tool that
performs a binary search on a set of things to try to identify which
thing or thing(s) in the set is 'bad'.  `binary_search_state.py` assumes
that the user has two sets, one where everything is known to be good,
ane one which contains at least one bad item.  `binary_search_state.py`
then copies items from the good and bad sets into a working set and
tests the result (good or bad).  `binary_search_state.py` requires that
a set of scripts be supplied to it for any particular job.  For more
information on `binary_search_state.py`, see

https://sites.google.com/a/google.com/chromeos-toolchain-team-home2/home/team-tools-and-scripts/binary-searcher-tool-for-triage

This particular set of scripts is designed to work wtih
`binary_search_state.py` in order to find the bad package or set of
packages in a ChromeOS build.


## QUICKSTART

After setting up your 3 build trees (see Prerequisites section), do the
following:

-   Decide which test script to use (`boot_test.sh` or
    `interactive_test.sh`)
-   Get the IP name or address of the chromebook you will use for testing.
-   Do the following inside your chroot:

    ```
    $ cd ~/trunk/src/third_party/toolchain_utils/binary_search_tool
    $ ./cros_pkg/setup.sh <board-to-test> <IP-name-or-address-of-chromebook>
    ```

    If you chose the boot test, then:

    ```
    $ python ./binary_search_state.py \
        --get_initial_items=cros_pkg/get_initial_items.sh \
        --switch_to_good=cros_pkg/switch_to_good.sh \
        --switch_to_bad=cros_pkg/switch_to_bad.sh \
        --test_setup_script=cros_pkg/test_setup.sh \
        --test_script=cros_pkg/boot_test.sh \
        --file_args \
        --prune
    ```

    Otherwise, if you chose the interactive test, then:

    ```
    $ python ./binary_search_state.py \
        --get_initial_items=cros_pkg/get_initial_items.sh \
        --switch_to_good=cros_pkg/switch_to_good.sh \
        --switch_to_bad=cros_pkg/switch_to_bad.sh \
        --test_setup_script=cros_pkg/test_setup.sh \
        --test_script=cros_pkg/interactive_test.sh \
        --file_args \
        --prune
    ```

    Once you have completely finished doing the binary search/triage,
    run the genereated cleanup script, to restore your chroot to the state
    it was in before you ran the `setup.sh` script:

    ```
    $ cros_pkg/${BOARD}_cleanup.sh
    ```


## FILES AND SCRIPTS

`boot_test.sh` - One of two possible test scripts used to determine
                 if the ChromeOS image built from the packages is good
                 or bad.  This script tests to see if the image
                 booted, and requires no user intervention.

`create_cleanup_script.py` - This is called by setup.sh, to
                             generate ${BOARD}_cleanup.sh,
                             which is supposed to be run by the user
                             after the binary search triage process is
                             finished, to undo the changes made by
                             setup.sh and return everything
                             to its original state.

`get_initial_items.sh` - This script is used to determine the current
                         set of ChromeOS packages.

`test_setup.sh` - This script will build and flash your image to the
                  remote machine. If the flash fails, this script will
                  help the user troubleshoot by flashing through usb or
                  by retrying the flash over ethernet.

`interactive_test.sh` - One of two possible scripts used to determine
                        if the ChromeOS image built from the packages
                        is good or bad.  This script requires user
                        interaction to determine if the image is
                        good or bad.

`setup.sh` - This is the first script the user should call, after
             taking care of the prerequisites.  It sets up the
             environment appropriately for running the ChromeOS
             package binary search triage, and it generates two
             necessary scripts (see below).

`switch_to_bad.sh` - This script is used to copy packages from the
                     'bad' build tree into the work area.

`switch_to_good.sh` - This script is used to copy packages from the
                      'good' build tree into the work area.


## GENERATED SCRIPTS

`common.sh`  - contains basic environment variable definitions for
               this binary search triage session.

`${BOARD}_cleanup.sh` - script to undo all the changes made by
                        running setup.sh, and returning
                        everything to its original state. The user
                        should manually run this script once the
                        binary search triage process is over.

## ASSUMPTIONS

-   There are two different ChromeOS builds, for the same board, with the
    same set of ChromeOS packages.  One build creates a good working ChromeOS
    image and the other does not.

-   You have saved the complete build trees for both the good and bad builds.


## PREREQUISITES FOR USING THESE SCRIPTS (inside the chroot)

-   The "good" build tree, for the board, is in /build/${board}.good
    (e.g. /build/lumpy.good or /build/daisy.good).

-   The "bad" build tree is in /build/${board}.bad
    (e.g. /build/lumpy.bad or /build/daisy.bad).

-   You made a complete copy of the "bad" build tree , and put it in
    /build/${board}.work (e.g. /build/lumpy.work or /build/daisy.work.
    The easiest way to do this is to use something similar to the
    following set of commands (this example assumes the board is
    'lumpy'):

    ```
    $ cd /build
    $ sudo tar -cvf lumpy.bad.tar lumpy.bad
    $ sudo mv lumpy.bad lumpy.work
    $ sudo tar -xvf lumpy.bad.tar
    ```


## USING THESE SCRIPTS FOR BINARY TRIAGE OF PACKAGES

To use these scripts, you must first run setup.sh, passing it two
arguments (in order): the board for which you are building the image;
and the name or ip address of the chromebook you want to use for
testing your chromeos images.  setup.sh will do the following:

-   Verify that your build trees are set up correctly (with good, bad and work).
-   Create a soft link for /build/${board} pointing to the work build tree.
-   Create the common.sh file that the other scripts passed to the binary triage
    tool will need.
-   Create a cleanup script, ${board}_cleanup.sh, for you to run after you are
    done with the binary triages, to undo all of these various changes that
    setup.sh did.

This set of scripts comes with two alternate test scripts.  One test
script, `boot_test.sh`, just checks to make sure that the image
booted (i.e. responds to ping) and assumes that is enough.  The other
test script, `interactive_test.sh`, is interactive and asks YOU
to tell it whether the image on the chromebook is ok or not (it
prompts you and waits for a response).


Once you have run `setup.sh` (and decided which test script you
want to use) run the binary triage tool using these scripts to
isolate/identify the bad package:

```
~/trunk/src/third_party/toolchain_utils/binary_search_tool/binary_search_state.py \
    --get_initial_items=cros_pkg/get_initial_items.sh \
    --switch_to_good=cros_pkg/switch_to_good.sh \
    --switch_to_bad=cros_pkg/switch_to_bad.sh \
    --test_setup_script=cros_pkg/test_setup.sh \
    --test_script=cros_pkg/boots_test.sh \  # could use interactive_test.sh instead
    --prune
```

After you have finished running the tool and have identified the bad
package(s), you will want to run the cleanup script that `setup.sh`
generated (`cros_pkg/${BOARD}_cleanup.sh`).
