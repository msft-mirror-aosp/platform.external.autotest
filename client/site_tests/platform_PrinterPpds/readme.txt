Tests naming convention
-----------------------
Names of tests (suffixes of control.* files) are build from two words
separated by an underscore character. The first one is 'core' or 'ext', what
defines the set of PPD files to test. These two are described in the section
below. The second word of the name is either 'test' or 'dump'.
Input sets of PPD files ('core' and 'ext')
------------------------------------------
There are two input sets of PPD files to test: 'core' and 'ext'. 'core' is the
smaller one and represents clusters defined in the file large_clusters.txt; it
is built by taking the first element (PPD filename) from every line of this
file. The set 'ext' is built in similar way by taking the first element (PPD
filename) from every line of small_clusters.txt file; however the elements
already present in 'core' are omitted. Currently, 'core' contains around ~130
PPD files; the exact size equals the number of lines in large_clusters.txt.
The set 'ext' contains around ~1400 PPD files; the exact size equals the number
of lines in small_clusters.txt minus the number of lines in large_clusters.txt.

Overall testing procedure
-------------------------
The purpose of this autotest is to verify that given subset of PPD files work
in ChromeOS. Each PPD file is tested with the following procedure:
1. A printer driver is added to CUPS server.
2. Test documents are printed on the configured printer.
3. Raw output from the CUPS server is intercepted by, so called, FakePrinter.
4. CUPS logs are parsed to make sure that no errors occured.
5. Obtained outputs are verified (see below) - test only.
6. All obtained outputs & logs are saved on the device (see below) - dump only.
7. The printer driver is removed from CUPS server.
This procedure is repeated for every PPD file. The number of PPD files may be
large (~2K files). To decrease amount of time needed by the autotest, several
PPD files are tested simultaneously in parallel threads. Autotest always run
the procedure for all given PPD files and print a summary report at the end.
If at least one of PPD files fails, whole autotest is finished with failure
(but always all PPD files are processed).

Output verification ('test')
----------------------------
Intercepted output is verified by comparision with the previous results
obtained for the same PPD. We cannot store outputs directly, because their
total size may have hundreds of megabytes. Instead of that short digest is
calculated for each obtained document and it is used for comparison.
A function for digests calculation is in the 'helpers.py' file. Not all
outputs can be tested this way because for some PPD files produced contents
differ between runs. List of PPD files for which we cannot calculate
constant digest is saved in the file digests_denylist.txt. Files with
expected digests for every test document are stored in the directory "digests".
If a digests for given pair (test document, PPD file) is missing, the test
checks only check if the output is not empty (or not too short).

Save outputs and logs ('dump')
------------------------------
All obtained outputs and logs are saved on the device in the directory
/tmp/PrinterPpds_outputs/. Results obtained from PPD files with the same prefix
are grouped together and stored in single archive to limit usage of disk space.

Test parameters
---------------
path_docs - path to directory with test documents (PDF files)
path_ppds - path to directory with PPD files, it is supposed to be compressed
            as .tar.xz files (with a command "tar cJf ...")
path_digests - path to directory with files containing digests for
            verification, if not set then outputs are not verified
path_outputs - if set, then all outputs are dumped there (given directory is
            deleted if already exists); also all digests files are recalculated
            and saved in the same directory

Generating new digests
----------------------
The following procedure can be used to update digests:
1. Run the test defined in control.all_dump:
        test_that <device IP>  platform_PrinterPpds.all_dump
2. Download generated files with digests to your workstation
        rsync root@<device IP>:/tmp/PrinterPpds_outputs/*.digests <local dir>
3. Replace the files from the "digests" directory and commit changes

Updating the archives with PPD files
------------------------------------
Currently, all tests are based on PPD files stored in local directories. The
autotest can download all PPD files by itself, but we do not use this option
to limit the number of possible points of failures during testing. Archives
with PPD files are prepared with ppdTool.go:
1. Delete old files:
    rm ppds_core.tar.xz ppds_ext.tar.xz large_clusters.txt small_clusters.txt
2. Download all PPD files to ppds_all directory:
    go run ppdTool.go download
3. Calculate new clusters:
    go run ppdTool.go compare
   If it fails with an error "too many open files" you have to increase the
   soft limit of open files with ulimit, e.g.:
    ulimit -Sn 10123
4. Compress new directories with PPD files:
    tar cJf ppds_core.tar.xz ppds_core
    tar cJf ppds_ext.tar.xz ppds_ext
