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
The Lithospheric Modelling Recipe (or LMR) is an Underworld input file, designed to make it easy for geologists and numerical modellers to setup and run robust and reproducible geodynamic models of lithospheric scale processes.

ADD MORE!

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


This workflow essentially preserves the original files, so changes you may implement in one model are not inadvertently copied across to other models. It also means it is very easy to get updates as the lmr is improved and optimised.

Section 3. The Wiki
-------------------------
Please visit the wiki for information on a much more indepth look into the LMR, what some of the components do, some additional examples that can be implemented, and guides on good modelling practices and methods. The wiki can be found `here <https://bitbucket.org/lmondy/lithosphericmodellingrecipe/wiki>`_
