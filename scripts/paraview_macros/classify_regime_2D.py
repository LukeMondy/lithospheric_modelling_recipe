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
sigma3 = data.PointData["EigVec_2"]

dirs = []
mags = []

a = np.array([0, 1])

# Get the angle from horizontal
s1p = np.degrees(np.arccos(np.einsum('ij,j->i', np.absolute(sigma1), a  )))
s3p = np.degrees(np.arccos(np.einsum('ij,j->i', np.absolute(sigma3), a  )))

# Get the plunge
s1p = 90 - s1p
s3p = 90 - s3p

# Setup storage for results
dirs = np.empty_like(s1p)
mags = np.empty_like(s1p)
dirs[::] = np.NAN
mags[::] = np.NAN

# Select the regions in extension and compression
extension_regime = (60 < s1p) & (s1p <=90)
compression_regime = (60 < s3p) & (s3p <=90)

dirs[extension_regime] = -1  # -1 means extension
mags[extension_regime] = 1 - ((90 - s1p[extension_regime])/30)
dirs[compression_regime] = 1 # 1 means extension
mags[compression_regime] = 1 - ((90 - s3p[compression_regime])/30)

output.PointData.append(dirs, "SigDir")
output.PointData.append(mags, "Mags")
"""
SetActiveSource(ProgrammableFilter1)

DataRepresentation = Show()

Render()
