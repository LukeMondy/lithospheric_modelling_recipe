#!/usr/bin/python

"""
Written by Luke Mondy (luke.s.mondy@gmail.com)

This script reads in lmrModelParameters.xml and interprets it for the LMR.

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



import sys, textwrap

"""
======================
==== xml2dict from http://code.activestate.com/recipes/410469-xml-as-dictionary/
==== Created by Duncan McGreggor, under the PSF License.
"""
from lxml import etree as ElementTree
from xml.parsers.expat import  ErrorString

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
"======================"




input_xml = 'lmrStart.xml'
xsd_location = 'LMR.xsd'

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
raw_dict = XmlDictConfig(root)

model_dict = {}

model_dict["dims"] = 2 if int(raw_dict["Model_Resolution"]["z"]) == 0 else 3

text_res = "x".join(map(str, raw_dict["Model_Resolution"].values()))
model_dict["description"] = "%s_%s" % (text_res, raw_dict["Output_Controls"]["description"])









model_dict["uwbinary"] = raw_dict["Underworld_Execution"]["Underworld_binary"]
model_dict["CPUs"]     = raw_dict["Underworld_Execution"]["CPUs"]

rawLinearSolver = raw_dict["Model_Precision"]["linear_solver"]
linearSolver = {"tolerance":     "--linearTolerance=%s" % rawLinearSolver["tolerance"],
                "minIterations": "--linearMinIterations=%s" % rawLinearSolver["min_iterations"],
                "maxIterations": "--linearMaxIterations=%s" % rawLinearSolver["max_iterations"]}

rawnonLinearSolver = raw_dict["Model_Precision"]["nonlinear_solver"]
nonlinearSolver = {"tolerance":     "--nonLinearTolerance=%s" % rawnonLinearSolver["tolerance"],
                   "minIterations": "--nonLinearMinIterations=%s" % rawnonLinearSolver["min_iterations"],
                   "maxIterations": "--nonLinearMaxIterations=%s" % rawnonLinearSolver["max_iterations"]}



model_dict["solver_flags"]["mumps"] = "-Uzawa_velSolver_pc_factor_mat_solver_package mumps -mat_mumps_icntl_14 200 -Uzawa_velSolver_ksp_type preonly -Uzawa_velSolver_pc_type lu"




if raw_dict["Thermal_Equilibration"]["run_thermal_equilibration_phase"] == 'true':
    pass
















