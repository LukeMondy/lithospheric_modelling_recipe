#!/usr/bin/python

"""
Written by Luke Mondy (luke.s.mondy@gmail.com)

This script reads in lmrStart.xml and interprets it for the LMR.

If you are just trying to use the LMR, you should have no need to modify this 
file. 

To run the LMR, simply run:
$ ./lmrRunModel.py

If an error comes up saying something like:
$ bash: ./lmrRunModel.py: Permission denied

then you will need to run this first:
chmod +x lmrRunModel.py

Then it should work.

"""

# Standard Python Libraries
from __future__ import division
import os, shutil, sys, textwrap
from subprocess import call, STDOUT, check_output
from itertools import chain
import fileinput
import glob

# H5py - http://www.h5py.org/
try:
    import h5py
except ImportError:
    sys.exit("=== ERROR ===\nThe LMR needs to use the Python library h5py. You can obtain it from http://www.h5py.org/, or from your package manager.")

# Python lXML - http://lxml.de/
try:
    from lxml import etree as ElementTree
except ImportError:
    sys.exit("=== ERROR ===\nThe LMR needs to use the Python library lxml. You can obtain it from http://lxml.de/, or from your package manager.")

# NumPy and SciPy - http://www.scipy.org/
try:
    import numpy as np
    import scipy.ndimage as ndimage
except ImportError:
    sys.exit("=== ERROR ===\nThe LMR needs to use the Python libraries NumPy and SciPy. You can obtain them from http://www.scipy.org/, or from your package manager.")

def load_xml(input_xml = 'lmrStart.xml', xsd_location = 'LMR.xsd'):
    """
    ===== xml2dict =================
    Author:  Duncan McGreggor
    License: PSF License
    Website: http://code.activestate.com/recipes/410469-xml-as-dictionary/
    """
    class XmlListConfig(list):
        def __init__(self, aList):
            for element in aList:
                if element:
                    if len(element) == 1 or element[0].tag != element[1].tag:
                        self.append(XmlDictConfig(element))
                    elif element[0].tag == element[1].tag:
                        self.append(XmlListConfig(element))
                elif element.text:
                    text = element.text.strip()
                    if text:
                        self.append(text)

    class XmlDictConfig(dict):
        def __init__(self, parent_element):
            if parent_element.items():
                self.update(dict(parent_element.items()))
            for element in parent_element:
                if len(element):
                    if len(element) == 1 or element[0].tag != element[1].tag:
                        aDict = XmlDictConfig(element)
                    else:
                        aDict = {element[0].tag: XmlListConfig(element)}
                    if element.items():
                        aDict.update(dict(element.items()))
                    self.update({element.tag: aDict})
                elif element.items():
                    self.update({element.tag: dict(element.items())})
                else:
                    self.update({element.tag: element.text.strip()}) # Line modified by LMondy to strip

    try:
        schema = ElementTree.XMLSchema(file=xsd_location)
    except Exception as e:
        sys.exit("Problem with the XSD validation! Computer says:\n%s" % e)

    try:
        tree = ElementTree.parse(input_xml)     # Any errors from mismatching tags will be caught
        schema.validate(tree)                   # Validate against xsd.
        error_log = schema.error_log

    except ElementTree.XMLSyntaxError as e:
        error_log = e.error_log

    finally:    
        if len(error_log) > 0:
            error = "=== Error reading from file %s ===\n" % input_xml

            for num, entry in enumerate(error_log):
                error += '''
                Error {num}:\n
                There was an issue reading in the XML you have used. The code is reporting that on line {line}, this error occured:
                \n\"{message}\"\n
                Please have a look at {input_xml} closely, especially around the mentioned line. If you are still having issues, try using an XML validator online to see where the bug is.\n
                \n'''.format(num=num+1, line=entry.line, message=entry.message, input_xml=input_xml)
            nice_error = "\n".join([textwrap.fill(e.strip()) for e in error.splitlines()])
            sys.exit(nice_error)

    root = tree.getroot()
    return XmlDictConfig(root)



