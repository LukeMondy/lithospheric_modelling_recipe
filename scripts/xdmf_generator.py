
# coding: utf-8
"""
# XDMF Generator

We want a script that can look at the files in a folder and generate a nice
XDMF output for them.

The XDMF/XMF structure for Underworld is as such:
 - XDMF.temporalFields.xmf points to XDMF.FilesField.xdmf
 - XDMF.FilesField.xdmf has a list of all the XDMF.Fields.**timestep**.xmf
   files
 - XDMF.Fields.**timestep**.xmf contains all the info to build a mesh from
   the h5 files.

Generally the problem is in XMDF.FilesField.xdmf, as when Underworld
restarts it can lead to out-of-order or missing entries.

Here is an example XDMF.FilesField.xdmf:

<?xml version="1.0" ?>
<Xdmf xmlns:xi="http://www.w3.org/2001/XInclude" Version="2.0">
<Grid GridType="Collection" CollectionType="Temporal" Name="FEM_Mesh_Fields">
 <xi:include href="XDMF.00000.xmf" xpointer="xpointer(//Xdmf/Domain/Grid[1])"/>
 <xi:include href="XDMF.00002.xmf" xpointer="xpointer(//Xdmf/Domain/Grid[1])"/>
 ...
 <xi:include href="XDMF.00332.xmf" xpointer="xpointer(//Xdmf/Domain/Grid[1])"/>
</Grid>
</Xdmf>
"""

import glob
import argparse
import sys

parser = argparse.ArgumentParser(
    description=('Generates a nice XDMF.temporalFields.xmf file, based on the'
                 ' files existing in the folder. This allows Paraview to read'
                 ' the data smoothly. The problem can come up when you '
                 'restart Underworld quite a lot.'))
parser.add_argument("data_path",
                    help=("The path to your results folder. Must contain the "
                          "XDMF files."))
parser.add_argument("--output_file",
                    help=("The name of new XDMF.TemporalFields.xmf. It will "
                          "be put in the same folder as the data_path."),
                    default="XDMF.CleanTemporalFields.xmf")

args = parser.parse_args()

xdmf_fields_header = (
    "<?xml version=\"1.0\" ?>\n"
    "<Xdmf xmlns:xi=\"http://www.w3.org/2001/XInclude\" Version=\"2.0\">\n"
    "<Grid GridType=\"Collection\" CollectionType=\"Temporal\" Name=\"FEM_Mesh_Fields\">\n"
    )

fields_line_string = '\t<xi:include href="{filename}" xpointer="xpointer(//Xdmf/Domain/Grid[1])"/>'

xdmf_fields_footer = ("</Grid>\n"
                      "</Xdmf>")


try:
    fields_xmf_files = sorted(glob.glob("{dir}/XDMF.Fields.*.xmf".format(dir=args.data_path)))
except Exception as e:
    sys.exit(e)

if len(fields_xmf_files) == 0:
    sys.exit(("ERROR: No files found in {data_path} that look like "
              "XDMF.Fields.*.xmf").format(data_path=args.data_path))


# Take the last chunk of the file path
fields_xmf_files_list = [fields_line_string.format(filename=fi.split("/")[-1])
                         for fi in fields_xmf_files]

try:
    with open("{}/{}".format(args.data_path, args.output_file), 'w') as new_file:
        new_file.write(xdmf_fields_header)
        new_file.write("\n".join(fields_xmf_files_list))
        new_file.write(xdmf_fields_footer)
except Exception as e:
    sys.exit(e)

print "Created file {}/{}".format(args.data_path, args.output_file)
