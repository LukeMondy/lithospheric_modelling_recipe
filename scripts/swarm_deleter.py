import glob
import sys
import os
import argparse


try:
    import numpy as np
except ImportError as e:
    sys.exit("This script requires numpy\n")


def main():
    parser = argparse.ArgumentParser(description=("For cleaning up the very"
                                                  " heavy materialSwarm files"))
    parser.add_argument("data_path",
                        help=("The path to your results folder. Must contain "
                              "the FrequentOutput.dat file."))

    parser.add_argument("--reference_files",
                        default="VelocityField",
                        help=("The script needs to figure out which timesteps"
                              " were checkpointed. To do so, it looks at some"
                              " reference files. The default is VelocityField"
                              " but you may specify your own. It will add a *"
                              " to the end of what you provide."))

    parser.add_argument("--keep_interval",
                        type=float,
                        default=3.15569e13,
                        help=("This number tells the script how often to keep"
                              " a checkpoint. The default is every 1 Myr."
                              " For example, since the default keep_interval"
                              " is 1 Myr, and checkpoints output every 50 kyr"
                              ", then this script will delete all checkpoints"
                              " except every ~20th one.\n"
                              "This parameter takes time in seconds! For ref"
                              ", 1 Myr = 3.15569e13 seconds."))

    parser.add_argument("--for_real",
                        action='store_true',
                        default=False,
                        help=("The script runs in test-mode by default. When"
                              " you are ready to really delete files, add "
                              "this flag."))

    args = parser.parse_args()

    folder = args.data_path
    reference_files_pattern = args.reference_files
    keep_interval = args.keep_interval
    test_run = False if args.for_real else True
    # Backwards way of doing this: If for_real, test_run is false

    if not reference_files_pattern.endswith("*"):
        reference_files_pattern += "*"

    try:
        timing_data = np.loadtxt("{folder}/FrequentOutput.dat".format(folder=folder))
    except IOError as ioe:
        sys.exit("Unable to find the FrequentOutput.dat file. Here is what the computer says:\n{0}".format(ioe))

    reference_files = sorted(glob.glob("{folder}/{ref_pattern}".format(folder=folder, ref_pattern=reference_files_pattern)))
    if len(reference_files) == 0:
        sys.exit(("Unable to find any {ref_pattern} files in {folder}. These are used to see how many "
                  "timesteps were actually checkpointed out.").format(folder=folder, ref_pattern=reference_files_pattern))

    checkpoints = [int(cpf.split(".")[-2]) for cpf in reference_files]


    time_since_kept = 0
    prev_time = 0
    dont_delete = [0]
    last_available_chpt = None

    for time in timing_data:
        time_since_kept += time[1] - prev_time

        if int(time[0]) in checkpoints:
            last_available_chpt = int(time[0])
            if time_since_kept > keep_interval:
                dont_delete.append(int(time[0]))
                time_since_kept = 0

        prev_time = time[1]

    if last_available_chpt not in dont_delete:
        dont_delete.append(last_available_chpt)

    for saved in dont_delete:
        print "Not deleting materialSwarm.{0:05d}.*".format(saved)

    for chkpt in checkpoints:
        if chkpt in dont_delete:
            continue
        if test_run:
            print "TEST -",
        print "Deleting materialSwarm.{0:05d}.*".format(chkpt),
        if not test_run:
            dead_files = glob.glob("{0!s}/materialSwarm.{1:05d}.*".format(folder, chkpt))
            if len(dead_files) == 0:
                print "- already deleted",
            else:
                for df in dead_files:
                    os.remove(df)
                print "- done",
        print

    if test_run:
        print "\nTest complete. To actually do this, run with the --for_real flag"
    else:
        print "\nDone cleaning"

if __name__ == "__main__":
    sys.exit(main())
