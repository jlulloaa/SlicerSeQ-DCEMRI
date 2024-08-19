<h1 align="center">
  Semi-Quantitative DCE-MRI parameters estimation
  <br>
</h1>
<h2 align="center">Extension for <a href="https://slicer.org" target="_blank">3D Slicer</a></h2>

![GitHub top language](https://img.shields.io/github/languages/top/jlulloaa/SlicerSemiQuantDCEMRI)
![GitHub repo size](https://img.shields.io/github/repo-size/jlulloaa/SlicerSemiQuantDCEMRI)
![GitHub forks](https://img.shields.io/github/forks/jlulloaa/SlicerSemiQuantDCEMRI)
![GitHub Repo stars](https://img.shields.io/github/stars/jlulloaa/SlicerSemiQuantDCEMRI)
![GitHub License](https://img.shields.io/github/license/jlulloaa/SlicerSemiQuantDCEMRI)

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#key-features">Key Features</a> •
  <a href="#comparison-with-slicerftvdcemri">Comparison with Slicer FTV DCEMRI</a> •
  <a href="#installation-and-setup">Installation and Setup</a> •
  <a href="#user-guide">User Guide</a> •
  <a href="#example-of-use">Example of Use</a> •
  <a href="#acknowledgments">Acknowledgments</a> •
  <a href="#license-information">License</a> •
</p>

<img alt="Welcome Page Screenshot" src="docs/imgs/screenshot001.png"> </a>

# Overview

 A brief introduction to the \href{https://github.com/jlulloaa/parametricDCEMRI}{slicerDCEMRI} extension, its purpose, and the motivation behind its development...

Slicer Extension to derive semi-quantitative parametric maps from signal intensity analysis of DCE-MRI datasets

This extension leverages the use of [Sequences](https://slicer.readthedocs.io/en/latest/user_guide/modules/sequences.html). Hence, it can process any DCEMRI dataset that can be loaded as, or combined into, a sequence. Furthermore, if the [Sequence Registration](https://github.com/moselhy/SlicerSequenceRegistration#volume-sequence-registration-for-3d-slicer) module is installed, there is an option to register the dataset prior to the analysis. 

This module is heavily based on the [Slicer FTV DCEMRI](https://github.com/rnadkarni2/SlicerBreast_DCEMRI_FTV) extension. The algorithms are essentially the same, but we have make use of the tools already available in Slicer to segment and quantify parameters associated with the functional tumour volume. There are still improvements that can be made, but we would like to share this first version so we can capture feedback on how useful is this tool.



# Key Features

# Comparison with Slicer FTV DCEMRI

# Installation and Setup

# User Guide

# Example of Use
# Acknowledgments
This project has been supported by ...

# License Information

This project is licensed under the terms of the [Slicer License](https://github.com/Slicer/Slicer/blob/master/License.txt)




 