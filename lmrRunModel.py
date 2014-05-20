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
    model_dict = {"input_xmls":               "{output_path}/xmls/lmrMain.xml",
                  "model_resolution":         {},
                  "thermal_model_resolution": {}, }

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
    output_controls = raw_dict["Output_Controls"]

    model_dict["description"] = output_controls["description"]

    for dim in output_controls["model_resolution"].keys():
        model_dict["model_resolution"][dim] = int(output_controls["model_resolution"][dim])

    experiment_duration_options = output_controls["experiment_duration_options"]
    model_dict["max_timesteps"] = int(experiment_duration_options["maximum_timesteps"])
    model_dict["max_time"] = float(experiment_duration_options["maximum_time_in_years"])

    checkpoint_frequency_options = output_controls["checkpoint_frequency_options"]
    model_dict["checkpoint_every_x_years"] = float(checkpoint_frequency_options["every_x_years"])
    model_dict["checkpoint_every_x_timesteps"] = int(checkpoint_frequency_options["every_x_timesteps"])

    model_dict["output_pictures"] = xmlbool(output_controls["output_pictures"])
    model_dict["write_log_file"] = xmlbool(output_controls["write_log_file"])
    # </Output_Controls>


    # <Thermal_Equilibration>
    therm_equil = raw_dict["Thermal_Equilibration"]

    model_dict["run_thermal_equilibration_phase"] = xmlbool(therm_equil["run_thermal_equilibration_phase"])
    model_dict["update_xml_information"] = xmlbool(therm_equil["update_xml_information"])
    model_dict["preserve_thermal_checkpoints"] = xmlbool(therm_equil["preserve_thermal_equilibration_checkpoints"])

    thermal_output_controls = therm_equil["output_controls"]

    model_dict["thermal_description"] = thermal_output_controls["description"]

    for dim in thermal_output_controls["thermal_model_resolution"].keys():
        model_dict["thermal_model_resolution"][dim] = int(thermal_output_controls["thermal_model_resolution"][dim])

    experiment_duration_options = thermal_output_controls["experiment_duration_options"]
    model_dict["thermal_max_timesteps"] = int(experiment_duration_options["maximum_timesteps"])
    model_dict["thermal_max_time"] = float(experiment_duration_options["maximum_time_in_years"])

    checkpoint_frequency_options = thermal_output_controls["checkpoint_frequency_options"]
    model_dict["thermal_checkpoint_every_x_years"] = float(checkpoint_frequency_options["every_x_years"])
    model_dict["thermal_checkpoint_every_x_timesteps"] = int(checkpoint_frequency_options["every_x_timesteps"])
    # </Thermal_Equilibration>


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
        if model_dict["run_thermal_equilibration_phase"] is True and prefix == "nonLinear":
            model_dict[solver]["max_iterations"] = 1   # So UW doesn't try to nonLinearly solve pure diffusion

        command_dict[solver] = "--{solver}Tolerance={tolerance} \
                                --{solver}MinIterations={min_iterations} \
                                --{solver}MaxIterations={max_iterations}"\
                                .format(solver=prefix,
                                        tolerance=model_dict[solver]["tolerance"],
                                        min_iterations=model_dict[solver]["min_iterations"],
                                        max_iterations=model_dict[solver]["max_iterations"])
    # </Model_Precision>

    return model_dict, command_dict


