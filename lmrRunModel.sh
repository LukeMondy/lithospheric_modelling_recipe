#!/bin/bash

FULLDIR=`pwd`

# === Model resolution ======================================
xres="208"  # 2 km resolution for fast run.
yres="80"




# === Data output ===========================================
JOBDESC="litho-${xres}x${yres}-reference_solution"
max_timesteps="100000"   # Use a large number for normal runs, use -1 for checking material geometries.
max_time="5e6"           # Model will stop after 5 million years
use_log_file=false        # If true, command-line output goes to $JOBDESC.log

# Underworld will output a checkpoint either after x many years, or x many checkpoints.
# It will choose whichever comes first, so make the one you don't want very large.
checkpoint_after_x_years="50000"
checkpoint_after_x_timesteps="1000000"




# === Restarting ============================================
restarting=false            # Set to be true to enable restart functionality.
restart_timestep="1000"     # Set to be the checkpoint number to restart from.




# === Model precision =======================================
       linear_tolerance="5e-4"      # Tolerance - the lower the better, but takes longer or may fail.
    nonlinear_tolerance="5e-3"
   linear_minIterations="15"        # Min iterations ensures the model does not settle on an incorrect solution.
nonlinear_minIterations="5"
   linear_maxIterations="15000"     # Max iterations controls how long the model will attempt to converge before failing.
nonlinear_maxIterations="500"




# === Thermal equilibration =================================
#   Underworld can run a purely thermal solve very quickly. This means we can setup our model
#   with whatever radiogenic and thermal boundary conditions we want, and then let the model
#   thermally equilibrate for >1 billion years without much computational cost. It is highly
#   recommended to this at least once, and then use the resulting outputs as your model initial
#   conditions.
run_thermal_equilibration=true  # After running once, set to false
path_to_thermal_initial_condition="${FULLDIR}/initial_condition"    # This MUST be set.

thermal_equilibration_max_time="1000e6"                 # Run thermal equilibration for 1000 myr
thermal_equilibration_checkpoint_after_x_years="10e6"   # Checkpoint every 10 myr when doing thermal equilibration
thermal_equilibration_xres="2"                          # Using a lower resolution when doing thermal equilibration will make it run significantly faster.
thermal_equilibration_yres="40"                         # The lower resolution, the more jagged the resulting geotherm. If your model is laterally homogeneous, then x can be very low (e.g., 2).
preserve_thermal_equilibration_checkpoints=false        # When false, all but the last checkpoint of thermal equilibration will be preserved.
automatically_update_lmrInitials_xml=true



# === Parallelism ===========================================
cpus="6"





# === Underworld binary file ================================
underworld="/home/luke/Programs/unmodified-uw/build/bin/Underworld"   # Point this to your Underworld installtion.





# === Messy details (no need to modify) =====================
if $run_thermal_equilibration ; then
    # Running thermal equilibration
    inputfile="${path_to_thermal_initial_condition}/xmls/lmrMain2D.xml ${path_to_thermal_initial_condition}/xmls/lmrThermalEquilibration.xml"
    OUTPUTDIR="${path_to_thermal_initial_condition}"
    logfile="${FULLDIR}/log-$JOBDESC-thermalEquilibration.log"
    
    resolution="--elementResI=${thermal_equilibration_xres} --elementResJ=${thermal_equilibration_yres}"
    nonlin_flags="--nonLinearTolerance=${nonlinear_tolerance} --nonLinearMinIterations=${nonlinear_minIterations} --nonLinearMaxIterations=1"
    checkpoint_flags="--checkpointAtTimeInc=${thermal_equilibration_checkpoint_after_x_years}"
    other_flags="--end=${thermal_equilibration_max_time} --outputPath=${OUTPUTDIR} --maxTimeSteps=${max_timesteps}"
else
    # Running actual model
    inputfile="${FULLDIR}/result-$JOBDESC/xmls/lmrMain2D.xml"
    OUTPUTDIR="${FULLDIR}/result-$JOBDESC"
    logfile="${FULLDIR}/log-$JOBDESC.log"
    
    resolution="--elementResI=${xres} --elementResJ=${yres}"
    nonlin_flags="--nonLinearTolerance=${nonlinear_tolerance} --nonLinearMinIterations=${nonlinear_minIterations} --nonLinearMaxIterations=${nonlinear_maxIterations}"
    other_flags="--end=${max_time} --outputPath=${OUTPUTDIR} --maxTimeSteps=${max_timesteps}"

    checkpoint_flags="--checkpointAtTimeInc=${checkpoint_after_x_years} --dumpEvery=${checkpoint_after_x_timesteps} --checkpointEvery=${checkpoint_after_x_timesteps}"
fi

linear_flags="--linearTolerance=${linear_tolerance} --linearMinIterations=${linear_minIterations} --linearMaxIterations=${linear_maxIterations}"
mumps_flags="-Uzawa_velSolver_pc_factor_mat_solver_package mumps -mat_mumps_icntl_14 200 -Uzawa_velSolver_ksp_type preonly -Uzawa_velSolver_pc_type lu"
debug_mumps="-ksp_converged_reason -ksp_monitor_true_residual -Uzawa_velSolver_ksp_view"


