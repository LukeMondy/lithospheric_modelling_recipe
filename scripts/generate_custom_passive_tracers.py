# # Using custom passive tracer particle layouts in Underworld
# 
# Underworld suffers from a poor algorithm for filling shapes with particles. This is a problem, since it can be useful to position passive tracers in shapes, such as spheres or walls, without a huge time penalty. 
# 
# To overcome this issue, this script allows users to define functions for particle layouts (the example given is for uniformly distributing points on a sphere). The points are then written to a h5 file, which Underworld can understand.
# 
# ## Point layout functions
# Any functions users define for points must return a numpy array of format:
# 
#     (x, y, (z), materialIndex)
# 
# The z axis is optional.
# 
# The resulting array of the above format can then be passed to the write_points_to_h5 function, which will handle the formatting automatically.
# 
# ## Using the particles in Underworld
# 
# In Underworld, you need to use a FileParticleLayout type. It only needs to take a 'filename' param. This param is the path and name of the data file you made when calling the write_points_to_h5 function - EXCEPT, it does not need the file extension. For example, "data.h5" would be simply "data".
# 
#     <struct name="particleLayout1"> 
#         <param name="Type"> FileParticleLayout </param>
#         <param name="filename"> <!-- the name of the file you made WITHOUT the .h5 extension --> </param>
#     </struct>
#     
# And Underworld will load the particles.
# 
import sys
import argparse
try:
    import h5py
    import numpy as np
except ImportError as e:
    sys.exit("ERROR - You need to have h5py and numpy. Please install the one you are lacking. The computer says:\n{0!s}".format(e))


def write_points_to_h5(points, filename):
    size, n = points.shape
    
    pos = points[:,:n-1]
    mi = points[:,-1].astype(int)
    
    try:
        f = h5py.File(filename, "w")
        f.attrs['Swarm Particle Count'] = size

        dpos = f.create_dataset("Position", (size,n-1), dtype='f')
        dmi =  f.create_dataset("MaterialIndex", (size,), dtype='i')

        dpos[...] = pos
        dmi[...] = mi
    except Exception as e:
        sys.exit("\nERROR\nComputer says:\n{0!s}\n".format(e))
    finally:
        f.close()


def make_sphere_shell(num_points, centre_x, centre_y, centre_z, radius, materialIndex, dims):
    if 1 < dims <= 3:
    
        # Make points
        x = np.random.normal(size=(num_points, dims)) 
        x /= np.linalg.norm(x, axis=1)[:, np.newaxis]

        # Scale to radius
        x *= radius

        # Position the sphere
        x[:,0] += centre_x
        x[:,1] += centre_y
        if dims == 3:
            x[:,2] += centre_z
            
        # Tack on MaterialIndex
        mi = np.zeros((num_points,1))
        mi.fill(materialIndex)
        
        x = np.hstack((x, mi))

    else:
        sys.exit("\nERROR\nUnsupported number of dimensions. 2 or 3 is OK!\n")
            
    return x

def main():

    dims = 2                    # Make 2D spheres (circles)
    num_spheres = 20            # How many spheres wanted
    points_per_sphere = 2000    # How many points should each sphere have?
    sphere_radii = 5000         # Radius

    # np.linspace makes an evenly spaced set of numbers (40 in this case) between -185000 and 185000. 
    xcentres = np.linspace(-185000, 185000, num_spheres)
    # All the spheres will have the same Y value
    ycentre = -140000

    # Initialise the storage
    allPoints = None

    # For each x location from np.linspace
    for count, xc in enumerate(xcentres):
        # make a sphere at that location
        points = make_sphere_shell(points_per_sphere, xc, ycentre, 0, sphere_radii, count, dims)
        
        # Stack all the loop outputs together
        if allPoints is None:
            allPoints = points
        else:
            allPoints = np.vstack((allPoints, points))

    filename = "2Ddata.h5"
    write_points_to_h5(allPoints, filename)

    print("Now add these structs to your lmrPassiveTracers.xml:")
    print("""
        <struct name="customParticleLayout"> 
             <param name="Type"> FileParticleLayout </param>
             <param name="filename"> {0} </param>
        </struct>

        <struct name="custom_marker_PTSwarm">
            <param name="Type"> MaterialPointsSwarm</param>
            <param name="CellLayout"> user_ElementCellLayoutTracer</param>
            <param name="ParticleLayout"> customParticleLayout </param>
            <param name="FiniteElement_Mesh"> linearMesh</param>
            <param name="FeMesh"> elementMesh </param>
            <list name="ParticleCommHandlers">
                <param> user_passiveSwarmMovementHandler </param>
            </list>
        </struct>
        <struct name="moho_marker_passiveTracerAdvect">
            <param name="Type"> SwarmAdvector </param>
            <param name="Swarm"> moho_marker_PTSwarm </param>
            <param name="TimeIntegrator"> timeIntegrator </param>
            <param name="VelocityField"> VelocityField </param>
            <param name="allowFallbackToFirstOrder"> True </param>
        </struct>
    """.format(filename))


    xmf = """<?xml version="1.0" ?>
    <Xdmf xmlns:xi="http://www.w3.org/2001/XInclude" Version="2.0">
        <Domain>
            <Grid Name="materialSwarm" GridType="Collection">
                <Time Value="0" />
                <Grid Name="spheres">
                    <Topology Type="POLYVERTEX" NodesPerElement="{numPoints}"> </Topology>
                    <Geometry Type="XYZ">
                        <DataItem Format="HDF" NumberType="Float" Precision="8" Dimensions="{numPoints} 3">{filename}:/Position</DataItem>
                    </Geometry>

                    <Attribute Type="Scalar" Center="Node" Name="MaterialIndex">
                        <DataItem Format="HDF" NumberType="Int" Dimensions="{numPoints} 1">{filename}:/MaterialIndex</DataItem>
                    </Attribute>
                </Grid>
            </Grid>
        </Domain>
    </Xdmf>
    """.format(numPoints=allPoints.shape[0], filename=filename)

    try:
        with open("3D_paraview.xmf", 'w') as f:
            f.write(xmf)
    except Exception as e:
        sys.exit("ERROR with writing 3D_paraview.xmf. Computer says:\n{0!s}".format(e))

if __name__ == "__main__":
    sys.exit(main())