def process_xml(raw_dict):

    def xmlbool(xml_bool_string):
        if xml_bool_string == "true":
            return True
        return False

    model_dict = {}
    command_dict = {}

    # <Model_Resolution>
    model_dict["resolution"] = {}
    for dim in raw_dict["Model_Resolution"].keys():
        model_dict["resolution"][dim] = int(raw_dict["Model_Resolution"][dim])
    command_dict["resolution"] = "--elementResI={resolution[x]} --elementResJ={resolution[y]} --elementResK={resolution[z]}"

    model_dict["dims"] = 2 if model_dict["resolution"]["z"] <= 0 else 3
    command_dict["dims"] = "--dim={dims}"
    # </Model_Resolution>

    # <Output_Controls>
    def process_output_controls(output_controls, model_dict, command_dict, thermal=False):
        text_res = "x".join(map(str, (model_dict["resolution"]["x"], model_dict["resolution"]["y"], model_dict["resolution"]["z"])))
        model_dict["description"] = {"text_res": text_res,
                                     "human_desc": output_controls["description"]}

        model_dict["max_time"] = float(output_controls["experiment_duration_options"]["maximum_time"])
        command_dict["max_time"] = "--end={max_time}"
        model_dict["max_timesteps"] = int(output_controls["experiment_duration_options"]["maximum_steps"])
        command_dict["max_timesteps"] = "--maxTimeSteps={max_timesteps}"

        model_dict["checkpoint_every_x_years"] = float(output_controls["checkpointing_options"]["years"])
        command_dict["checkpoint_every_x_years"] = "--checkpointAtTimeInc={checkpoint_every_x_years}"
        model_dict["checkpoint_every_x_steps"] = int(output_controls["checkpointing_options"]["timesteps"])
        command_dict["checkpoint_every_x_steps"] = "--checkpointEvery={checkpoint_every_x_steps}"
        
        model_dict["output_pictures"] = xmlbool(output_controls["output_pictures"])
        command_dict["output_pictures"] = "--dumpEvery=10" if thermal == False else "--dumpEvery=250"
        if model_dict["output_pictures"] == False:
            command_dict["output_pictures"] = "--components.window.Type=DummyComponent"
        
        model_dict["main_model_resolution"] = model_dict["resolution"]
        
        if thermal == False:
            model_dict["write_to_log"] = xmlbool(output_controls["write_log_file"])        
            if model_dict["write_to_log"] == True:
                command_dict["write_to_log"] = "&> {logfile}"
        else:    
            model_dict["resolution"] = {dim: int(output_controls["thermal_model_resolution"][dim]) for dim in output_controls["thermal_model_resolution"].keys()}

    output_controls = raw_dict["Output_Controls"]
    process_output_controls(output_controls, model_dict, command_dict)

    model_dict["output_path"] = "result_" + "_".join(model_dict["description"].values())
    command_dict["output_path"] = "--outputPath={output_path}"
    model_dict["input_xmls"] = "{output_path}/xmls/lmrMain.xml"
    command_dict["input_xmls"] = "{input_xmls}"

    model_dict["logfile"] = "log_%s.txt" % model_dict["output_path"]
    # </Output_Controls>


    # <Thermal_Equilibration>
    thermal_equilib = raw_dict["Thermal_Equilibration"]

    model_dict["run_thermal_equilibration"] = xmlbool(thermal_equilib["run_thermal_equilibration_phase"])
    model_dict["update_xml_information"] = xmlbool(thermal_equilib["update_xml_information"])
    
    if model_dict["run_thermal_equilibration"]:
        model_dict["preserve_thermal_equilibration_checkpoints"] = xmlbool(thermal_equilib["preserve_thermal_equilibration_checkpoints"])

        output_controls = thermal_equilib["output_controls"]
        process_output_controls(output_controls, model_dict, command_dict, thermal=True)

        model_dict["output_path"] = "initial-condition_" + "_".join(model_dict["description"].values())
        model_dict["input_xmls"] += " {output_path}/xmls/lmrThermalEquilibration.xml"
        model_dict["logfile"] = "log_%s.txt" % model_dict["output_path"]
    # </Thermal_Equilibration>

    # Thermal EQ or not, we need to know where to look for the initial condition files:
    model_dict["initial_condition_desc"] = raw_dict["Thermal_Equilibration"]["output_controls"]["description"]

    # <Restarting_Controls>
    restarting = raw_dict["Restarting_Controls"]
    model_dict["restarting"] = xmlbool(restarting["restart"])
    if model_dict["restarting"] == True:
        model_dict["restart_timestep"] = int(restarting["restart_from_step"])
        command_dict["restart"] = "--restartTimestep={restart_timestep}"
    # </Restarting_Controls>
    
    # <Underworld_Execution>
    uw_exec = raw_dict["Underworld_Execution"]
    model_dict["uwbinary"] = uw_exec["Underworld_binary"]
    command_dict["uwbinary"] = "{uwbinary}"
    if xmlbool(uw_exec["supercomputer_mpi_format"]) == False:
        model_dict["cpus"] = uw_exec["CPUs"]
        command_dict["cpus"] = "mpirun -np {cpus}"
    else:
        command_dict["cpus"] = "mpirun"

    # </Underworld_Execution>

    # <Model_Precision>
    precision = raw_dict["Model_Precision"]
    for solver in precision.keys():
        prefix = solver.split("_")[0]
        model_dict[solver] = {"tolerance":    float(precision[solver]["tolerance"]),
                              "min_iterations": int(precision[solver]["min_iterations"]),
                              "max_iterations": int(precision[solver]["max_iterations"])}
        if model_dict["run_thermal_equilibration"] == True and prefix == "nonLinear":
            model_dict[solver]["max_iterations"] = 1   # So UW doesn't try to nonLinearly solve pure diffusion
        command_dict[solver] = "--{solver}Tolerance={tolerance} --{solver}MinIterations={min_iterations} --{solver}MaxIterations={max_iterations}".format(solver=prefix, tolerance=model_dict[solver]["tolerance"], min_iterations = model_dict[solver]["min_iterations"], max_iterations = model_dict[solver]["max_iterations"])
    # </Model_Precision>

    return model_dict, command_dict


