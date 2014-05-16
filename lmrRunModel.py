# Standard Python Libraries
from __future__ import division
import os
import shutil
import sys
import textwrap
import subprocess
import fileinput
import glob
import copy
from itertools import chain

# External Python packages required:
#  - h5py - http://www.h5py.org/
#  - Python lXML - http://lxml.de/
#  - NumPy and SciPy - http://www.scipy.org/
# Each are imported when required.


# Python lXML - http://lxml.de/
have_lxml = True
try:
    from lxml import etree as ElementTree
except ImportError:
    have_lxml = False
    print "=== WARNING ===\n Unable to find the Python library lxml. The LMR can still run, but will not be able to validate the lmrStart.xml file. You can obtain it from: http://lxml.de/, or from your package manager."
    from xml.etree import cElementTree as ElementTree 


def load_xml(input_xml='lmrStart.xml', xsd_location='LMR.xsd'):
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
                    self.update({element.tag: element.text.strip()})  # Line modified by LMondy to strip

    error_log = ""
    try:
        tree = ElementTree.parse(input_xml)     # Any errors from mismatching tags will be caught
        
        if have_lxml is True:
            # If we have lxml, get the schema and parse it
            try:
                schema = ElementTree.XMLSchema(file=xsd_location)
            except Exception as e:
                sys.exit("Problem with the XSD validation! Computer says:\n%s" % e)   
            
            schema.validate(tree)                   # Validate against xsd.
            error_log = schema.error_log
    
    except ElementTree.XMLSyntaxError as e:
        error_log = e.error_log
    
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

    # Initialise some standard stuff
    model_dict = {"input_xmls": "{output_path}/xmls/lmrMain.xml", }

    command_dict = {"input_xmls":               "{input_xmls}",
                    "resolution":               "--elementResI={resolution[x]} \
                                                 --elementResJ={resolution[y]} \
                                                 --elementResK={resolution[z]}",
                    "dims":                     "--dim={dims}",
                    "output_path":              "--outputPath={output_path}",
                    "output_pictures":          "--components.window.Type=DummyComponent",
                    "max_time":                 "--end={max_time}",
                    "max_timesteps":            "--maxTimeSteps={max_timesteps}",
                    "checkpoint_every_x_years": "--checkpointAtTimeInc={checkpoint_every_x_years}",
                    "checkpoint_every_x_steps": "--checkpointEvery={checkpoint_every_x_steps}",
                    "uwbinary":                 "{uwbinary}",
                    "cpus":                     "mpirun", }

    # <Output_Controls>
    def process_output_controls(output_controls, model_dict, command_dict, thermal=False):
        resolution_key = "model_resolution" if thermal is False else "thermal_model_resolution"

        # Process the generic stuff
        #  - Get the resolution
        resolution = {}
        try:
            for dim in output_controls[resolution_key].keys():
                resolution[dim] = int(output_controls[resolution_key][dim])
        except Exception as e:
            print e
            print output_controls
            sys.exit()

        text_res = "x".join(map(str, (resolution["x"], resolution["y"], resolution["z"])))

        #  - Time controls
        model_dict["max_time"] = float(output_controls["experiment_duration_options"]["maximum_time"])
        model_dict["max_timesteps"] = int(output_controls["experiment_duration_options"]["maximum_timesteps"])
        model_dict["checkpoint_every_x_years"] = float(output_controls["checkpoint_frequency_options"]["every_x_years"])
        model_dict["checkpoint_every_x_steps"] = int(output_controls["checkpoint_frequency_options"]["every_x_timesteps"])

        # The thermal and thermo-mechanical output_controls have some specialised functions
        # Handle each differently:
        if thermal is False:
            # process output pics, and write_log
            model_dict["write_to_log"] = xmlbool(output_controls["write_log_file"])

            model_dict["output_pictures"] = xmlbool(output_controls["output_pictures"])
            if model_dict["output_pictures"] is True:
                command_dict["output_pictures"] = "--dumpEvery=10" if thermal is False else "--dumpEvery=250"

            # Dims is a global - you won't want a 3d thermal initial condition for a 2D model!
            model_dict["dims"] = 2 if resolution["z"] <= 0 else 3

            model_dict["description"] = "{text_res}_{description}".format(text_res=text_res, description=output_controls["description"])
            model_dict["output_path"] = "%s/result_%s" % (os.getcwd(), model_dict["description"])
            model_dict["resolution"] = copy.deepcopy(resolution)

        else:
            # process run thermal, update xml, and preserve thermal
            model_dict["run_thermal_equilibration"] = xmlbool(output_controls["run_thermal_equilibration_phase"])
            model_dict["update_xml_information"] = xmlbool(output_controls["update_xml_information"])

            model_dict["thermal_description"] = "{text_res}_{description}".format(text_res=text_res, description=output_controls["description"])
            model_dict["thermal_output_path"] = "%s/initial-condition_%s" % (os.getcwd(), model_dict["thermal_description"])

            if model_dict["run_thermal_equilibration"] is True:
                model_dict["input_xmls"] += " {output_path}/xmls/lmrThermalEquilibration.xml"

                # If we're running a thermal model, use the thermal resolution.
                model_dict["resolution"] = copy.deepcopy(resolution)
                model_dict["output_path"] = copy.deepcopy(model_dict["thermal_output_path"])
                if model_dict["dims"] == 2:
                    model_dict["resolution"]["z"] = 0  # Just to make sure

    output_controls = raw_dict["Output_Controls"]
    process_output_controls(output_controls, model_dict, command_dict)
    # </Output_Controls>


    # <Thermal_Equilibration>
    thermal_equilib = raw_dict["Thermal_Equilibration"]
    process_output_controls(thermal_equilib, model_dict, command_dict, thermal=True)    
    
    # </Thermal_Equilibration>

    # Thermal EQ or not, we need to know where to look for the initial condition files:
    model_dict["initial_condition_desc"] = raw_dict["Thermal_Equilibration"]["output_controls"]["description"]

    # <Restarting_Controls>
    restarting = raw_dict["Restarting_Controls"]
    model_dict["restarting"] = xmlbool(restarting["restart"])
    if model_dict["restarting"] is True:
        model_dict["restart_timestep"] = int(restarting["restart_from_step"])
        command_dict["restart"] = "--restartTimestep={restart_timestep}"
    # </Restarting_Controls>

    # <Underworld_Execution>
    uw_exec = raw_dict["Underworld_Execution"]
    model_dict["uwbinary"] = uw_exec["Underworld_binary"]
    
    if xmlbool(uw_exec["supercomputer_mpi_format"]) is False:
        model_dict["cpus"] = uw_exec["CPUs"]
        command_dict["cpus"] = "mpirun -np {cpus}"
    # </Underworld_Execution>

    # <Model_Precision>
    precision = raw_dict["Model_Precision"]
    for solver in precision.keys():
        prefix = solver.split("_")[0]
        model_dict[solver] = {"tolerance":    float(precision[solver]["tolerance"]),
                              "min_iterations": int(precision[solver]["min_iterations"]),
                              "max_iterations": int(precision[solver]["max_iterations"])}
        if model_dict["run_thermal_equilibration"] is True and prefix == "nonLinear":
            model_dict[solver]["max_iterations"] = 1   # So UW doesn't try to nonLinearly solve pure diffusion

        command_dict[solver] = "--{solver}Tolerance={tolerance} \
                                --{solver}MinIterations={min_iterations} \
                                --{solver}MaxIterations={max_iterations}".format(solver=prefix,
                                                                                 tolerance=model_dict[solver]["tolerance"],
                                                                                 min_iterations=model_dict[solver]["min_iterations"],
                                                                                 max_iterations=model_dict[solver]["max_iterations"])
    # </Model_Precision>

    return model_dict, command_dict


