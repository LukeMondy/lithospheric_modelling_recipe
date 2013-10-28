=========================================
=== The Lithospheric Modelling Recipe ===
============ For Underworld =============

Authors: Luke Mondy, Guillaume Duclaux, Patrice Rey, Julian, etc.

=== What is the Lithospheric Modelling Recipe? ===
The Lithospheric Modelling Recipe (or LMR) is an Underworld input file, designed to make 
it easy for geologists and numerical modellers to setup and run robust and reproducible 
geodynamic models of lithospheric scale processes.

ADD MORE!

=== Ideal workflow ===
1. Clone the repo as such:
hg clone https://username@bitbucket.org/lmondy/lithosphericmodellingrecipe lmr-src

2. In the lmr-src directory, open lmrRunJob.sh and update the 'underworld' variable to 
point to your Underworld installation.

3. Copy the lmr-src directory, calling the new folder something relevant to your problem. 
For example:
cp -R lmr-src rapid-rifting

4. Modify the lmr*.xml files in the new directory, adjusting them to represent the problem 
you are investigating.

5. Modify the lmrRunJob.sh file with the appropriate resolution and output parameters.

6. Run the job by typing (in the terminal): ./lmrRunJob.sh

This workflow essentially preserves the original lmr repo, so changes you may implement in 
one model are not inadvertently copied across to other models. It also means it is very 
easy to get updates as the lmr is improved and optimised.

