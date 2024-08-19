cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(parametricDCEMRI)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/parametricDCEMRI")
set(EXTENSION_CATEGORY "Quantification")
set(EXTENSION_CONTRIBUTORS "Jose L. Ulloa (iSANDEx Ltd.), Muhammad Qadir (Austin Health)")
set(EXTENSION_DESCRIPTION "Slicer Extension to derive non-PK parametric maps from signal intensity analysis of DCE-MRI datasets")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/parametricDCEMRI.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/parametricDCEMRI/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") #["SequenceRegistration"]) #"NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(quantification)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