def prepare_job(model_dict, command_dict):

    if model_dict["dims"] == 2 or model_dict["run_thermal_equilibration"] is True:
        solvers = ["-Uzawa_velSolver_pc_factor_mat_solver_package mumps",
                   "-mat_mumps_icntl_14 200",
                   "-Uzawa_velSolver_ksp_type preonly",
                   "-Uzawa_velSolver_pc_type lu"]

    else:
        def multigrid_test(number, count=1):
            if number % 2 == 0:
                return multigrid_test(number / 2, count + 1)
            else:
                return count

        model_dict["mg_levels"] = min(multigrid_test(model_dict["resolution"]["x"]),
                                      multigrid_test(model_dict["resolution"]["y"]),
                                      multigrid_test(model_dict["resolution"]["z"]))

        solvers = ["--mgLevels=4",
                   "-ksp_type fgmres",
                   "-mg_levels_pc_type bjacobi",
                   "-mg_levels_ksp_type gmres",
                   "-mg_levels_ksp_max_it 3",
                   "-mg_coarse_pc_factor_mat_solver_package superlu_dist",
                   "-mg_coarse_pc_type lu",
                   "-log_summary",
                   "-options_left"]

        solvers = ["--mgLevels=4",
                   "-pc_type fieldsplit",
                   "-pc_fieldsplit_type multiplicative",
                   "-fieldsplit_0_pc_type hypre",
                   "-fieldsplit_0_ksp_type preonly",
                   "-fieldsplit_1_pc_type jacobi",
                   "-fieldsplit_1_ksp_type preonly",
                   "-log_summary",
                   "-options_left"]
                   
        solvers = ["-pc_mg_type full -ksp_type richardson -mg_levels_pc_type bjacobi",
                  "-mg_levels_ksp_type gmres -mg_levels_ksp_max_it 3",
                  "-mg_coarse_pc_factor_mat_solver_package superlu_dist -mg_coarse_pc_type lu",
                  "-pc_mg_galerkin -pc_mg_levels 5 -pc_type mg",
                  "-log_summary  -pc_mg_log -ksp_monitor_true_residual -options_left -ksp_view",
                  "-ksp_max_it 30",
                  "-options_left"]

        model_dict["input_xmls"] += " {output_path}/xmls/lmrSolvers.xml"

    command_dict["solver"] = " ".join(solvers)

    if model_dict["restarting"] is False:
        # Make the output folders ready for UW.
        output_dir = model_dict["output_path"]
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        xmls_dir = os.path.join(output_dir, "xmls/")
        if not os.path.isdir(xmls_dir):
            os.mkdir(xmls_dir)

        for files in os.listdir("./"):
            if files.endswith(".xml"):
                shutil.copy(files, xmls_dir)

    model_dict["input_xmls"] = model_dict["input_xmls"].format(output_path=model_dict["output_path"])
    return model_dict, command_dict


