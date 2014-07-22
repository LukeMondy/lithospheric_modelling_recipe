===================================
 The Lithospheric Modelling Recipe 
===================================
--------------------------------------------
 For Underworld (www.underworldproject.org)
--------------------------------------------

:Authors: - Luke Mondy (1)
          - Guillaume Duclaux (2)
          - Patrice Rey (1)
          - John Mansour (3) 
          - Julian Giordani (3)
          - Louis Moresi (3)
    
:Organization: 1. The EarthByte Group, School of Geosciences, The University of Sydney, NSW 2006, Australia. 2. Earth Sciences Centre, 11 Julius Avenue, North Ryde, NSW 2113. 3. Monash.

:Version: 1.0

.. image:: http://i.imgur.com/ZWjQKoTl.png

Section 1. What is the Lithospheric Modelling Recipe?
-----------------------------------------------------
The Lithospheric Modelling Recipe (or LMR) is a set of Underworld input files, designed to make it easy for geologists and numerical modellers to setup and run robust and reproducible geodynamic models of lithospheric scale processes.

The LMR input files are setup (by default) with a 2/3D continental rifting scenario. The model includes stress and temperature dependent rheologies, partial melting, and basic threshold-style surface processes. An example of a high resolution 3D model using (almost) these inputs files can be seen here: http://youtu.be/8TxvBO2UdKg

The LMR also comes with a pre-configured virtual machine (VM), known as the Modelling Environment, which has Underworld and its dependencies installed and ready to run.

Section 2. Ideal workflow
-------------------------
*If you are using the Modelling Environment, start at step 4.*

1. Open a terminal, and navigate to where you want to store the LMR.

2. Clone the repo. For example:
   
   ``hg clone https://username@bitbucket.org/lmondy/lithosphericmodellingrecipe lmr-src``

3. In the lmr-src directory, open lmrStart.xml and scroll down to the <Underworld_Execution> area. Update the "Underworld_binary" variable to point to your Underworld installation.

4. Make a copy of the lmr-src directory, calling the new folder something relevant to your problem. For example, if you are using the terminal:
   
   ``cp -R lmr-src rapid-rifting``

5. Modify the XML files in the new directory, adjusting them to represent the problem you are investigating. Beginners should start by just running the standard model, or by making slight changes in lmrVelocityBoundaries.xml or lmrMaterials.xml.

6. The model needs to be thermally equilibrated to achieve a steady-state geotherm. This is controlled within the <Thermal_Equilibration> block in lmrStart.xml, by turning the <run_thermal_equilibration_phase> parameter to true or false. By default, this parameter is set to true, so simply run the model by typing:
   
   ``python ./lmrRunModel.py``
   
   Ensuring your models are thermally equilibrated is almost always a good idea - it is discussed more `here <https://bitbucket.org/lmondy/lithosphericmodellingrecipe/wiki/Thermal%20Equilibration>`_.
   You can also modify some basic details of how the thermal equilibration model is run within the <Thermal_Equilibration> block, but the defaults usually suffice.

7. Once the thermal equilibration is done, open the lmrStart.xml file again, and set the <run_thermal_equilibration_phase> parameter to false. You can now run the full thermo-mechanical model by typing the same command as before:
   
   ``python ./lmrRunModel.py``

8. When the model finishes, you can visualise the model output by opening Paraview, clicking File -> Open, navigating to the output directory, double-clicking on XDMF.temporalFields.xmf, and finally clicking Apply. You can then view the different fields by using the dropdown boxes towards to the top-left of the screen.


This workflow preserves the original files, so changes you may implement in one model are not inadvertently copied across to other models. It also means it is very easy to get updates as the lmr is improved and optimised.

NOTE: The LMR requires the latest version of Underworld, and two additional toolboxes. Please see `this wiki page <https://bitbucket.org/lmondy/lithosphericmodellingrecipe/wiki/Setting%20up%20Underworld%20for%20the%20LMR>`_. for instructions on how to install Underworld for use with the LMR.

Section 3. What do I do now?
----------------------------
If you followed the workflow in section 2, you now have a model result, but very little understanding of what went into it. The LMR is made of a number of XML files which define the model behavior. It is worthwhile exploring them all, as there are useful comments within them, but beginners should focus their attention on these files:
 - **lmrVelocityBoundaries.xml** - this file defines the mechanical boundary conditions - try multiplying the left and right walls by 0.5 or by 2 to see the resulting impact of rift velocity. Change the signs of the velocities to model convergence.
 - **lmrThermalBoundaries.xml** - this file defines the thermal boundary conditions - try increasing the basal temperature to observe the effects on resulting rift structures.
 - **lmrMaterials.xml** - this files defines two main things: the layout of materials (for example, the layered upper crust), and the rheologies of those materials. The top of the file defines the material layouts, and the bottom defines their rheologies.
     - **lmrRheologyLibrary.xml** - we have built up a collection of published rheological parameters that can be used in the lmrMaterials.xml file. Have a browse, try changing some of the rheologies defined at the bottom of lmrMaterials.xml to see their impact on rift evolution.

This is only a very basic overview of how to get started with the LMR, but should provide some idea of the layout and design of both the LMR and Underworld. With further experimentation over time, both the power and limits of Underworld, the LMR, and this particular model setup should hopefully become clear.


Section 4. The Wiki
-------------------------
Please visit the wiki for information on a much more indepth look into the LMR, what some of the components do, some additional examples that can be implemented, and guides on good modelling practices and methods. The wiki can be found `here <https://bitbucket.org/lmondy/lithosphericmodellingrecipe/wiki>`_