def prepare_job(model_dict, command_dict):

    if model_dict["dims"] == 2 or model_dict["run_thermal_equilibration"] == True:
        command_dict["solver"] = "-Uzawa_velSolver_pc_factor_mat_solver_package mumps -mat_mumps_icntl_14 200 -Uzawa_velSolver_ksp_type preonly -Uzawa_velSolver_pc_type lu"
    else:
        def multigrid_test(number, count = 1):
            if number % 2 == 0:
                return multigrid_test(number / 2, count + 1)
            else:
                return count

        model_dict["mg_levels"] = min(multigrid_test(model_dict["resolution"]["x"]),
                                      multigrid_test(model_dict["resolution"]["y"]),
                                      multigrid_test(model_dict["resolution"]["z"]))

        command_dict["solver"] = "--mgLevels={mg_levels} -A11_ksp_type fgmres -mg_levels_pc_type sor -A11_pc_mg_smoothup 4 -A11_pc_mg_smoothdown 4 -mg_levels_ksp_type minres -mg_levels_ksp_max_it 3 -mg_levels_pc_type sor -mg_levels_ksp_convergence_test skip -mg_coarse_pc_factor_mat_solver_package superlu_dist -mg_accelerating_smoothing_view true -mg_smooths_max 100 -mg_smooths_to_start 1 -mg_smoothing_increment 1 -mg_target_cycles_10fold_reduction 1"

        uw_bin = os.path.model_dict["uwbinary"]
        model_dict["input_xmls"] += " {output_path}/xmls/lmrSolvers.xml"


    # Make the output folders ready for UW.
    output_dir = model_dict["output_path"]
    if not os.path.isdir( output_dir ):
        os.mkdir( output_dir )

    xmls_dir = os.path.join( output_dir, "xmls/" )
    if not os.path.isdir( xmls_dir ):
        os.mkdir( xmls_dir )

    for files in os.listdir("./"):
        if files.endswith(".xml"):
            shutil.copy(files, xmls_dir)

    model_dict["input_xmls"] = model_dict["input_xmls"].format(output_path=model_dict["output_path"])
    return model_dict, command_dict


