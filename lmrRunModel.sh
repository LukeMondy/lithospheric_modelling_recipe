#!/bin/bash

FULLDIR=`pwd`

# === Model resolution ======================================
xres="208"
yres="80"
zres="0"    # For 3D, set this to be more than 0.




# === Data output ===========================================
job_description="reference-solution"
max_timesteps="-1"   # Use a large number for normal runs, use -1 for checking material geometries.
max_time="5e6"           # Model will stop after 5 million years
use_log_file=false        # If true, command-line output goes to $job_description.log

# Underworld will output a checkpoint either after x many years, or after x many checkpoints.
# It will choose whichever comes first, so make the one you don't want very large.
checkpoint_after_x_years="50000"
checkpoint_after_x_timesteps="1000000"

print_pictures_during_modelrun=true



# === Restarting ============================================
restarting=false            # Set to be true to enable restart functionality.
restart_timestep="26"     # Set to be the checkpoint number to restart from.




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
run_thermal_equilibration=false                         # After running once, set to false
path_to_thermal_initial_condition="${FULLDIR}/initial-condition"    # This must always be set.

thermal_equilibration_max_time="1000e6"                 # - Run thermal equilibration for 1000 myr
thermal_equilibration_checkpoint_after_x_years="10e6"   # - Checkpoint every 10 myr when doing thermal equilibration
thermal_equilibration_xres="2"                          # - Using a lower resolution when doing thermal equilibration will make it run significantly faster.
thermal_equilibration_yres="40"                         #   The lower resolution, the more jagged the resulting geotherm. If your model is laterally homogeneous,
thermal_equilibration_zres="2"                          #   then x and z can be very low (e.g., 2).
thermal_equilibration_preserve_checkpoints=false        # - When false, all but the last checkpoint of thermal equilibration will be preserved.
automatically_update_lmrInitials_xml=true               # - lmrInitials.xml has some placeholder text for where the initial condition results need to be specified.
                                                        #   Setting this to be true means it will be automatically set to the correct place.



# === Parallelism ===========================================
cpus="2"





# === Underworld binary file ================================
underworld="/home/litho/Programs/uw-src/build/bin/Underworld"   # Point this to your Underworld installation.






# === Messy details (no need to modify) =====================
dims="2"
text_res="${xres}x${yres}"
if [[ "$zres" -gt "0" ]] ; then
    dims="3"
    text_res="${text_res}x${zres}"
fi
job_description="${text_res}_${job_description}"
path_to_thermal_initial_condition="${path_to_thermal_initial_condition}_${job_description}"

if $run_thermal_equilibration ; then
    # Running thermal equilibration
    inputfile="${path_to_thermal_initial_condition}/xmls/lmrMain.xml ${path_to_thermal_initial_condition}/xmls/lmrThermalEquilibration.xml"
    OUTPUTDIR="${path_to_thermal_initial_condition}"
    logfile="${FULLDIR}/log-${job_description}-thermalEquilibration.log"
    
    resolution="--dim=${dims} --elementResI=${thermal_equilibration_xres} --elementResJ=${thermal_equilibration_yres} --elementResK=${thermal_equilibration_zres}"
    nonlin_flags="--nonLinearTolerance=${nonlinear_tolerance} --nonLinearMinIterations=${nonlinear_minIterations} --nonLinearMaxIterations=1"
    checkpoint_flags="--checkpointAtTimeInc=${thermal_equilibration_checkpoint_after_x_years} --dumpEvery=250"
    other_flags="--end=${thermal_equilibration_max_time} --outputPath=${OUTPUTDIR} --maxTimeSteps=${max_timesteps}"
else
    # Running actual model
    inputfile="${FULLDIR}/result-${job_description}/xmls/lmrMain.xml"
    OUTPUTDIR="${FULLDIR}/result-${job_description}"
    logfile="${FULLDIR}/log-${job_description}.log"
    
    resolution="--dim=${dims} --elementResI=${xres} --elementResJ=${yres} --elementResK=${zres}"
    nonlin_flags="--nonLinearTolerance=${nonlinear_tolerance} --nonLinearMinIterations=${nonlinear_minIterations} --nonLinearMaxIterations=${nonlinear_maxIterations}"
    other_flags="--end=${max_time} --outputPath=${OUTPUTDIR} --maxTimeSteps=${max_timesteps}"

    checkpoint_flags="--checkpointAtTimeInc=${checkpoint_after_x_years} --dumpEvery=1 --checkpointEvery=${checkpoint_after_x_timesteps}"
