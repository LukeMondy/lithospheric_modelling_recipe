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


from __future__ import division
import sys, textwrap
from lxml import etree as ElementTree
from xml.parsers.expat import  ErrorString

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
    model_dict["resolution"] = {dim: int(raw_dict["Model_Resolution"][dim]) for dim in raw_dict["Model_Resolution"].keys()}
    command_dict["resolution"] = "--elementResI={x} --elemntResJ={y} --elementResK={z}"

    model_dict["dims"] = 2 if model_dict["resolution"]["z"] <= 0 else 3
    command_dict["dims"] = "--dim={dims}"
    # </Model_Resolution>

    # <Output_Controls>
    def process_output_controls(output_controls, model_dict, command_dict, thermal=False):
        text_res = "x".join(map(str, model_dict["resolution"].values()))
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
    model_dict["input_xmls"] = ["lmrMain.xml"]
    command_dict["input_xmls"] = "{input_xmls}"

    model_dict["logfile"] = "log_" + model_dict["output_path"]
    # </Output_Controls>


    # <Thermal_Equilibration>
    thermal_equilib = raw_dict["Thermal_Equilibration"]

    model_dict["run_thermal_equilibration"] = xmlbool(thermal_equilib["run_thermal_equilibration_phase"])
    if model_dict["run_thermal_equilibration"]:
        model_dict["update_xml_information"] = xmlbool(thermal_equilib["update_xml_information"])
        model_dict["preserve_thermal_equilibration_checkpoints"] = xmlbool(thermal_equilib["preserve_thermal_equilibration_checkpoints"])

        output_controls = thermal_equilib["output_controls"]
        process_output_controls(output_controls, model_dict, command_dict, thermal=True)

        model_dict["output_path"] = "initial-condition_" + "_".join(model_dict["description"].values())
        model_dict["input_xmls"] = ["lmrMain.xml", "lmrThermalEquilibration.xml"]
        model_dict["logfile"] = "log_" + model_dict["output_path"]
    # </Thermal_Equilibration>

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
    model_dict["cpus"]     = uw_exec["CPUs"]
    command_dict["cpus"] = "mpirun -np {cpus}"
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




    return command_dict


def run_model(command_dict):
    # === To Do ====
    # - Make or check the ouptut directory exists
    # - Remember, command_dict["write_to_log"] may need to go at the end.
    # - Maybe check if 2 or 3 dim when writing the --element stuff
    pass


def main():
    raw_dict = load_xml()

    model_dict, command_dict = process_xml(raw_dict)

    command_dict = prepare_job(model_dict, command_dict)

    print "Commands!"
    print "\n".join(map(str, command_dict.values()))
    print "\nModel_dict\n-",
    print "\n- ".join(map(str, model_dict.items()))

    run_model(command_dict)



if __name__ == '__main__':
    main()