uw_flags="$resolution $linear_flags $nonlin_flags $other_flags $checkpoint_flags $mumps_flags"

if $restarting ; then
    uw_flags="--restartTimestep=${restart_timestep} ${uw_flags}"
    echo ""
    echo "======================================================================"
    echo "=== Restarting job: ${JOBDESC} ==="
    echo "    Are you sure? (Waiting 5 seconds, press ctrl-c to abort)"
    sleep 5;
else
    # If we are not restarting, then make sure Underworld has an output directory
    # In that directory, create a folder of all the XMLs used to run the model.
    if [ ! -d $OUTPUTDIR ]; then 
        mkdir -p $OUTPUTDIR 
    fi
    if [ ! -d $OUTPUTDIR/xmls ]; then 
        mkdir $OUTPUTDIR/xmls
    fi
    cp ${FULLDIR}/*xml $OUTPUTDIR/xmls/
    
    # Since the thermal equilibration takes an unknown number of steps, the follow scripting
    # finds the final checkpoint, and subs in the correct values into lmrInitials.xml.
    if ! $run_thermal_equilibration && $automatically_update_lmrInitials_xml ; then 
        initial_condition_timestep=`ls ${path_to_thermal_initial_condition}/TemperatureField* | tail -n 1 | sed -r 's/.*TemperatureField.([0-9]*)\..*/\1/g'`
        initial_condition_timestep=$(echo $initial_condition_timestep | sed 's/^0*//')
        replaceTemp=`printf "${path_to_thermal_initial_condition}/TemperatureField.%05d.h5\n" "${initial_condition_timestep}"`
        perl -p -i -e "s|!!PATH_TO_TEMP_FILE!!|${replaceTemp}|g" $OUTPUTDIR/xmls/lmrInitials.xml
        replaceMesh=`printf "${path_to_thermal_initial_condition}/Mesh.linearMesh.%05d.h5\n" "${initial_condition_timestep}"`
        perl -p -i -e "s|!!PATH_TO_MESH_FILE!!|${replaceMesh}|g" $OUTPUTDIR/xmls/lmrInitials.xml
    fi
fi

if $use_log_file ; then
    echo "Directing all output to $logfile."
    mpirun -np $cpus $underworld $uw_flags $inputfile &> $logfile
else
    mpirun -np $cpus $underworld $uw_flags $inputfile
fi

if $run_thermal_equilibration ; then
    # Underworld doesn't like interpolating HDF5initial conditions when running in parallel.
    # The only safe way around this is to restart the job on 1 CPU at the resolution you want.
    # This may be slightly more time consuming, but hopefully not too bad. To actually do this
    # the script looks in the initial conditions folder, finds the last timestep and restarts
    # from there.
    restart_timestep=`ls ${path_to_thermal_initial_condition}/TemperatureField* | tail -n 1 | sed -r 's/.*TemperatureField.([0-9]*)\..*/\1/g'`
    restart_timestep=$(echo $restart_timestep | sed 's/^0*//') 
    if [[ "$restart_timestep" != '' ]] ; then
		echo ""
		echo "======================================================================"
		echo "==== Restarting on a single CPU to interpolate to ${xres}x${yres} ===="
		echo "     Restart timestep: $restart_timestep"
		sleep 10
		resolution="--elementResI=${xres} --elementResJ=${yres}"
		checkpoint_flags="--dumpEvery=1 --checkpointEvery=1"
		other_flags="--end=${thermal_equilibration_max_time} --outputPath=${path_to_thermal_initial_condition} --maxTimeSteps=1"
		uw_flags="--restartTimestep=${restart_timestep} --interpolateRestart=1 $resolution $linear_flags $nonlin_flags $other_flags $checkpoint_flags $mumps_flags"
		if $use_log_file ; then
		    $underworld $uw_flags $inputfile &>> $logfile
		else
		    $underworld $uw_flags $inputfile
		fi
		
		if ! $preserve_thermal_equilibration_checkpoints ; then
		    # Delete all but the last checkpoint.
		    echo "Cleaning up thermal equilibration checkpoints"
		    last_step=$(( $restart_timestep + 1 ))
		    find ${path_to_thermal_initial_condition} -type f -not -name "*${last_step}*" | xargs rm
		fi
	else
		echo ""
		echo "=========================================================================="
		echo "=== ERROR: lmrRunJob.sh couldn't find any thermal equilibration steps!"
		echo "           This is most likely because the thermal equilibration has either"
		echo "           only outputted the first timestep (t=0), or hasn't outputted anything"
		echo "           Some ways to try fixing this:"
		echo "               - Run the equilibration phase for longer,"
		echo "               - Reduce the equilibration timestep length,"
		echo "               - Turn off equilibration checkpoint cleanup."
		echo ""
	fi
fi