fi

linear_flags="--linearTolerance=${linear_tolerance} --linearMinIterations=${linear_minIterations} --linearMaxIterations=${linear_maxIterations}"
mumps_flags="-Uzawa_velSolver_pc_factor_mat_solver_package mumps -mat_mumps_icntl_14 200 -Uzawa_velSolver_ksp_type preonly -Uzawa_velSolver_pc_type lu"
debug_mumps="-ksp_converged_reason -ksp_monitor_true_residual -Uzawa_velSolver_ksp_view"

function mglevel_test {
    # Test to see how many times the input number can 
    # be divided by two while remaining an integer.
    n=$1; count=0; rem=0
    until [ "$rem" -ne 0 ] ; do let "rem = $n % 2"; let "n /= 2"; let "count += 1"; done
    echo $count
}

if [[ "${dims}" -eq "2" ]] ; then
    solver_flags="${mumps_flags}"
else
    mg_levelx=$( mglevel_test ${xres} )
    mg_levely=$( mglevel_test ${yres} )
    mg_levelz=$( mglevel_test ${zres} )

    mg_level=$mg_levelx
    # Find the smallest mg level
    if [[ "$mg_levely" -lt "$mg_level" ]] ; then
        mg_level=$mg_levely    
    fi
    if [[ "$mg_levelz" -lt "$mg_level" ]] ; then
        mg_level=$mg_levelz 
    fi

    multigrid_flags="--mgLevels=${mg_level} -A11_ksp_type fgmres -mg_levels_pc_type sor -A11_pc_mg_smoothup 4 -A11_pc_mg_smoothdown 4 -mg_levels_ksp_type minres -mg_levels_ksp_max_it 3 -mg_levels_pc_type sor -mg_levels_ksp_convergence_test skip -mg_coarse_pc_factor_mat_solver_package superlu_dist -mg_accelerating_smoothing_view true -mg_smooths_max 100 -mg_smooths_to_start 1 -mg_smoothing_increment 1 -mg_target_cycles_10fold_reduction 1"

    solver_flags="${multigrid_flags}"
    if ! $run_thermal_equilibration ; then
        # If the model is actually running, ensure it has the solvers it needs
        inputfile="${inputfile} ${FULLDIR}/result-${job_description}/xmls/lmrSolvers.xml"
    fi
fi

glucifer_flags=""
if ! $print_pictures_during_modelrun ; then
    glucifer_flags="--components.window.Type=DummyComponent"
fi


uw_flags="$resolution $linear_flags $nonlin_flags $other_flags $checkpoint_flags $solver_flags $glucifer_flags"

if $restarting ; then
    uw_flags="--restartTimestep=${restart_timestep} ${uw_flags}"
    echo ""
    echo "======================================================================"
    echo "=== Restarting job \"result-${job_description}\" at timestep ${restart_timestep}"
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
		echo "==== Restarting on a single CPU to interpolate to ${text_res}"
		echo "     Restart timestep: $restart_timestep"
		sleep 5
		resolution="--dim=${dims} --elementResI=${xres} --elementResJ=${yres} --elementResK=${zres}"
		checkpoint_flags="--dumpEvery=1 --checkpointEvery=1"
		other_flags="--end=${thermal_equilibration_max_time} --outputPath=${path_to_thermal_initial_condition} --maxTimeSteps=1"
		uw_flags="--restartTimestep=${restart_timestep} --interpolateRestart=1 $resolution $linear_flags $nonlin_flags $other_flags $checkpoint_flags $solver_flags $glucifer_flags"
		if $use_log_file ; then
		    $underworld $uw_flags $inputfile &>> $logfile
		else
		    $underworld $uw_flags $inputfile
		fi
		
		if ! $thermal_equilibration_preserve_checkpoints ; then
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






