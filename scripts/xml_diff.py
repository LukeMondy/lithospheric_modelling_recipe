"""
==========
 XML diff
==========

:Authors:
    Mark Williams
    Luke Mondy

A surprisingly difficult tool to find (in open-source anyway)!

Prints out the diffs between two Underworld flattened XMLs.

Run by:
python xml_diff.py <xml_file_1> <xml_file_2>

When you do this, it will print out a list of differences, generally with
some context.

For example:
::
    ['*** ',
     '--- ',
     '***************',
     '*** 21,28 ****',
     "   OrderedDict([('Type', 'StgFEM_PeakMemory'",
     "   ('Context', 'context')]",
     "   OrderedDict([('Type', 'Underworld_HDF5ConditionFunction'",
     "!  ('FeVariableHDF5Filename', '/mnt/landscapes/UWtests/lmrMeshAdapter/initial-condition_4x52x0_laterally_homog/TemperatureField.04505.h5'",
     "!  ('MeshHDF5Filename', '/mnt/landscapes/UWtests/lmrMeshAdapter/initial-condition_4x52x0_laterally_homog/Mesh.linearMesh.00000.h5'",
     "   ('TargetFeVariable', 'TemperatureField'",
     "   ('Partitioned', False)]",
     "   OrderedDict([('rhoZeroMaterial', 'mantle'",
     '--- 21,28 ----',
     "   OrderedDict([('Type', 'StgFEM_PeakMemory'",
     "   ('Context', 'context')]",
     "   OrderedDict([('Type', 'Underworld_HDF5ConditionFunction'",
     "!  ('FeVariableHDF5Filename', '/mnt/landscapes/UWtests/lmrMeshAdapter_v2/initial-condition_4x48x0_laterally_homog/TemperatureField.00152.h5'",
     "!  ('MeshHDF5Filename', '/mnt/landscapes/UWtests/lmrMeshAdapter_v2/initial-condition_4x48x0_laterally_homog/Mesh.linearMesh.00000.h5'",
     "   ('TargetFeVariable', 'TemperatureField'",
     "   ('Partitioned', False)]",
     "   OrderedDict([('rhoZeroMaterial', 'mantle'"]


The two lines with differences are highlighted with '!', and the surrounding
stuff is just to give some context about where in the file these changes are.
It is far from perfect, but works well enough.

Relies on numerous code snippets from the web. Unfortunately, the sources to
these have been lost. If you recognise the source of these code snippets,
please let us know, and we will reference accordingly.
"""

from xml.etree import ElementTree
from pprint import pprint
from collections import OrderedDict
import difflib
import sys
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description="Compare two flattened UW XML files.")
    parser.add_argument("xml_file_1",
                        help="The first XML file.")
    parser.add_argument("xml_file_2",
                        help="The second XML file.")
    args = parser.parse_args()

    if not os.path.isfile(args.xml_file_1):
        sys.exit("ERROR - Can't find first XML file: {}".format(args.xml_file_1))
    if not os.path.isfile(args.xml_file_2):
        sys.exit("ERROR - Can't find second XML file: {}".format(args.xml_file_2))

    tree1 = ElementTree.parse(args.xml_file_1)
    tree2 = ElementTree.parse(args.xml_file_2)
    dict1 = _elementToDict(tree1.getroot())
    dict2 = _elementToDict(tree2.getroot())
    diff = dict_diff(dict1, dict2)
    if(len(diff)):
        print "Differences:"
        for key, value in diff.items():
            first = str(value[0]).split('),')
            second = str(value[1]).split('),')
            result = list(difflib.context_diff(first, second, lineterm=""))
            pprint(result)
    else:
        print "No Differences"


def _elemGetKey(elem):
    elemtagsplit = elem.tag
    if 'name' in elem.attrib:
        return elem.attrib['name']
    else:
        return elemtagsplit


def _elementToDict(elem):
    # set key
    dicttag = elem.tag.split("}")[1]
    # get children count
    if len(elem):
        value = OrderedDict()
        for child in elem:
            # add this check to ensure we use only the valid guys
            if child.tag.split('}')[1] in ['param', 'list', 'struct']:
                childkey = _elemGetKey(child)
                valueGuy = _elementToDict(child)
                if dicttag in ['struct', 'StGermainData']:
                    # if no entry with this key, add one
                    if childkey not in value:
                            value[childkey] = valueGuy
                elif dicttag == 'list':
                    # if entry already exists,
                    try:
                        # assume it's a list, and add item to list
                        value[childkey].append(valueGuy)
                    except:
                        # if that fails, lets create a list and add item
                        value[childkey] = []
                        value[childkey].append(valueGuy)
                else:
                    print "Error.. param cannot contain sub values"
                    print childkey, valueGuy
                    sys.exit(2)
        # now, if elem is a list, ensure there's only one dict entry,
        # and then simply return the list
        if dicttag == "list":
            if len(value) == 1:
                tempval = value.items()[0][1]
                value = tempval
        # ignores multiple list tags within the 1 struct. It will ignore
        # last list tag in sample xml file
        # else:
        #     print "Error: your list contains more than one item type"
        #     sys.exit(2)

    else:
        value = _convToNativeWherePossible(elem.text)

    return value


def _convToNativeWherePossible(string):
    if string is None:
            return None
    elif string.lower() == "true":
            return True
    elif string.lower() == "false":
            return False
    else:
        try:
            return int(string)
        except ValueError:
            try:
                return float(string)
            except ValueError:
                return string


class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDictConfig(dict):
    '''
    Example usage:

    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:

    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)

    And then use xmldict for what it is... a dict.
    '''
    def __init__(self, parent_element):
        childrenNames = []
        childrenNames = [child.tag for child in parent_element.getchildren()]

        if parent_element.items():  # attributes
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if len(element):
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                # print len(element), element[0].tag, element[1].tag
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {element[0].tag: XmlListConfig(element)}
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))

                if childrenNames.count(element.tag) > 1:
                    try:
                        currentValue = self[element.tag]
                        currentValue.append(aDict)
                        self.update({element.tag: currentValue})
                    except:
                        # the first of its kind, an empty list must be created
                        self.update({element.tag: [aDict]})
                        # aDict is written in [], i.e. it will be a list

                else:
                    self.update({element.tag: aDict})
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
                self[element.tag].update({"__Content__": element.text})
            # finally, if there are no child tags and no attributes, extract
            # the text
            else:
                self.update({element.tag: element.text})


def dict_diff(first, second):
    """ Return a dict of keys that differ with another config object.  If a
        value is not found in one of the configs, it will be represented by
        KEYNOTFOUND.
        @param first:   Fist dictionary to diff.
        @param second:  Second dicationary to diff.
        @return diff:   Dict of Key => (first.val, second.val)
    """
    diff = {}
    # Check all keys in first dict
    for key in first.keys():
        if key not in second:
            diff[key] = (first[key], KEYNOTFOUND)
        elif first[key] != second[key]:
            diff[key] = (first[key], second[key])
    # Check all keys in second dict to find missing
    for key in second.keys():
        if key not in first:
            diff[key] = (KEYNOTFOUND, second[key])
    return diff

if __name__ == '__main__':
    main()
