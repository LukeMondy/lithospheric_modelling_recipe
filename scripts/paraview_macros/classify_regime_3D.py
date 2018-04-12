try:
    paraview.simple
except:
    from paraview.simple import *

XDMF_temporalFields_xmf = GetActiveSource()

ProgrammableFilter1 = ProgrammableFilter()

ProgrammableFilter1.RequestUpdateExtentScript = ''
ProgrammableFilter1.PythonPath = ''
ProgrammableFilter1.RequestInformationScript = ''

ProgrammableFilter1.Script = """
import numpy as np

data = inputs[0]

sigma1 = data.PointData["EigVec_1"]
sigma2 = data.PointData["EigVec_2"]
sigma3 = data.PointData["EigVec_3"]

dirs = []
mags = []

a = np.array([0, 0, 1])

for s1, s2, s3 in zip(sigma1, sigma2, sigma3):
    # Get the angle from horizontal
    s1p = np.degrees(np.arccos(np.dot(np.absolute(s1), a)))
    s2p = np.degrees(np.arccos(np.dot(np.absolute(s2), a)))
    s3p = np.degrees(np.arccos(np.dot(np.absolute(s3), a)))
   
    # Get the plunge
    s1p = 90 - s1p
    s2p = 90 - s2p
    s3p = 90 - s3p
    
    regime = np.NAN
    mag = np.NAN
    
    if 60 < s1p <= 90:
        regime = 0 # "E"
        mag = 1 - ((90 - s1p)/30)
    if 60 < s2p <= 90:
        regime = 1 # "SS"
        mag = 1 - ((90 - s2p)/30)
    if 60 < s3p <= 90:
        regime = 2 # "C"
        mag = 1 - ((90 - s3p)/30)
    dirs.append(regime)
    try:
        mags.append(mag)
    except:
        mags.append(np.NAN)

npdirs = np.array(dirs)
npmags = np.array(mags)
output.PointData.append(npdirs, "SigDir")
output.PointData.append(npmags, "Mags")
"""
SetActiveSource(ProgrammableFilter1)

DataRepresentation = Show()

Render()