def run_model(model_dict, command_dict):
    # === To Do ====
    # - Remember, command_dict["write_to_log"] may need to go at the end.

    first = command_dict["cpus"]
    del(command_dict["cpus"])

    second = command_dict["uwbinary"]
    del(command_dict["uwbinary"])

    third = command_dict["input_xmls"]
    del(command_dict["input_xmls"])
    
    prioritised = " ".join((first, second, third))

    remainder = " ".join(command_dict.values())

    together = " ".join((prioritised, remainder))

    command = together.format(**model_dict).split(" ")

    try:
        
        if model_dict["write_to_log"]:
            with open(model_dict["logfile"], "w") as logfile:
                model_run_status = call(command, shell=False, stdout=logfile, stderr=STDOUT)
                print model_run_status
        else:
            model_run_status = call(command, shell=False)
            
        if model_run_status != 0:
            sys.exit("\n\nUnderworld did not exit nicely - have a look at its output to try and determine the problem.")
    except KeyboardInterrupt:
        # This is pretty dangerous...
        call(["pkill", "Underworld"])
        sys.exit("\nYou have cancelled the job - all instances of Underworld have been killed.")

def find_last_thermal_timestep(model_dict):
    thermal_results_dir = "initial-condition_{main_model_resolution[x]}x{main_model_resolution[y]}x{main_model_resolution[z]}_{initial_condition_desc}".format(**model_dict)
    # Look for temp files, which are in the format of: TemperatureField.00000.h5
    try:
        last_ts = max([ int(f.split('/')[-1].split('.')[1]) for f in glob.glob("%s/TemperatureField*" % thermal_results_dir)])
    except:
        if not os.path.isdir( thermal_results_dir ):
            sys.exit("The initial condition folder '%s' does not exist. You must run the thermal equilibration phase first." %  thermal_results_dir)
        else:
            sys.exit("Unable to find any files starting with 'TemperatureField.<some number>.h5' in the folder '%s'. You may need to re-run the thermal equilibration phase, or run it for longer." % thermal_results_dir)
    return last_ts

def modify_initialcondition_xml(last_ts, model_dict):
    prefix = "initial-condition_{main_model_resolution[x]}x{main_model_resolution[y]}x{main_model_resolution[z]}_{initial_condition_desc}".format(**model_dict)
    new_temp_file = "%s/TemperatureField.%05d.h5" % (prefix, last_ts)
    new_mesh_file = "%s/Mesh.linearMesh.%05d.h5" % (prefix, last_ts)
    
    try:
        for line in fileinput.input("{output_path}/xmls/lmrInitials.xml".format(**model_dict), inplace=True):
            if "!!PATH_TO_TEMP_FILE!!" in line:
                print line.replace("!!PATH_TO_TEMP_FILE!!", new_temp_file),
            elif "!!PATH_TO_MESH_FILE!!" in line:
                print line.replace("!!PATH_TO_MESH_FILE!!", new_mesh_file),
            else:
                print line,
    except IOError as err:
        sys.exit("Problem opening lmrInitials.xml to update the HDF5 initial condition.")


