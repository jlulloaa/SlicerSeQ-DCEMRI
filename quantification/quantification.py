import logging
import os
from typing import Annotated, Optional

import vtk, ctk

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
    parameterPack,
)

# from slicer import vtkMRMLScalarVolumeNode, 
from slicer import vtkMRMLSequenceNode, vtkMRMLSegmentationNode, vtkMRMLTableNode
from slicer import vtkMRMLLabelMapVolumeNode
# from slicer import vtkMRMLPlotSeriesNode, vtkMRMLPlotChartNode

import numpy as np

#
# quantification
#


class quantification(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Parametric DCE-MRI")
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Quantification")]
        self.parent.dependencies = ["SequenceRegistration"]  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Jose L. Ulloa (ISANDEX LTD.), Nasib Washal (Queen's Hospital)"] 
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""
Slicer Extension to derive non-PK parametric maps from signal intensity analysis of DCE-MRI datasets. 
For up-to-date user guide, go to <a href="https://gthub.com/jlulloaa/..."> official GitHub repository </a>.
""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This file was originally developed by Jose L. Ulloa, Nasib Washal. 
It is derived from the extension <a href="https://github.com/rnadkarni2/SlicerBreast_DCEMRI_FTV"> Slicer DCEMRI FTV </a>. 
This work was (partially) funded by… (grant Name and Number).
""")

        # Additional initialization step after application startup is complete
        # slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#


# def registerSampleData():
#     """Add data sets to Sample Data module."""
#     # It is always recommended to provide sample data for users to make it easy to try the module,
#     # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

#     import SampleData

#     iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

#     # To ensure that the source code repository remains small (can be downloaded and installed quickly)
#     # it is recommended to store data sets that are larger than a few MB in a Github release.

#     # quantification1
#     SampleData.SampleDataLogic.registerCustomSampleDataSource(
#         # Category and sample name displayed in Sample Data module
#         category="quantification",
#         sampleName="quantification1",
#         # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
#         # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
#         thumbnailFileName=os.path.join(iconsPath, "quantification1.png"),
#         # Download URL and target file name
#         uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
#         fileNames="quantification1.nrrd",
#         # Checksum to ensure file integrity. Can be computed by this command:
#         #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
#         checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
#         # This node name will be used when the data set is loaded
#         nodeNames="quantification1",
#     )

#     # quantification2
#     SampleData.SampleDataLogic.registerCustomSampleDataSource(
#         # Category and sample name displayed in Sample Data module
#         category="quantification",
#         sampleName="quantification2",
#         thumbnailFileName=os.path.join(iconsPath, "quantification2.png"),
#         # Download URL and target file name
#         uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
#         fileNames="quantification2.nrrd",
#         checksums="SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
#         # This node name will be used when the data set is loaded
#         nodeNames="quantification2",
#     )


#
# quantificationParameterNode
#

# @parameterPack
# class relevantDCEindices:
#     preContrastIndex: Annotated[float, WithinRange(0.0, 1.0)] = 0.0
#     earlyPostContrastIndex: Annotated[float, WithinRange(0.0, 1.0)] = 0.0
#     latePostContrastIndex: Annotated[float, WithinRange(0.0, 1.0)] = 0.0
    

@parameterNodeWrapper
class quantificationParameterNode:
    """
    The parameters needed by module.

    input4DVolume - The volume to threshold.
    imageThreshold - The value at which to threshold the input volume.
    invertThreshold - If true, will invert the threshold.
    thresholdedVolume - The output volume that will contain the thresholded volume.
    invertedVolume - The output volume that will contain the inverted thresholded volume.
    """

    input4DVolume: vtkMRMLSequenceNode #vtkMRMLScalarVolumeNode
    inputMaskVolume: vtkMRMLSegmentationNode #vtkMRMLScalarVolumeNode
    PreContrastIndex: Annotated[float, WithinRange(0.0, 100.0)] = 0.0 #relevantDCEindices
    EarlyPostContrastIndex: Annotated[float, WithinRange(0.0, 100.0)] = 0.0 #relevantDCEindices
    LatePostContrastIndex: Annotated[float, WithinRange(0.0, 100.0)] = 0.0 #relevantDCEindices
    # segmentationList: vtkMRMLLabelMapVolumeNode
    # imageThreshold: Annotated[float, WithinRange(-100, 500)] = 100
    # Setting up table and plot nodes (do we really need this?)
    # tableTICNode : vtkMRMLTableNode #  = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode")
    # plotTICNode: vtkMRMLPlotSeriesNode # = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "Time Intensity Curves")
    # # Create chart and add plot
    # plotChartTICNode: vtkMRMLPlotChartNode # = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode")

    # invertThreshold: bool = False
    # thresholdedVolume: vtkMRMLScalarVolumeNode
    # invertedVolume: vtkMRMLScalarVolumeNode


#
# quantificationWidget
#


class quantificationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        print('(re-)Starting')
        self._parameterNode = None
        self._parameterNodeGuiTag = None
        
        # JU - Setup an initial layout
        # Switch to a layout that contains a plot view to create a plot widget
        self.layoutManager = slicer.app.layoutManager()
        # 38 is the layout called "Four-up Quantitative" in the layout dropdown list 
        # (to check which number is currently set, use: self.layoutManger.layout)
        self.layoutManager.setLayout(38)
        # JU - to ensure the columns name are consisten between TICTable and TICplot, I define them here:
        self.TICTableRowNames = ["Timepoint", "Relative ENH (%)", "Curve Fit"]
        self.SummaryTableRowNames = ["Parameter", "Value", "Units"]
        # Display and other constants:
        self.MAX_PC = 300

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/quantification.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)
        
        # JU - Segmentation List Selector 
        # parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        # parametersCollapsibleButton.text = "Parameters"
        # self.layout.addWidget(parametersCollapsibleButton)

        # Layout within the dummy collapsible button
        # parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        # Create segment editor to get access to effects        
        self.segmentationListSelector = slicer.qMRMLSegmentEditorWidget()
        # self.segmentationListSelector = slicer.qMRMLNodeComboBox()
        self.segmentationListSelector.setMRMLScene(slicer.mrmlScene)
        # To show segment editor widget (useful for debugging): segmentEditorWidget.show()
        self.segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
        slicer.mrmlScene.AddNode(self.segmentEditorNode)
        # self.segmentationListSelector.nodeTypes = ["vtkSegmentation"]#["vtkMRMLLabelMapVolumeNode"]
        self.segmentationListSelector.enabled = False
        # self.segmentationListSelector.addEnabled = False
        # self.segmentationListSelector.selectNodeUponCreation = True
        # self.segmentationListSelector.renameEnabled = False
        # self.segmentationListSelector.removeEnabled = False
        # self.segmentationListSelector.noneEnabled = False
        self.segmentationListSelector.setToolTip(_("Select label mask"))
        # self.segmentationListSelector.setCurrentNode(None)
        # # addRow: appends new element
        self.ui.segmentEditorCollapsibleButton.layout().addRow(self.segmentationListSelector)
        self.segmentationListSelector.setMRMLSegmentEditorNode(self.segmentEditorNode)

        # JU - Output table selector
        self.outputTICTableSelector = slicer.qMRMLNodeComboBox()
        self.outputTICTableSelector.noneDisplay = _("Create new table")
        self.outputTICTableSelector.setMRMLScene(slicer.mrmlScene)
        self.outputTICTableSelector.nodeTypes = ["vtkMRMLTableNode"]
        self.outputTICTableSelector.enabled = False
        self.outputTICTableSelector.addEnabled = False
        self.outputTICTableSelector.selectNodeUponCreation = True
        self.outputTICTableSelector.renameEnabled = False
        self.outputTICTableSelector.removeEnabled = False
        self.outputTICTableSelector.noneEnabled = False
        self.outputTICTableSelector.setToolTip(_("Select a Table"))
        self.outputTICTableSelector.setCurrentNode(None)
        # use insertRow to append the new element into a specific row (i.e. FormLayout.insertRow(position, Text, Table))
        self.ui.parametersFormLayout.addRow(_("Output tables:"), self.outputTICTableSelector)
        
        # JU - Initialise plot series and chart nodes:
        # self.plotSeriesNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotSeriesNode")
        self.plotChartNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotChartNode")
        
        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = quantificationLogic()
        
        # Connections
        # JU - Any change in the input volume will be reflected by a change in the scene
        # self.ui.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInputSelect())
        # self.ui.inputMaskSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onMaskSelect())
        # JU - Any change in the selected index defining the DCE timepoints of interest, 
        # will be reflected as a change in the visualisation:
        self.ui.indexSliderPreContrast.connect("valueChanged(double)", self.setSequenceItemIndex)
        self.ui.indexSliderEarlyPostContrast.connect("valueChanged(double)", self.setSequenceItemIndex)
        self.ui.indexSliderLatePostContrast.connect("valueChanged(double)", self.setSequenceItemIndex)
        # JU - Connect the output table to ensure it gets updated whenever the Apply buttons is pressed:
        # self.outputTableSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onNodeSelectionChanged)
        # JU - Add an additional connector to monitor the collapsible status of the segmentation editor.
        #      by monitoring it, will display options to select a segmentation mask from an updated list:
        self.ui.segmentEditorCollapsibleButton.connect("contentsCollapsed(bool)", self.monitorStatusSegmemtation)
        # self.ui.segmentListSelector.connect("highlighted(int)", self.selectedMaskIndex)
        self.ui.segmentListSelector.connect("currentIndexChanged(int)", self.updateSelectedSegmentMask)
        # self.ui.segmentListSelector.connect("currentTextChanged(str)", self.updateSelectedSegmentMaskText)
        # self.ui.segmentListSelector.connect("highlighted(int)", self.selectSegmentMask)
        # self.ui.segmentListSelector.connect(self.selectSegmentMask)
        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.input4DVolume:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSequenceNode")
            if firstVolumeNode:
                self._parameterNode.input4DVolume = firstVolumeNode               
                # Initialise the index slider:
                # JU - DEBUG
                # print(f'Populating automatically the Input Selector')
                self.ui.parametersCollapsibleButton.enabled=True
                self.refreshIndexSelectors(self._parameterNode.input4DVolume.GetNumberOfDataNodes())
            # else:
                # self.refreshIndexSelectors(0)
            
        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.inputMaskVolume:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
            if firstVolumeNode:
                self._parameterNode.inputMaskVolume = firstVolumeNode
            else:
                # There are no segmentation masks available, so let's create one by default
                self._parameterNode.inputMaskVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation Mask")
                # But keeps the selector disabled until the segmentation has a label map
                self.ui.inputMaskSelector.enabled = False
                # And enable the connection with the segment editor to create a label map:
                self.segmentationListSelector.enabled = True
                
        # Select default plot and tables nodes, to avoid creating new ones:
        if not self.outputTICTableSelector.currentNode():
            self.TICTableNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLTableNode")
            self.SummaryTableNode = slicer.mrmlScene.GetNthNodeByClass(1, "vtkMRMLTableNode")
            if not self.TICTableNode:
                self.TICTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "TIC Table")
            # TODO: Check how to assign multiple tables to selector
            if not self.SummaryTableNode:
                self.SummaryTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "Summary Table")
            self.outputTICTableSelector.setCurrentNode(self.SummaryTableNode)

        # if not self.plotSeriesNode:
        numberOfPlotSeriesNode = slicer.mrmlScene.GetNodesByClass("vtkMRMLPlotSeriesNode").GetNumberOfItems()
        if numberOfPlotSeriesNode == 0:
            # TODO: JU - replace "TIC Plot" by the segment mask currently active
            firstPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "TIC plot")
            secondPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "Curve Fit")
        elif numberOfPlotSeriesNode == 1:
            firstPlotSeriesNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotSeriesNode")
            secondPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "Curve Fit")
        else:
            firstPlotSeriesNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotSeriesNode")
            secondPlotSeriesNode = slicer.mrmlScene.GetNthNodeByClass(1, "vtkMRMLPlotSeriesNode")
            
        self.plotSeriesNode = firstPlotSeriesNode
        self.plotCurveFitNode = secondPlotSeriesNode
        self.plotSeriesNode.SetAndObserveTableNodeID(self.TICTableNode.GetID())
        self.plotCurveFitNode.SetAndObserveTableNodeID(self.TICTableNode.GetID())

        if not self.plotChartNode:
            firstPlotChartNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotChartNode")
            if not firstPlotChartNode:
                firstPlotChartNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode", "TIC chart")
            self.plotChartNode = firstPlotChartNode
            self.plotChartNode.AddAndObservePlotSeriesNodeID(self.plotSeriesNode.GetID())
            self.plotChartNode.AddAndObservePlotSeriesNodeID(self.plotCurveFitNode.GetID())
            
        # Finally, (re-)configure the plot window
        self.configurePlotWindow()
     
    def setParameterNode(self, inputParameterNode: Optional[quantificationParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """
        # JU - DEBUGMODE
        print('setParameterNode - Start')
        if self._parameterNode:
            # JU - DEBUGMODE
            print('Parameter Node is not null. Disconnecting GUI')
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        # JU - DEBUGMODE
        print('Setting the parameter Node to input Parameter node')
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            print('Parameter Node is not null. Assigning a Node GUI Tag')
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            if self._parameterNode.input4DVolume: 
                self.refreshIndexSelectors(self._parameterNode.input4DVolume.GetNumberOfDataNodes())
                self.ui.segmentEditorCollapsibleButton.enabled = True

            if self._parameterNode.inputMaskVolume:
                # enable the segment editor if a segmentation mask is already loaded
                self.segmentationListSelector.enabled = True

            if (self.ui.segmentEditorCollapsibleButton.enabled) & (self.segmentationListSelector.enabled):
                # If there both, the input volume and a segmentation mask, set them up in the segment editor:
                self.onMaskSelect()
                
            self._checkCanApply()
        # JU - DEBUGMODE
        print('setParameterNode - End')

    def _checkCanApply(self, caller=None, event=None) -> None:
        if self._parameterNode and self._parameterNode.input4DVolume and self._parameterNode.inputMaskVolume:
            # JU - DEBUGMODE
            print("Compute output volume")
            # TODO: update legend indicating the index corresponds to the Pre-Contrast phase
            # self.setSequenceItemIndex(self.ui.indexSliderPreContrast.value)
            self.ui.parametersCollapsibleButton.enabled=True
            self.ui.applyButton.toolTip = _("Compute output volume")
            self.ui.applyButton.enabled = True
            # self.outputTICTableSelector.enabled = True
        else:
            # JU - DEBUGMODE
            print('Nothing to do, will keep the button disabled...')
            # self.ui.applyButton.toolTip = _("Select input and output volume nodes")
            self.ui.applyButton.toolTip = _("Select input and mask volumes nodes")
            self.ui.applyButton.enabled = False
            
        if self._parameterNode.input4DVolume:
        #     self.ui.parametersCollapsibleButton.enabled=True
            self.ui.segmentEditorCollapsibleButton.enabled = True


    def onApplyButton(self) -> None:
        """Run processing when user clicks "Apply" button."""
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            # Enable Table selection and update chart window:
            self.plotSeriesNode.SetName(self.ui.segmentListSelector.currentText)
            self.update_plot_window()
            # Compute output
            self.logic.process(self._parameterNode.input4DVolume, # self.ui.inputSelector.currentNode(), 
                               self._parameterNode.inputMaskVolume, # self.ui.inputMaskSelector.currentNode(), 
                               {'TICTable': [self.TICTableNode, self.TICTableRowNames],
                                'SummaryTable': [self.SummaryTableNode, self.SummaryTableRowNames]}, #outputTICTableSelector.currentNode(),
                               int(self._parameterNode.PreContrastIndex), #int(self.ui.indexSliderPreContrast.value), 
                               int(self._parameterNode.EarlyPostContrastIndex), # int(self.ui.indexSliderEarlyPostContrast.value), 
                               int(self._parameterNode.LatePostContrastIndex), #int(self.ui.indexSliderLatePostContrast.value), #)
                               self.ui.segmentListSelector.currentIndex,
                               self.MAX_PC)
                            #    self.ui.imageThresholdSliderWidget.value, self.ui.invertOutputCheckBox.checked)
            # Compute inverted output (if needed)
            # if self.ui.invertedOutputSelector.currentNode():
            #     # If additional output volume is selected then result with inverted threshold is written there
            #     self.logic.process(self.ui.inputSelector.currentNode(), self.ui.invertedOutputSelector.currentNode(),
            #                        self.ui.imageThresholdSliderWidget.value, not self.ui.invertOutputCheckBox.checked, showResult=False)
            # slicer.modules.plots.logic().ShowChartInLayout(self.plotChartNode)        

    # JU - user-defined connnector functions
    def onInputSelect(self):
        if not self._parameterNode.input4DVolume: #self.ui.inputSelector.currentNode():
            # print('No nodes to use')
            numberOfDataNodes = 0
        else:
            numberOfDataNodes = self._parameterNode.input4DVolume.GetNumberOfDataNodes() #self.ui.inputSelector.currentNode().GetNumberOfDataNodes()
            # JU - DEBUG
            # Get some information of the selected sequence:
            self.ui.segmentEditorCollapsibleButton.enabled = True
            self.segmentationListSelector.enabled = True
        print(f'Number of items in the sequence: {numberOfDataNodes}')
        self.refreshIndexSelectors(numberOfDataNodes)
    
    def monitorStatusSegmemtation(self):
        # Get an updated segment list:
        segmentList = self.logic.getSegmentList(self._parameterNode.inputMaskVolume)
        # for segments in segmentList:
        #     print(f'Segment Name: {segments.GetName()}')
            
        if self.ui.segmentEditorCollapsibleButton.collapsed:
            print(f'show selection list with the following options:')
            # Get currently selected index and text:
            currIndex = self.ui.segmentListSelector.currentIndex
            currText = self.ui.segmentListSelector.currentText
            print(f'Currently, this text {currText} and index {currIndex} are selected')
            # Update the content of the list:
            segmentListItems = [segment.GetName() for segment in segmentList]
            # is the new Clear the old list:
            print(f'Clearing the list...')
            self.ui.segmentListSelector.clear()
            # Re-populate with the updated list:
            print(f'Re-populating the list...')
            self.ui.segmentListSelector.addItems(segmentListItems)
            # check wether the udpated list is the same as before, or the items' name have been modified
            # get index where the already selected text is in the new list:
            if currText in segmentListItems:
                # find the position
                updatedIndex = segmentListItems.index(currText)
                print(f'Current Text {currText} still part of the list and is located at {updatedIndex}')
            else:
                updatedIndex = 0
                print('Segment Mask has been deleted, restart the selection at 0')
                                
            self.updateSelectedSegmentMask(updatedIndex)
            self.ui.segmentListSelector.enabled=True
        else:
            print(f'disable/hide the list of options')
            self.ui.segmentListSelector.enabled=False
    
    def updateSelectedSegmentMask(self, updatedIndex):
        updatedIndex = np.max([0, updatedIndex])
        self.ui.segmentListSelector.setCurrentIndex(updatedIndex)
        print(f'List Selected Text: {self.ui.segmentListSelector.currentText}') # itemText(updatedIndex)}')
        print(f'List Selection: {self.ui.segmentListSelector.currentIndex}')
        # Set visibility for the selected segmentation label:
        displayNode = self._parameterNode.inputMaskVolume.GetDisplayNode()
        displayNode.SetAllSegmentsVisibility(False) # Hide all segments
        displayNode.SetSegmentVisibility(self._parameterNode.inputMaskVolume.GetSegmentation().GetNthSegmentID(updatedIndex), True)
        
    def onMaskSelect(self):
        
        # TODO: here enable the options to select a particular segmentation label (e.g. Tumour Tissue)
        print(f'onMaskSelect Function')
        # if self.ui.inputMaskSelector.currentNode():
        # self.ui.segmentEditorCollapsibleButton.enabled = True
        # segmentList = self.logic.getSegmentList(self.ui.inputMaskSelector.currentNode())
        segmentList = self.logic.getSegmentList(self._parameterNode.inputMaskVolume)
        # Update the segmentListSelector:
        segmentListItems = [segment.GetName() for segment in segmentList]
        self.ui.segmentListSelector.clear()
        self.ui.segmentListSelector.addItems(segmentListItems)
        # JU - DEBUG
        print('Segment Names: ' + '\n'.join(segmentListItems))
            
        # # self.segmentationListSelector = segmentList#.setCurrentNode(segmentList[0])
        # self.segmentationListSelector.setCurrentNode(segmentList[0])
        # self.segmentationListSelector.enabled = True
        self.setSequenceItemIndex(self._parameterNode.EarlyPostContrastIndex) # ui.indexSliderEarlyPostContrast.value)
        # self.segmentationListSelector.setSegmentationNode(self.ui.inputMaskSelector.currentNode())
        self.segmentationListSelector.setMRMLSegmentEditorNode(self.segmentEditorNode)
        self.segmentationListSelector.setSegmentationNode(self._parameterNode.inputMaskVolume) # self.ui.inputMaskSelector.currentNode())
        self.segmentationListSelector.setSourceVolumeNode(self.currentVolume)
        self.ui.segmentEditorCollapsibleButton.text = _("Add/Edit segmentation label")
        self.ui.segmentEditorCollapsibleButton.collapsed = False

        # print(segmentList)
        # workflow: 
        # 1) After a segmentation mask is selected
        # 2) Populate a drop down list with the segmentation labels
        # 3) Enables the drop down list with the segment masks
        
    # JU - separate to refresh the index selctors everytime the module is loaded (not only when the input selector changes)
    def refreshIndexSelectors(self, maxIndex):
        for sequenceItemSelectorWidget in [self.ui.indexSliderPreContrast, self.ui.indexSliderEarlyPostContrast, self.ui.indexSliderLatePostContrast]:
        # for sequenceItemSelectorWidget in [self._parameterNode.PreContrastIndex, self._parameterNode.EarlyPostContrastIndex, self._parameterNode.LatePostContrastIndex]:
            print(f'sequenceItemSelectorWidget: {sequenceItemSelectorWidget}')
            if maxIndex < 1:
                sequenceItemSelectorWidget.maximum = 0
                sequenceItemSelectorWidget.enabled = False
            else:
                sequenceItemSelectorWidget.maximum = maxIndex-1
                sequenceItemSelectorWidget.enabled = True

        self._parameterNode.PreContrastIndex = 0 #ui.indexSliderPreContrast.value =  0
        self._parameterNode.EarlyPostContrastIndex =  1
        self._parameterNode.LatePostContrastIndex = sequenceItemSelectorWidget.maximum
        # JU - DEBUG
        # print(f'Pre Contrast slider: {self.ui.indexSliderPreContrast.value}')
        # print(f'Early Post Contrast slider: {self.ui.indexSliderEarlyPostContrast.value}')
        # print(f'Late Post Contrast slider: {self.ui.indexSliderLatePostContrast.value}')
        
    def setSequenceItemIndex(self, index):
        sequenceBrowserNode = self.logic.findBrowserForSequence(self._parameterNode.input4DVolume) #ui.inputSelector.currentNode())
        # JU - DEBUGMODE
        print(f'Selected Sequence from browser is {sequenceBrowserNode.GetName()}')
        # if sequenceBrowserNode:
        if index is not None:
            sequenceBrowserNode.SetSelectedItemNumber(int(index))
        self.currentVolume = sequenceBrowserNode.GetProxyNode(self._parameterNode.input4DVolume) #self.ui.inputSelector.currentNode())
        # JU - This shows the actual volume in the viewer
        # (https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#show-a-volume-in-slice-views)
        self.updateViewer(self.currentVolume)
        # JU - DEBUG
        # voxelArray = slicer.util.arrayFromVolume(currentVolume)
        # print(f'Mean value: {voxelArray.mean()}')

    def updateViewer(self, volumeToDisplay=None):
        slicer.util.setSliceViewerLayers(background=volumeToDisplay)
    
    def configurePlotWindow(self):
        print('Configuring Plot Series and Chart Window...')
        # Configure Plot Series:
        # Looks like XColumnName and YColumnName have to match the columns names in the Table
        # self.XColumnName = self.outputTICTableSelector.currentNode().GetColumnName(0)
        # self.YColumnName = self.outputTICTableSelector.currentNode().GetColumnName(1)
        # print(f'Xlabel: {self.XColumnName}')
        self.plotSeriesNode.SetXColumnName(self.TICTableRowNames[0])
        self.plotSeriesNode.SetYColumnName(self.TICTableRowNames[1])
        self.plotSeriesNode.SetPlotType(self.plotSeriesNode.PlotTypeScatter)
        self.plotSeriesNode.SetLineStyle(slicer.vtkMRMLPlotSeriesNode.LineStyleSolid)
        # self.plotSeriesNode.SetMarkerStyle(slicer.vtkMRMLPlotSeriesNode.MarkerStyleSquare)
        self.plotSeriesNode.SetColor(0, 0.6, 1.0)
        
        # Configure Plot Curve Fit
        self.plotCurveFitNode.SetXColumnName(self.TICTableRowNames[0])
        self.plotCurveFitNode.SetYColumnName(self.TICTableRowNames[2])
        self.plotCurveFitNode.SetPlotType(self.plotCurveFitNode.PlotTypeScatter)
        self.plotCurveFitNode.SetLineStyle(slicer.vtkMRMLPlotSeriesNode.LineStyleSolid)
        self.plotCurveFitNode.SetMarkerStyle(slicer.vtkMRMLPlotSeriesNode.MarkerStyleNone)
        self.plotCurveFitNode.SetColor(0, 0, 0)

        # Configure Plot Chart Window:
        self.plotChartNode.SetTitle("Time Intensity Curves")
        self.plotChartNode.SetXAxisTitle("Timepoints")
        self.plotChartNode.SetYAxisTitle("REL")
        self.plotChartNode.LegendVisibilityOn()
        self.plotChartNode.SetXAxisRangeAuto(True)
        # self.plotChartNode.SetYAxisRangeAuto(True)
        self.plotChartNode.YAxisRangeAutoOff()
        self.plotChartNode.SetYAxisRange(0, self.MAX_PC)
        
        # Assign Plot Series to Chart window:
        plotWidget = self.layoutManager.plotWidget(0)
        self.plotViewNode = plotWidget.mrmlPlotViewNode()
        self.plotViewNode.SetPlotChartNodeID(self.plotChartNode.GetID())
        
        
    def update_plot_window(self):
        # enable TIC table:
        self.outputTICTableSelector.enabled=True
        self.ui.outputsCollapsibleButton.enabled=True
        # display table:
        self.logic.displayTable(self.SummaryTableNode) #outputTICTableSelector.currentNode())
        # updating plot in chart view:
        self.logic.displayChart(self.plotChartNode)
        
    def clickToDisplay():
        print('hola')
        

#
# quantificationLogic
#


class quantificationLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return quantificationParameterNode(super().getParameterNode())

    # JU - User-defined functions
    def findBrowserForSequence(self, sequenceNode):
        browserNodes = slicer.util.getNodesByClass("vtkMRMLSequenceBrowserNode")
        for browserNode in browserNodes:
            if browserNode.IsSynchronizedSequenceNode(sequenceNode, True):
                return browserNode
        return None
    
    def getSegmentList(self, maskVolumeNode):

        nsegments = maskVolumeNode.GetSegmentation().GetNumberOfSegments()
        segmentList = [maskVolumeNode.GetSegmentation().GetNthSegment(idx) for idx in range(nsegments)]

        return segmentList

    def displayTable(self, currentTable):
        slicer.app.applicationLogic().GetSelectionNode().SetActiveTableID(currentTable.GetID())
        currentTable.SetUseColumnTitleAsColumnHeader(True)  # Make column titles visible (instead of column names)
        slicer.app.applicationLogic().PropagateTableSelection()
        
    def displayChart(self, currentPlotChart):
        slicer.modules.plots.logic().ShowChartInLayout(currentPlotChart) 
    
    # JU - Fitting functions (TODO: Explore whether can take some of the implementation in PkModelling and/or Breast_DCEMRI_FTV)
    def simple_linear_fit(self, time_axis, sample_points, norder = 1):
        # simple lin fit: y(t) = m*t + n ==> lin_params = [m_slope, n_coeff]
        lin_params = np.polyfit(time_axis, sample_points, norder)
        yeval = np.polyval(lin_params, time_axis)
        return lin_params, yeval
           
    # def setParametricMapsVolumeSequence(self, volumeNode, )
    # JU - This may be useful to define the table and labels:
    # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#create-color-table-node
    # JU - End of user-defined section

    def process(self,
                inputVolume: vtkMRMLSequenceNode, #vtkMRMLScalarVolumeNode,
                maskVolume: vtkMRMLSegmentationNode, #vtkMRMLScalarVolumeNode,
                tableNodeDict: dict={'TableName': [vtkMRMLTableNode, 'label_list']}, #vtkMRMLTableNode,
                preContrastIndex: int=0,
                earlyPostContrastIndex: int=1,
                latePostContrastIndex: int=-1,
                segmentNodeIndex: int=0,
                # rowLabels: list=['x', 'y1', 'y2'],
                enhancementUpperThreshold: float=500.0,
                # imageThreshold: float,
                # invert: bool = False,
                # showResult: bool = True
                ) -> None:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputVolume or not maskVolume:
            raise ValueError("Input or output volume is invalid")

        import time

        startTime = time.perf_counter()
        logging.info("Processing started")

        # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
        # cliParams = {
        #     "InputVolume": inputVolume.GetID(),
        #     "OutputVolume": maskVolume.GetID(),
        #     "ThresholdValue": imageThreshold,
        #     "ThresholdType": "Above" if invert else "Below",
        # }
        # cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
        # # We don't need the CLI module node anymore, remove it to not clutter the scene with it
        # slicer.mrmlScene.RemoveNode(cliNode)
        # JU - Get more help: 
        # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#show-volume-rendering-automatically-when-a-volume-is-loaded
        # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#access-voxels-of-a-4d-volume-as-numpy-array
        
        # To get Summary statistics use the SegmentStatistics module
        import SegmentStatistics
        segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
        segStatLogic.getParameterNode().SetParameter("Segmentation", maskVolume.GetID())
        segStatLogic.computeStatistics()
        stats = segStatLogic.getStatistics()

        # Get the segment selected by the list "Segment Label Mask":
        segmentID = maskVolume.GetSegmentation().GetNthSegmentID(segmentNodeIndex)
        segmentName = maskVolume.GetSegmentation().GetSegment(segmentID).GetName()
        # Get Segment volume:
        volume_cm3 = stats[segmentID,"LabelmapSegmentStatisticsPlugin.volume_cm3"]            
        end_proc_mask_time = time.perf_counter()

        # JU - DEBUG Mode:
        print(f'Segment name: {segmentID}')
        print(f'Pre-Contrast Index: {preContrastIndex}')
        print(f'Early Post-Contrast Index: {earlyPostContrastIndex}')
        print(f'Late Post-Contrast Index: {latePostContrastIndex}')

        label = slicer.util.arrayFromSegmentBinaryLabelmap(maskVolume, segmentID)
        points  = np.where( label == 1 )  # or use another label number depending on what you segmented
        # Size of the numpy array is ordered as [nz, ny(row), nx(col)] TODO: verify row and col are correctly assigned!!
        [nz, ny, nx] = slicer.util.arrayFromVolume(inputVolume.GetNthDataNode(0)).shape
        nt = inputVolume.GetNumberOfDataNodes()
        inputVolume4Darray = np.zeros([nt, nz, ny, nx]) # JU to follow ITK convention for 4D volumes
        # Fill in the 4D array from the sequence node
        for volumeIndex in range(nt):
            inputVolume4Darray[volumeIndex, :, :, :] = slicer.util.arrayFromVolume(inputVolume.GetNthDataNode(volumeIndex))
        time_intensity_curve = np.full((nt, len(tableNodeDict['TICTable'][1])), np.nan)
        time_intensity_curve[:,0] = np.linspace(0, nt, nt, endpoint=False) # TODO: replace it by te actual sequence timings (e.g. trigger_times)
        print(f'Volume Size (Nz x Ny x Nx): [{nz} x {ny} x {nx}]')
        end_load_4dVol_time = time.perf_counter()
        
        # Represent the data in terms of SER (S(t)/S0(t)). identifying S0 as the pre-contrast index:
        preContrastVolume = inputVolume4Darray[preContrastIndex, :, :, :]
        print(f'Volume Size: {preContrastVolume.shape}')

        uptakeMap = 100 * (inputVolume4Darray / (1e-6 + preContrastVolume))
        uptakeMap[uptakeMap > enhancementUpperThreshold] = 0
        preEnhVol = uptakeMap[preContrastIndex, :, :, :]
        earlyEnhVol = uptakeMap[earlyPostContrastIndex, :, :, :]
        lateEnhVol = uptakeMap[latePostContrastIndex, :, :, :]

        delta_ENH = lateEnhVol - earlyEnhVol
        first_pass_ENH = earlyEnhVol - preEnhVol
        max_ENH = np.max(uptakeMap, axis=0)
        
        for time_index in range(nt):
            uptake_ti = uptakeMap[time_index, :, :, :]# slicer.util.arrayFromVolume(inputVolume.GetNthDataNode(volumeIndex)) 
            ser_roi  = uptake_ti[points] # this will be a list of the label values
            time_intensity_curve[time_index,1] =  ser_roi.mean()
                    
        [m_slope, n_coeff], time_intensity_curve[1:,2] = self.simple_linear_fit(time_intensity_curve[1:,0], time_intensity_curve[1:,1])
        print(f'Mean Values: {time_intensity_curve}') # should match the mean value of LabelStatistics calculation as a double-check
        labelColumnContent = ['Maximum Enhancement','Delta Enhancement','First Pass Enhancement','Enhancement Slope', 'ROI volume']
        statsColumnContent = [max_ENH[points].mean(), delta_ENH[points].mean(), first_pass_ENH[points].mean(), m_slope, volume_cm3]
        unitsColumnContent = ['%', '%', '%', '[]', 'cm3']
        labelColumn = vtk.vtkStringArray()
        labelColumn.SetName(tableNodeDict['SummaryTable'][1][0])
        statsColumn = vtk.vtkDoubleArray()
        statsColumn.SetName(tableNodeDict['SummaryTable'][1][1])
        unitsColumn = vtk.vtkStringArray()
        unitsColumn.SetName(tableNodeDict['SummaryTable'][1][2])
        for rows in zip(labelColumnContent, statsColumnContent, unitsColumnContent):
            labelColumn.InsertNextValue(rows[0])
            statsColumn.InsertNextValue(rows[1])
            unitsColumn.InsertNextValue(rows[2])

        # np.savetxt("values.txt", values)
        stopTime = time.perf_counter()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")
        print(f'Elapsed time to load the masks: {(end_proc_mask_time-startTime):.2f}s')
        print(f'Elapsed time to load 4D volume and get stats: {(end_load_4dVol_time-end_proc_mask_time):.2f}s')
        print(f'Elapsed time for the whole process: {(stopTime - startTime):.2f}s')
        # JU - Update table and plot - TODO: I think this should be moved to a different function
        slicer.util.updateTableFromArray(tableNodeDict['TICTable'][0], time_intensity_curve, tableNodeDict['TICTable'][1])
        tableNodeDict['SummaryTable'][0].AddColumn(labelColumn)
        tableNodeDict['SummaryTable'][0].AddColumn(statsColumn)
        tableNodeDict['SummaryTable'][0].AddColumn(unitsColumn)
        # self.plot_time_intensity_curve(tableNode)

#
# quantificationTest
#


class quantificationTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_quantification1()

    def test_quantification1(self):
        """Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        import SampleData

        registerSampleData()
        inputVolume = SampleData.downloadSample("quantification1")
        self.delayDisplay("Loaded test data set")

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = quantificationLogic()

        # Test algorithm with non-inverted threshold
        logic.process(inputVolume, outputVolume, threshold, True)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], threshold)

        # Test algorithm with inverted threshold
        logic.process(inputVolume, outputVolume, threshold, False)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], inputScalarRange[1])

        self.delayDisplay("Test passed")
