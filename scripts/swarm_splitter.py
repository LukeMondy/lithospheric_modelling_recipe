"""
Written by Luke Mondy, 2014

When Underworld checkpoints passiveTracer swarms, the XDMF writer sometimes
has trouble keeping the XDMF meta files sane. SwarmSplitter simply creates
new XDMF metafiles for each passiveTracer swarm.

Usage:
   python swarm_splitter.py <path to Underworld output>

The path to the Underworld input MUST be where the XDMF.00000.xmf files are
stored.
"""

import sys

if len(sys.argv) != 2:
    sys.exit(("ERROR - You must provide the path to the data directory. "
              "For example:\n\tpython splitSwarms.py "
              "/data/result_208x96x0_reference_model"))
else:
    data_dir = sys.argv[1]

swarm_header = '<?xml version="1.0" ?>\n<Xdmf xmlns:xi="http://www.w3.org/2001/XInclude" Version="2.0">\n<Grid GridType="Collection" CollectionType="Temporal" Name="FEM_Swarms">'
swarm_footer = '</Grid>\n</Xdmf>'
swarm_entry = '\t<xi:include href="XDMF.{checkpoint}.xmf" xpointer="xpointer(//Xdmf/Domain/Grid[{swarm}])"/>'
temporal_contents = '<?xml version="1.0" ?>\n<Xdmf xmlns:xi="http://www.w3.org/2001/XInclude" Version="2.0">\n\n<Domain>\n\n\t<xi:include href="{0}" xpointer="xpointer(//Xdmf/Grid)"/>\n\n</Domain>\n\n</Xdmf>'


# In[ ]:

swarms = []
try:
    with open("{0}/XDMF.00000.xmf".format(data_dir), 'r') as data_layout_file:
        for line in data_layout_file:
            if "<Grid Name=" in line and "Collection" in line:
                swarm_name = line.split("\"")[1]
                swarms.append(swarm_name)
except IOError as err:
    sys.exit(("ERROR - could not find or open:\n{0}/XDMF.00000.xmf\n"
              "Computer says:\n{1}").format(data_dir, err))

checkpoints = []
try:
    with open("{0}/XDMF.FilesSwarm.xdmf".format(data_dir), 'r') as temporal_file:
        # Skip the first 3 lines
        next(temporal_file)
        next(temporal_file)
        next(temporal_file)
        for line in temporal_file:
            try:
                checkpoints.append(line.split(".")[1])
            except:
                pass
except IOError as err:
    sys.exit(("ERROR - could not find or open:"
              "\n{0}/XDMF.FilesSwarm.xdmf\n"
              "Computer says:\n{1}").format(data_dir, err))


# In[ ]:

for i, s in enumerate(swarms):
    # Build the file into a big list
    filecontents = [swarm_header]
    for ck in checkpoints:
        filecontents.append(swarm_entry.format(checkpoint=ck, swarm=i+2))
    filecontents.append(swarm_footer)

    filename = "XDMF.Files_{0}.xdmf".format(s)
    try:
        with open("{0}/{1}".format(data_dir, filename), 'w') as swarm_file:
            swarm_file.write("\n".join(filecontents))
    except IOError as err:
        sys.exit(("ERROR - A problem has happened when writing:\n{0}/{1}\n"
                  "Computer says:\n{2}").format(data_dir, filename, err))

    temporal_filename = "XDMF.temporal_{0}.xmf".format(s)
    try:
        with open("{0}/{1}".format(data_dir, temporal_filename), 'w') as temporal_file:
            temporal_file.write(temporal_contents.format(filename))
        print "Created new file: {0}/{1}".format(data_dir, temporal_filename)
    except IOError as err:
        sys.exit(("ERROR - A problem has happened when writing:\n{0}/{1}\n"
                  "Computer says:\n{2}").format(data_dir,
                                                temporal_filename,
                                                err))