def interpolate_to_full_resolution(model_dict, last_ts):

    def longlist2array(longlist):
        """
        Faster implementation of np.array(longlist)
        Source: http://stackoverflow.com/questions/17973507/why-is-converting-a-long-2d-list-to-numpy-array-so-slow
        """
        flat = np.fromiter(chain.from_iterable(longlist), np.array(longlist[0][0]).dtype, -1) # Without intermediate list:)
        return flat.reshape((len(longlist), -1))
    
    
    new_x_res = int(model_dict["main_model_resolution"]["x"])
    new_y_res = int(model_dict["main_model_resolution"]["y"])
    new_z_res = int(model_dict["main_model_resolution"]["z"])

    # === File loading ====================
    init_data_path = model_dict["output_path"]
    temp_file = "TemperatureField.%05.d.h5" % last_ts
    mesh_file = "Mesh.linearMesh.%05.d.h5" % last_ts
    out_data_path = init_data_path

    out_temp_file = "TemperatureField.%05.d.h5" % (last_ts + 1)
    out_mesh_file = "Mesh.linearMesh.%05.d.h5" % (last_ts + 1)

    data_attributes = {}

    try:
        with h5py.File("%s/%s" % (init_data_path, temp_file), "r") as temp:
            np_temp = np.array(temp['data'][...], dtype=np.float32) # This may need to be float64
    except IOError as err:
        sys.exit("Unable to open the TemperatureField file from the thermal equilibration phase. lmrRunModel looked for the file:\n%s/%s\n\nThe hdf5 reader said this:\n%s\n" % (init_data_path, temp_file, err))
    
    try:
        with h5py.File("%s/%s" % (init_data_path, mesh_file), "r") as mesh:    
            np_min = mesh['min'][...]
            np_max = mesh['max'][...]

            np_vert = np.array(mesh['vertices'][...], dtype=np.float64)

            for key in mesh.attrs:
                data_attributes[key] = mesh.attrs[key]  # Make-shift deepcopy
    except IOError as err:
        sys.exit("Unable to open the Mesh.linearMesh file from the thermal equilibration phase. lmrRunModel looked for the file:\n%s/%s\n\nThe hdf5 reader said this:\n%s\n" % (init_data_path, mesh_file, err))
    # === End of File loading =============

    # === Grid stats ======================
    dims = data_attributes["dimensions"]

    xdim = (np_min[0], np_max[0])
    ydim = (np_min[1], np_max[1])
    if dims == 3:
        zdim = (np_min[2], np_max[2])

    nx = data_attributes["mesh resolution"][0] + 1
    ny = data_attributes["mesh resolution"][1] + 1
    if dims == 3:
        nz = data_attributes["mesh resolution"][2] + 1
    # === End of Grid stats ===============

    # === Interpolation ===================
    new_x_res += 1
    new_y_res += 1
    if dims == 3:
        new_z_res += 1

    # ====== Temperature =============
    if dims == 2:
        temp_grid = np_temp.reshape( (ny, nx) )
    else:
        temp_grid = np_temp.reshape( (nz, ny, nx) )

    x_zoom_factor = new_x_res / nx
    y_zoom_factor = new_y_res / ny
    zoom_factors = [x_zoom_factor, y_zoom_factor]
    if dims == 3:
        z_zoom_factor = new_z_res / nz
        zoom_factors.append(z_zoom_factor)
    zoom_factors = tuple(reversed(zoom_factors))

    temp_zoomed_grid = ndimage.zoom(temp_grid, zoom_factors)
    temp_zoomed_lin = np.ravel(temp_zoomed_grid)[:, None]    # Need empty dim for writing back

    data_points = temp_zoomed_lin.shape[0]
    mesh_dim = temp_zoomed_grid.shape
    # ====== End of Temperature ======

    # ====== Mesh ====================
    # ========= Vertices =============
    vert_x = np.linspace(np_min[0], np_max[0], new_x_res).astype(np.float64)
    vert_y = np.linspace(np_min[1], np_max[1], new_y_res).astype(np.float64)
    
    if dims == 3:
        vert_z = np.linspace(np_min[2], np_max[2], new_z_res).astype(np.float64)
    vertices = []
    vert_append = vertices.append
    if dims == 2:
        for y in vert_y:
            for x in vert_x:
                vert_append((x, y))
    else:
        for z in vert_z:
            for y in vert_y:
                for x in vert_x:
                    vert_append((x, y, z))
    np_vertices = longlist2array(vertices)
    # ========= End of Vertices ======

    # ========= Connectivity =========
    """
    Element defined:   3D
         2D          8 --- 7
       4 --- 3      /|    /|
       |     |     4 --- 3 6
       1 --- 2     |     |/
                   1 --- 2
    """
    elements = []
    elem_append = elements.append

    if dims == 2:
        for y in xrange(new_y_res-1):
            nxy = new_x_res * y
            nxyPone = nxy + 1
            nxyOne = new_x_res * (y + 1)
            nxyOnePone = nxyOne + 1
            for x in xrange(new_x_res-1):
                elem_append( (x+nxy, x+nxyPone, x+nxyOnePone, x+nxyOne) )
    else:
        for z in xrange(new_z_res-1):
            nxnyz = new_x_res * new_y_res * z
            for y in xrange(new_y_res-1):
                nxy = new_x_res * y
                nxyPone = nxy + 1
                nxyOne = new_x_res * (y + 1)
                nxyOnePone = nxyOne + 1
                for x in xrange(new_x_res-1):
                    elem_append( (x+nxy,               x+nxyPone, 
                                  x+nxyOnePone,          x+nxyOne, 
                                 (x+nxy)*nxnyz,      ((x+nxy)*nxnyz)+1, 
                                ((x+nxyOne)*nxnyz)+1, (x+nxyOne)*nxnyz))    
    np_elements = longlist2array(elements)
    # ========= End of Connectivity ==
    # ====== End of Mesh =============
    # === End of Interpolation ============


    # === File writing ====================
    res = [ new_x_res-1, new_y_res-1 ] if dims == 2 else [ new_x_res-1, new_y_res-1, new_z_res-1 ]

    try:
        with h5py.File("%s/%s" % (out_data_path, out_temp_file), "w") as out_temp:
            temp_dataset = out_temp.create_dataset("data", (data_points,1), dtype=np.float32)
            temp_dataset[...] = temp_zoomed_lin
            
            for key in ("dimensions", "checkpoint file version"):
                out_temp.attrs[key] = data_attributes[key]
            out_temp.attrs["mesh resolution"] = np.array( res )
    except IOError as err:
        sys.exit("Unable to write to the new TemperatureField file after interpolating from the thermal equilibration phase. lmrRunModel tried to write to file:\n%s/%s\n\nThe hdf5 reader said this:\n%s\n" % (out_data_path, out_temp_file, err))

    try:
        with h5py.File("%s/%s" % (out_data_path, out_mesh_file), "w") as out_mesh:
            max_dataset = out_temp.create_dataset("max", (dims,), dtype=np.float32)
            max_dataset[...] = np_max
            min_dataset = out_temp.create_dataset("min", (dims,), dtype=np.float32)
            min_dataset[...] = np_min
            vertices_dataset = out_temp.create_dataset("vertices", (data_points,dims), dtype=np.float64)
            vertices_dataset[...] = np_vertices
            connectivity_dataset = out_temp.create_dataset("connectivity", (np_elements.shape[0],2**dims), dtype=np.int32)
            connectivity_dataset[...] = np_elements

            for key in ("dimensions", "checkpoint file version"):
                out_mesh.attrs[key] = data_attributes[key]
            out_mesh.attrs["mesh resolution"] = np.array( res )
    except IOError as err:
        sys.exit("Unable to write to the new Mesh.linearMesh file after interpolating from the thermal equilibration phase. lmrRunModel tried to write to file:\n%s/%s\n\nThe hdf5 reader said this:\n%s\n" % (out_data_path, out_temp_file, err))

    # === End of File writing =============



def main():
    raw_dict = load_xml()

    model_dict, command_dict = process_xml(raw_dict)

    model_dict, command_dict = prepare_job(model_dict, command_dict)

    if model_dict["run_thermal_equilibration"] == False:
        last_ts = find_last_thermal_timestep(model_dict)
        if model_dict["update_xml_information"] == True:
            modify_initialcondition_xml(last_ts, model_dict)

    run_model(model_dict, command_dict)
    
    if model_dict["run_thermal_equilibration"] == True:
        last_ts = find_last_thermal_timestep(model_dict)
        print "\nInterpolating last thermal equilibration checkpoint to {x}x{y}x{z}...".format(**model_dict["main_model_resolution"])
        interpolate_to_full_resolution(model_dict, last_ts)
        print "Done."
        if model_dict["preserve_thermal_equilibration_checkpoints"] == False:
            filelist = [ f for f in os.listdir(model_dict["output_path"]) if str(last_ts+1) not in f and "xmls" not in f ]
            for f in filelist:
                os.remove("%s/%s" % (model_dict["output_path"], f))
    
    

if __name__ == '__main__':
    main()

