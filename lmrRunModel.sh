#!/bin/bash

FULLDIR=./

# === Define x and y resolution here ========================
xres="208"
yres="112"

# === Data output ===========================================
JOBDESC="litho-${xres}x${yres}-parameter_set_1"
outputFreq="1"      # How frequently should UW checkpoint?
maxTimesteps="10"   # Use a large number for normal runs, use -1 for checking material geometries.

# === Model precision =======================================
       linear_tolerance="5e-4"      # Tolerance - the lower the better, but takes longer or may fail.
    nonlinear_tolerance="5e-3"
   linear_minIterations="10"        # Min iterations ensures the model does not settle on an incorrect solution.
nonlinear_minIterations="2"
   linear_maxIterations="15000"     # Max iterations controls how long the model will attempt to converge before failing.
nonlinear_maxIterations="500"

# === Parallelism ==========================================
cpus="6"

# === Restarting ============================================
restarting=false            # Set to be true to enable restart functionality.
restart_timestep="9"     # Set to be the checkpoint number to restart from.




# ===========================================================
underworld="/home/luke/Programs/uw-be-4th_July_2013/build/bin/Underworld"   # Point this to your Underworld installtion.

inputfile="${FULLDIR}/result-$JOBDESC/xmls/lmrMain2D.xml"
OUTPUTDIR="${FULLDIR}/result-$JOBDESC"
logfile="${FULLDIR}/log-$JOBDESC.log"
linear_flags="--linearTolerance=${linear_tolerance} --linearMinIterations=${linear_minIterations} --linearMaxIterations=${linear_maxIterations}"
nonlin_flags="--nonLinearTolerance=${nonlinear_tolerance} --nonLinearMinIterations=${nonlinear_minIterations} --linearMaxIterations=${nonlinear_maxIterations}"
resolution="--elementResI=${xres} --elementResJ=${yres}"
mumps_flags="-Uzawa_velSolver_pc_factor_mat_solver_package mumps -mat_mumps_icntl_14 200 -Uzawa_velSolver_ksp_type preonly -Uzawa_velSolver_pc_type lu"
debug_mumps="-ksp_converged_reason -ksp_monitor_true_residual -Uzawa_velSolver_ksp_view"
other_flags="--outputPath=${OUTPUTDIR} --dumpEvery=${outputFreq} --checkpointEvery=${outputFreq} --airIdx=${airIdx} --maxTimeSteps=${maxTimesteps}"

uw_flags="$resolution $linear_flags $nonlin_flags $other_flags $mumps_flags"

if $restarting ; then
    uw_flags="--restartTimestep=${restart_timestep} ${uw_flags}"
    echo ""
    echo "Restarting job: ${JOBDESC}"
    echo "Are you sure? (Waiting 5 seconds, press ctrl-c to abort)"
    sleep 5;
else
    if [ ! -d $OUTPUTDIR ]; then 
        mkdir -p $OUTPUTDIR 
    fi
    if [ ! -d $OUTPUTDIR/xmls ]; then 
        mkdir $OUTPUTDIR/xmls
    fi
    cp ${FULLDIR}/*xml $OUTPUTDIR/xmls/
fi

mpirun -np $cpus $underworld $uw_flags $inputfile