def run_model(model_dict, command_dict):

    first = command_dict["cpus"]
    del(command_dict["cpus"])

    second = command_dict["uwbinary"]
    del(command_dict["uwbinary"])

    third = command_dict["input_xmls"]
    del(command_dict["input_xmls"])

    # Some commmands NEED to come first (mpirun, for example)
    prioritised = " ".join((first, second, third))

    remainder = " ".join(command_dict.values())

    together = " ".join((prioritised, remainder))

    command = together.format(**model_dict).split(" ")

    try:
        if model_dict["write_to_log"]:
            with open(model_dict["logfile"], "w") as logfile:
                model_run = subprocess.Popen(command, shell=False, stdout=logfile, stderr=subprocess.STDOUT)
        else:
            model_run = subprocess.Popen(command, shell=False)

        model_run.wait()

        if model_run.returncode != 0:
            sys.exit("\n\nUnderworld did not exit nicely - have a look at its output to try and determine the problem.")
    except KeyboardInterrupt:
        model_run.terminate()
        if model_dict["run_thermal_equilibration"] is True:
            print "\n### Warning! ###\nUnderworld thermal equilibration stopped - will interpolate with the last timestep to be outputted."
        else:
            sys.exit("\nYou have cancelled the job - all instances of Underworld have been killed.")


def find_last_thermal_timestep(model_dict):
    thermal_results_dir = "initial-condition_{therm_resolution[x]}x{therm_resolution[y]}x{therm_resolution[z]}_{initial_condition_desc}".format(**model_dict)
    # Look for temp files, which are in the format of: TemperatureField.00000.h5

    print "ThermDir: %s" % thermal_results_dir

    try:
        last_ts = max([int(f.split('/')[-1].split('.')[1]) for f in glob.glob("%s/TemperatureField*" % thermal_results_dir)])
        print last_ts, "\n\n\n"
    except:
        if not os.path.isdir(thermal_results_dir):
            sys.exit("The initial condition folder '%s' does not exist. You must run the thermal equilibration phase \
                        first." % thermal_results_dir)
        else:
            sys.exit("Unable to find any files starting with 'TemperatureField.<some number>.h5' in the folder '%s'.\
                         You may need to re-run the thermal equilibration phase, or run it for longer." % thermal_results_dir)
    return last_ts


def modify_initialcondition_xml(last_ts, model_dict):

    print "\n\n\nLAST TS: %d\n\n\n\n" % last_ts

    prefix = "initial-condition_{resolution[x]}x{resolution[y]}x{resolution[z]}_{initial_condition_desc}".format(**model_dict)
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
        sys.exit("Problem opening lmrInitials.xml to update the HDF5 initial condition. The computer reported:\n\
                    %s" % err)


def main():
    # Basic CLI argument parsing - if someone says python lmrRunModel.py <somefilename>, 
    # it will send that file through to the XML parser. If no argument is given (or too 
    # many), it will just look for lmrStart.xml
    if len(sys.argv) > 1 and len(sys.argv) <= 2:
        raw_dict = load_xml(str(sys.argv[1]))        
    else:
        raw_dict = load_xml()

    model_dict, command_dict = process_xml(raw_dict)

    if model_dict["write_to_log"] is True:
        log_file = open(model_dict["logfile"], "a")
        sys.stdout = log_file

    model_dict, command_dict = prepare_job(model_dict, command_dict)

    if model_dict["run_thermal_equilibration"] is False and \
       model_dict["update_xml_information"] is True and     \
       model_dict["restarting"] is False:
        last_ts = find_last_thermal_timestep(model_dict)
        modify_initialcondition_xml(last_ts, model_dict)

    run_model(model_dict, command_dict)

    if model_dict["run_thermal_equilibration"] is True:
        last_ts = find_last_thermal_timestep(model_dict)
        if model_dict["preserve_thermal_equilibration_checkpoints"] is False:
            filelist = [f for f in os.listdir(model_dict["output_path"]) if str(last_ts) not in f and "xmls" not in f]
            for f in filelist:
                os.remove("%s/%s" % (model_dict["output_path"], f))

    if model_dict["write_to_log"] is True:
        log_file.close()


if __name__ == '__main__':
    main()