def prepare_job(model_dict, command_dict):
    # Prepare resolutions, and thermal equil or not
    if model_dict["model_resolution"]["z"] <= 0:
        model_dict["dims"] = 2
        model_dict["thermal_model_resolution"]["z"] = 0  # Just to be sure.
    else:
        model_dict["dims"] = 3

    if model_dict["run_thermal_equilibration_phase"] is True:
        model_dict["resolution"] = copy.deepcopy(model_dict["thermal_model_resolution"])

        model_dict["input_xmls"] += " {output_path}/xmls/lmrThermalEquilibration.xml"
        output_prefix = "initial-condition"
    else:
        model_dict["resolution"] = copy.deepcopy(model_dict["thermal_model_resolution"])
        output_prefix = "result"

    text_res = "x".join(map(str, (model_dict["resolution"]["x"],
                                  model_dict["resolution"]["y"],
                                  model_dict["resolution"]["z"])))
    model_dict["nice_description"] = "_".join([text_res, model_dict["description"]])
    model_dict["output_path"] = "%s/%s" % (os.getcwd(), "_".join([output_prefix, model_dict["nice_description"]]))
    model_dict["logfile"] = "log_%s.txt" % model_dict["output_path"]

    # Select solvers
    if model_dict["dims"] == 2 or model_dict["run_thermal_equilibration"] is True:
        solvers = ["-Uzawa_velSolver_pc_factor_mat_solver_package mumps",
                   "-mat_mumps_icntl_14 200",
                   "-Uzawa_velSolver_ksp_type preonly",
                   "-Uzawa_velSolver_pc_type lu",
                   "-log_summary",
                   "-options_left"]
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

    # Prepare file system for UW run.
    output_dir = model_dict["output_path"]
    xmls_dir = os.path.join(output_dir, "xmls/")  # Standard place

    # We should always check to see if the results folder is even there
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    if model_dict["restarting"] is True:
        # When we restart, we need to preserve the original XMLs stored in result/xmls.
        # To do so, find the last xmls folder, and increment the number.
        xml_folders = sorted([folder for folder in glob.glob("%s/xmls*" % output_dir)
                             if os.path.isdir(os.path.join(output_dir, folder))])
        if len(xml_folders) > 1:
            last_restart_num = int(xml_folders[-1].split("_")[-1])
            xmls_dir = os.path.join(output_dir, "xmls_restart_%d" % (last_restart_num + 1))
        elif len(xml_folders) == 1:
            xmls_dir = os.path.join(output_dir, "xmls_restart_1")
        # There is no 'else' - if no xmls folder is found, it will just make one now.

    if not os.path.isdir(xmls_dir):
        os.mkdir(xmls_dir)
    for files in os.listdir("./"):
        if files.endswith(".xml"):
            shutil.copy(files, xmls_dir)

    model_dict["input_xmls"] = model_dict["input_xmls"].format(output_path=model_dict["output_path"])

    # Need to modify the XML in the result/xmls/folder, so the main folder is pristine.
    if model_dict["run_thermal_equilibration_phase"] is False and model_dict["update_xml_information"] is True:
        therm_text_res = "x".join(map(str, (model_dict["thermal_model_resolution"]["x"],
                                            model_dict["thermal_model_resolution"]["y"],
                                            model_dict["thermal_model_resolution"]["z"])))
        model_dict["thermal_output_path"] = "initial-condition_{text_res}_{thermal_description}".format(text_res=therm_text_res, thermal_description=model_dict["thermal_description"])
        last_ts = find_last_timestep(model_dict["thermal_output_path"])
        modify_initialcondition_xml(last_ts, xmls_dir)

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
        if model_dict["write_log_file"]:
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


def find_last_timestep(path):
    try:
        # We can use Mesh files because every model will have it.
        last_ts = max([int(f.split('/')[-1].split('.')[1]) for f in glob.glob("%s/Mesh.*.h5" % path)])
    except:
        if not os.path.isdir(path):
            sys.exit("The folder '%s' does not exist. The LMR is either trying to find an initial condition, or restarting." % path)
        else:
            sys.exit("Unable to find any files starting with 'Mesh.*.h5' in the folder '%s'." +
                     "You may need to re-run the thermal equilibration phase, or run it for longer." % thermal_results_dir)
    return last_ts


def modify_initialcondition_xml(last_ts, xml_path):
    new_temp_file = "%s/TemperatureField.%05d.h5" % (xml_path, last_ts)
    new_mesh_file = "%s/Mesh.linearMesh.%05d.h5" % (xml_path, last_ts)

    try:
        for line in fileinput.input("{xml_path}/lmrInitials.xml".format(xml_path=xml_path), inplace=True):
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

    # STEP 1
    model_dict, command_dict = process_xml(raw_dict)

    if model_dict["write_log_file"] is True:
        log_file = open(model_dict["logfile"], "a")
        sys.stdout = log_file

    # STEP 2
    model_dict, command_dict = prepare_job(model_dict, command_dict)

    # STEP 3
    # run_model(model_dict, command_dict)

    if model_dict["run_thermal_equilibration_phase"] is True:
        last_ts = find_last_timestep(model_dict["thermal_output_path"])
        if model_dict["preserve_thermal_equilibration_checkpoints"] is False:
            filelist = [f for f in os.listdir(model_dict["output_path"]) if str(last_ts) not in f and "xmls" not in f]
            for f in filelist:
                os.remove("%s/%s" % (model_dict["output_path"], f))

    if model_dict["write_log_file"] is True:
        log_file.close()


if __name__ == '__main__':
    main()
